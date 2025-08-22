"""Analysis API endpoints."""

import logging
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc, func
import uuid
from datetime import datetime, timedelta

from src.core.database import get_db, get_async_db
from src.core.security import get_current_user, User
from src.models.analysis import AnalysisSession, ReportSection, AgentExecution, AnalysisStatus, ProgressEvent, MessageLog
from src.models.user import User as UserModel
from src.schemas.analysis import (
    AnalysisConfigRequest,
    AnalysisStartRequest,
    AnalysisControlRequest,
    AnalysisResponse,
    AnalysisStatusResponse,
    AnalysisListResponse,
    AnalysisMetricsResponse,
    AnalysisStatsResponse,
    ReportSectionResponse,
    AgentExecutionResponse,
    ProgressEventResponse,
    MessageLogResponse
)
from src.schemas.common import ApiResponse, PaginatedResponse
from src.services.analysis_manager import AnalysisManager
from src.models.base import get_kst_now

router = APIRouter()
logger = logging.getLogger(__name__)

# Global managers (would be properly initialized in lifespan)
analysis_manager = AnalysisManager()

# 엔드포인트 순서 맞추기 (CRUD, status, metrics, config 순서)
# 1. 분석 세션 생성 (POST /start)
@router.post("/start", response_model=AnalysisResponse)
async def start_analysis(
    request: AnalysisStartRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    """Start a new analysis session."""
    try:
        config = request.config
        session_id = str(uuid.uuid4())
        analysis_session = AnalysisSession(
            session_id=session_id,
            user_id=current_user.id,
            username=current_user.username,
            ticker=config.ticker,
            analysis_date=datetime.strptime(config.analysis_date, '%Y-%m-%d'),
            config_snapshot=config.model_dump(),
            selected_analysts=[analyst.value for analyst in config.analysts],
            research_depth=config.research_depth,
            llm_provider=config.llm_provider.value,
            status=AnalysisStatus.PENDING,
            client_ip=request.client_metadata.get("ip") if request.client_metadata else None,
            user_agent=request.client_metadata.get("user_agent") if request.client_metadata else None
        )
        db.add(analysis_session)
        await db.commit()
        await db.refresh(analysis_session)
        # Run async function in separate thread with new event loop
        def run_analysis_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    analysis_manager.run_analysis(session_id, config, current_user)
                )
            finally:
                loop.close()
        
        background_tasks.add_task(run_analysis_in_thread)
        logger.info(f"Started analysis {session_id[:8]} for user {current_user.username} - ticker: {config.ticker}")
        
        # Create response without trying to access relationships
        return AnalysisResponse(
            session_id=analysis_session.session_id,
            username=analysis_session.username,
            ticker=analysis_session.ticker,
            analysis_date=analysis_session.analysis_date,
            status=analysis_session.status,
            started_at=analysis_session.started_at,
            completed_at=analysis_session.completed_at,
            execution_time_seconds=analysis_session.execution_time_seconds,
            final_decision=analysis_session.final_decision,
            confidence_score=analysis_session.confidence_score,
            confidence_level=analysis_session.confidence_level,
            llm_call_count=analysis_session.llm_call_count,
            tool_call_count=analysis_session.tool_call_count,
            agents_completed=analysis_session.agents_completed,
            agents_failed=analysis_session.agents_failed,
            error_message=analysis_session.error_message,
            config_snapshot=analysis_session.config_snapshot,
            created_at=analysis_session.created_at,
            report_sections=None,  # Empty for new session
            agent_executions=None  # Empty for new session
        )
    except Exception as e:
        logger.error(f"Failed to start analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}"
        )


# 2. 분석 세션 목록 조회 (GET /sessions)
@router.get("/sessions", response_model=AnalysisListResponse)
async def get_analysis_sessions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    status: Optional[AnalysisStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    include_reports: bool = Query(False, description="Include report sections"),
    include_agents: bool = Query(False, description="Include agent executions")
):
    """Get user's analysis sessions."""
    
    try:
        query = select(AnalysisSession).where(
            AnalysisSession.user_id == current_user.id
        )
        if ticker:
            query = query.where(AnalysisSession.ticker == ticker.upper())
        if status:
            query = query.where(AnalysisSession.status == status)
        if include_reports:
            query = query.options(selectinload(AnalysisSession.report_sections))
        if include_agents:
            query = query.options(selectinload(AnalysisSession.agent_executions))
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_result = db.execute(count_query)
        total = total_result.scalar()
        query = query.order_by(desc(AnalysisSession.created_at))
        query = query.offset((page - 1) * per_page).limit(per_page)
        result = db.execute(query)
        sessions = result.scalars().all()
        
        # Convert sessions to responses, handling relationships properly
        session_responses = []
        for session in sessions:
            response = AnalysisResponse(
                session_id=session.session_id,
                username=session.username,
                ticker=session.ticker,
                analysis_date=session.analysis_date,
                status=session.status,
                started_at=session.started_at,
                completed_at=session.completed_at,
                execution_time_seconds=session.execution_time_seconds,
                final_decision=session.final_decision,
                confidence_score=session.confidence_score,
                confidence_level=session.confidence_level,
                llm_call_count=session.llm_call_count,
                tool_call_count=session.tool_call_count,
                agents_completed=session.agents_completed,
                agents_failed=session.agents_failed,
                error_message=session.error_message,
                config_snapshot=session.config_snapshot,
                created_at=session.created_at,
                report_sections=[ReportSectionResponse.model_validate(rs) for rs in session.report_sections] if include_reports and hasattr(session, 'report_sections') and session.report_sections else None,
                agent_executions=[AgentExecutionResponse.model_validate(ae) for ae in session.agent_executions] if include_agents and hasattr(session, 'agent_executions') and session.agent_executions else None
            )
            session_responses.append(response)
        pages = (total + per_page - 1) // per_page
        return AnalysisListResponse(
            sessions=session_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
    except Exception as e:
        logger.error(f"Failed to get analysis sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to get analysis sessions"
        )

# 3. 분석 세션 단건 조회 (GET /{session_id})
@router.get("/{session_id}", response_model=AnalysisResponse)
async def get_analysis_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_reports: bool = Query(True, description="Include report sections"),
    include_agents: bool = Query(True, description="Include agent executions")
):
    """Get specific analysis session."""
    try:
        query = select(AnalysisSession).where(
            and_(
                AnalysisSession.session_id == session_id,
                AnalysisSession.user_id == current_user.id
            )
        )
        if include_reports:
            query = query.options(selectinload(AnalysisSession.report_sections))
        if include_agents:
            query = query.options(selectinload(AnalysisSession.agent_executions))
        result = db.execute(query)
        analysis_session = result.scalar_one_or_none()
        if not analysis_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis session not found"
            )
        
        # Create response properly handling relationships
        return AnalysisResponse(
            session_id=analysis_session.session_id,
            username=analysis_session.username,
            ticker=analysis_session.ticker,
            analysis_date=analysis_session.analysis_date,
            status=analysis_session.status,
            started_at=analysis_session.started_at,
            completed_at=analysis_session.completed_at,
            execution_time_seconds=analysis_session.execution_time_seconds,
            final_decision=analysis_session.final_decision,
            confidence_score=analysis_session.confidence_score,
            confidence_level=analysis_session.confidence_level,
            llm_call_count=analysis_session.llm_call_count,
            tool_call_count=analysis_session.tool_call_count,
            agents_completed=analysis_session.agents_completed,
            agents_failed=analysis_session.agents_failed,
            error_message=analysis_session.error_message,
            config_snapshot=analysis_session.config_snapshot,
            created_at=analysis_session.created_at,
            report_sections=[ReportSectionResponse.model_validate(rs) for rs in analysis_session.report_sections] if include_reports and hasattr(analysis_session, 'report_sections') and analysis_session.report_sections else None,
            agent_executions=[AgentExecutionResponse.model_validate(ae) for ae in analysis_session.agent_executions] if include_agents and hasattr(analysis_session, 'agent_executions') and analysis_session.agent_executions else None
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysis session"
        )

# 4. 분석 세션 삭제 (DELETE /{session_id})
@router.delete("/{session_id}")
async def delete_analysis_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete analysis session."""
    try:
        result = db.execute(
            select(AnalysisSession).where(
                and_(
                    AnalysisSession.session_id == session_id,
                    AnalysisSession.user_id == current_user.id
                )
            )
        )
        analysis_session = result.scalar_one_or_none()
        if not analysis_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis session not found"
            )
        if analysis_session.is_running:
            # Note: This should be made sync or handled differently
            logger.warning(f"Deleting running analysis session {session_id[:8]}")
        db.delete(analysis_session)
        db.commit()
        logger.info(f"Deleted analysis session {session_id[:8]} for user {current_user.username}")
        return ApiResponse(
            success=True,
            message="Analysis session deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete analysis session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete analysis session"
        )

# 5. 분석 세션 제어 (POST /control)
@router.post("/control")
async def control_analysis(
    request: AnalysisControlRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Control analysis session (stop, pause, resume)."""
    try:
        result = db.execute(
            select(AnalysisSession).where(
                and_(
                    AnalysisSession.session_id == request.session_id,
                    AnalysisSession.user_id == current_user.id
                )
            )
        )
        analysis_session = result.scalar_one_or_none()
        if not analysis_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis session not found"
            )
        if request.action == "stop":
            # Note: This should be made sync or handled differently
            analysis_session.cancel_analysis()
        elif request.action == "pause":
            # Note: This should be made sync or handled differently  
            analysis_session.pause_analysis()
        elif request.action == "resume":
            # Note: This should be made sync or handled differently
            analysis_session.resume_analysis()
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {request.action}"
            )
        db.commit()
        logger.info(f"Analysis {request.session_id[:8]} {request.action} by user {current_user.username}")
        return ApiResponse(
            success=True,
            message=f"Analysis {request.action} successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to control analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to control analysis: {str(e)}"
        )

# 6. 분석 세션 상태 조회 (GET /status/{session_id})
@router.get("/status/{session_id}", response_model=AnalysisStatusResponse)
async def get_analysis_status(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis session status."""
    try:
        result = db.execute(
            select(AnalysisSession).where(
                and_(
                    AnalysisSession.session_id == session_id,
                    AnalysisSession.user_id == current_user.id
                )
            ).options(selectinload(AnalysisSession.agent_executions))
        )
        analysis_session = result.scalar_one_or_none()
        if not analysis_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis session not found"
            )
        elapsed_seconds = None
        estimated_remaining_seconds = None
        if analysis_session.started_at:
            if analysis_session.completed_at:
                elapsed_seconds = (analysis_session.completed_at - analysis_session.started_at).total_seconds()
            else:
                elapsed_seconds = (get_kst_now() - analysis_session.started_at).total_seconds()
        
        
        total_agents = len(analysis_session.selected_analysts or [])

        completed_agents = analysis_session.agents_completed or 0
        
        # Calculate progress percentage
        progress_percentage = 0.0
        if total_agents > 0:
            progress_percentage = round((completed_agents / total_agents) * 100, 1)
        
        agents_status = {}
        current_agent = None
        for execution in analysis_session.agent_executions:
            if execution and execution.status:
                agents_status[execution.agent_name] = execution.status
                if execution.status == "running":
                    current_agent = execution.agent_name
        runtime_status = None
        if analysis_session.is_running:
            # Note: This should be made sync or handled differently
            runtime_status = {}  # Skip async status for now

        return AnalysisStatusResponse(
            session_id=session_id,
            status=analysis_session.status,
            current_agent=current_agent or runtime_status.get("current_agent") if runtime_status else None,
            progress_percentage=progress_percentage,
            started_at=analysis_session.started_at,
            elapsed_seconds=elapsed_seconds,
            estimated_remaining_seconds=estimated_remaining_seconds,
            llm_call_count=analysis_session.llm_call_count or 0,
            tool_call_count=analysis_session.tool_call_count or 0,
            agents_status=agents_status,
            last_message=runtime_status.get("last_message") if runtime_status else None,
            error_message=analysis_session.error_message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get analysis status: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysis status"
        )

# 7. 분석 메트릭 요약 (GET /metrics/summary)
@router.get("/metrics/summary", response_model=AnalysisMetricsResponse)
async def get_analysis_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Period in days")
):
    """Get analysis metrics for user."""
    try:
        cutoff_date = get_kst_now() - timedelta(days=days)
        metrics_query = select(
            func.count(AnalysisSession.session_id).label('total'),
            func.sum(func.case([(AnalysisSession.status == AnalysisStatus.COMPLETED, 1)], else_=0)).label('completed'),
            func.sum(func.case([(AnalysisSession.status == AnalysisStatus.FAILED, 1)], else_=0)).label('failed'),
            func.sum(func.case([(AnalysisSession.status == AnalysisStatus.RUNNING, 1)], else_=0)).label('running'),
            func.avg(AnalysisSession.execution_time_seconds).label('avg_time'),
            func.avg(AnalysisSession.confidence_score).label('avg_confidence')
        ).where(
            and_(
                AnalysisSession.user_id == current_user.id,
                AnalysisSession.created_at >= cutoff_date
            )
        )
        metrics_result = db.execute(metrics_query)
        metrics = metrics_result.first()
        decisions_query = select(
            AnalysisSession.final_decision,
            func.count().label('count')
        ).where(
            and_(
                AnalysisSession.user_id == current_user.id,
                AnalysisSession.created_at >= cutoff_date,
                AnalysisSession.final_decision.isnot(None)
            )
        ).group_by(AnalysisSession.final_decision)
        decisions_result = db.execute(decisions_query)
        decisions = {row.final_decision: row.count for row in decisions_result}
        ticker_query = select(
            AnalysisSession.ticker,
            func.count().label('count')
        ).where(
            and_(
                AnalysisSession.user_id == current_user.id,
                AnalysisSession.created_at >= cutoff_date
            )
        ).group_by(AnalysisSession.ticker).order_by(desc(func.count())).limit(1)
        ticker_result = db.execute(ticker_query)
        top_ticker = ticker_result.first()
        total = metrics.total or 0
        completed = metrics.completed or 0
        success_rate = (completed / total * 100) if total > 0 else 0
        return AnalysisMetricsResponse(
            total_analyses=total,
            completed_analyses=completed,
            failed_analyses=metrics.failed or 0,
            running_analyses=metrics.running or 0,
            average_execution_time_minutes=metrics.avg_time / 60 if metrics.avg_time else None,
            success_rate_percentage=success_rate,
            most_analyzed_ticker=top_ticker.ticker if top_ticker else None,
            decision_distribution=decisions,
            average_confidence_score=float(metrics.avg_confidence) if metrics.avg_confidence else None
        )
    except Exception as e:
        logger.error(f"Failed to get analysis metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get analysis metrics"
        )

# 8. 메시지 로그 조회 (GET /{session_id}/messages)
@router.get("/{session_id}/messages", response_model=PaginatedResponse[MessageLogResponse])
async def get_message_logs(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    message_type: Optional[str] = Query(None, description="Filter by message type"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(100, ge=1, le=500, description="Items per page"),
    order: str = Query("asc", regex="^(asc|desc)$", description="Order by sequence_number")
):
    """Get message logs for analysis session."""
    try:
        # Verify session ownership
        session_query = select(AnalysisSession).where(
            and_(
                AnalysisSession.session_id == session_id,
                AnalysisSession.user_id == current_user.id
            )
        )
        session_result = db.execute(session_query)
        analysis_session = session_result.scalar_one_or_none()
        
        if not analysis_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis session not found"
            )
        
        # Build message query
        query = select(MessageLog).where(MessageLog.session_id == session_id)
        
        if message_type:
            query = query.where(MessageLog.message_type == message_type)
        if agent_name:
            query = query.where(MessageLog.agent_name == agent_name)
        
        # Count total messages
        count_query = select(func.count()).select_from(query.subquery())
        total_result = db.execute(count_query)
        total = total_result.scalar()
        
        # Order and paginate
        if order == "desc":
            query = query.order_by(desc(MessageLog.sequence_number))
        else:
            query = query.order_by(MessageLog.sequence_number)
        
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Execute query
        result = db.execute(query)
        message_logs = result.scalars().all()
        
        # Convert to response models
        message_responses = [MessageLogResponse.model_validate(msg) for msg in message_logs]
        
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            items=message_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get message logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get message logs"
        )


# 9. 진행 상황 이벤트 조회 (GET /{session_id}/events)
@router.get("/{session_id}/events", response_model=PaginatedResponse[ProgressEventResponse])
async def get_progress_events(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    stage: Optional[str] = Query(None, description="Filter by stage"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page")
):
    """Get progress events for analysis session."""
    try:
        # Verify session ownership
        session_query = select(AnalysisSession).where(
            and_(
                AnalysisSession.session_id == session_id,
                AnalysisSession.user_id == current_user.id
            )
        )
        session_result = db.execute(session_query)
        analysis_session = session_result.scalar_one_or_none()
        
        if not analysis_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis session not found"
            )
        
        # Build event query
        query = select(ProgressEvent).where(ProgressEvent.session_id == session_id)
        
        if event_type:
            query = query.where(ProgressEvent.event_type == event_type)
        if agent_name:
            query = query.where(ProgressEvent.agent_name == agent_name)
        if stage:
            query = query.where(ProgressEvent.stage == stage)
        
        # Count total events
        count_query = select(func.count()).select_from(query.subquery())
        total_result = db.execute(count_query)
        total = total_result.scalar()
        
        # Order by creation time (newest first) and paginate
        query = query.order_by(desc(ProgressEvent.created_at))
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Execute query
        result = db.execute(query)
        progress_events = result.scalars().all()
        
        # Convert to response models
        event_responses = [ProgressEventResponse.model_validate(event) for event in progress_events]
        
        pages = (total + per_page - 1) // per_page
        
        return PaginatedResponse(
            items=event_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages,
            has_next=page < pages,
            has_prev=page > 1
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get progress events: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get progress events"
        )


# 10. 현재 세션 상태 및 메시지 조회 (GET /{session_id}/live)
@router.get("/{session_id}/live")
async def get_live_session_data(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_messages: bool = Query(True, description="Include message logs"),
    message_limit: int = Query(100, ge=1, le=500, description="Max number of recent messages")
):
    """Get current session state with real-time messages for analysis page."""
    try:
        # Verify session ownership
        session_query = select(AnalysisSession).where(
            and_(
                AnalysisSession.session_id == session_id,
                AnalysisSession.user_id == current_user.id
            )
        ).options(
            selectinload(AnalysisSession.agent_executions),
            selectinload(AnalysisSession.report_sections)
        )
        
        session_result = db.execute(session_query)
        analysis_session = session_result.scalar_one_or_none()
        
        if not analysis_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis session not found"
            )
        
        # Get runtime status from analysis manager if running
        runtime_status = None
        if analysis_session.is_running:
            runtime_status = await analysis_manager.get_analysis_status(session_id)
        
        # Calculate progress and timing
        elapsed_seconds = None
        if analysis_session.started_at:
            if analysis_session.completed_at:
                elapsed_seconds = (analysis_session.completed_at - analysis_session.started_at).total_seconds()
            else:
                elapsed_seconds = (get_kst_now() - analysis_session.started_at).total_seconds()
        
        
        
        
        # Get agent statuses
        agents_status = {}
        current_agent = None
        

     

        for execution in analysis_session.agent_executions:
            if execution and execution.status:
                agents_status[execution.agent_name] = execution.status
                if execution.status == "running":
                    current_agent = execution.agent_name

        total_agents = len(analysis_session.selected_analysts) + 5
        completed_agents = analysis_session.agents_completed or 0

        progress_percentage = round((len(agents_status) / total_agents) * 100)
        # Get recent messages if requested
        messages = []
        if include_messages:
            message_query = select(MessageLog).where(
                MessageLog.session_id == session_id
            ).order_by(desc(MessageLog.sequence_number)).limit(message_limit)
            
            message_result = db.execute(message_query)
            message_logs = message_result.scalars().all()
            messages = [MessageLogResponse.model_validate(msg) for msg in reversed(message_logs)]
        
        # Build response data
        response_data = {
            "session_id": session_id,
            "status": analysis_session.status,
            "ticker": analysis_session.ticker,
            "analysis_date": analysis_session.analysis_date,
            "current_agent": current_agent,
            "progress_percentage": progress_percentage,
            "started_at": analysis_session.started_at,
            "completed_at": analysis_session.completed_at,
            "elapsed_seconds": elapsed_seconds,
            "agents_status": agents_status,
            "agents_completed": completed_agents,
            "agents_failed": analysis_session.agents_failed or 0,
            "selected_analysts": analysis_session.selected_analysts or [],
            "last_message": runtime_status.get("last_message") if runtime_status else analysis_session.last_message,
            "last_message_timestamp": analysis_session.last_message_timestamp,
            "created_at": analysis_session.created_at,
            "messages": messages if include_messages else None,
            "report_sections": [ReportSectionResponse.model_validate(rs) for rs in analysis_session.report_sections] if analysis_session.report_sections else [],
            "agent_executions": [AgentExecutionResponse.model_validate(ae) for ae in analysis_session.agent_executions] if analysis_session.agent_executions else []
        }
        
        return ApiResponse(
            success=True,
            message="Live session data retrieved successfully",
            data=response_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get live session data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get live session data"
        )


# 11. 분석 config 유효성 검사 (GET /config/validate)
@router.get("/config/validate")
async def validate_analysis_config(
    config: AnalysisConfigRequest,
    current_user: User = Depends(get_current_user)
):
    """Validate analysis configuration."""
    try:
        validation_errors = []
        warnings = []
        if not config.ticker.isalnum():
            validation_errors.append("Ticker must contain only alphanumeric characters")
        analysis_date = datetime.strptime(config.analysis_date, '%Y-%m-%d')
        if analysis_date > get_kst_now():
            warnings.append("Analysis date is in the future")
        if len(config.analysts) > 4:
            warnings.append("Selecting all analysts may increase analysis time")
        if config.research_depth > 5:
            warnings.append("High research depth may significantly increase analysis time")
        return ApiResponse(
            success=len(validation_errors) == 0,
            message="Configuration validation complete",
            data={
                "valid": len(validation_errors) == 0,
                "errors": validation_errors,
                "warnings": warnings
            }
        )
    except Exception as e:
        logger.error(f"Config validation error: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message=f"Validation failed: {str(e)}"
        )
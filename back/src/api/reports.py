"""Reports API endpoints."""

import logging
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, desc, func

from src.core.database import get_db
from src.core.security import User
from src.models.analysis import AnalysisSession, ReportSection
from src.schemas.analysis import (
    AnalysisResponse,
    ReportSectionResponse,
    AnalysisStatsResponse
)
from src.schemas.common import ApiResponse
from src.core.security import get_current_user, User
from src.models.base import get_kst_now
router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/history")
async def get_analysis_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page")
):
    """Get user's analysis history."""
    try:
        # Build query - no eager loading for list view (better performance)
        query = select(AnalysisSession).where(
            AnalysisSession.user_id == current_user.id
        )
        
        # Apply ticker filter
        if ticker:
            query = query.where(AnalysisSession.ticker.contains(ticker.upper()))
        
        # Count total
        count_query = select(func.count()).select_from(
            query.subquery()
        )
        total_result = db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination and ordering
        query = query.order_by(desc(AnalysisSession.created_at))
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        # Execute query
        result = db.execute(query)
        sessions = result.scalars().all()
        
        # Convert to response objects
        session_responses = [AnalysisResponse.model_validate(session) for session in sessions]
        
        # Calculate pagination info
        pages = (total + per_page - 1) // per_page

        data = {
            "sessions": session_responses,
            "total": total,
            "page": page,
            "per_page": per_page,
            "pages": pages,
            "has_next": page < pages,
            "has_prev": page > 1
        }
        
        return ApiResponse(
            success=True,
            message="Analysis history fetched successfully",
            data=data
        )
        
    except Exception as e:
        logger.error(f"Failed to get analysis history: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message="Failed to get analysis history",
            data=None
        )


@router.get("/{session_id}")
async def get_analysis_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get complete analysis report."""
    try:
        # Get analysis session with all related data - eager loading for detail view
        result = db.execute(
            select(AnalysisSession).where(
                and_(
                    AnalysisSession.session_id == session_id,
                    AnalysisSession.user_id == current_user.id
                )
            ).options(
                selectinload(AnalysisSession.report_sections),
                selectinload(AnalysisSession.agent_executions)
            )
        )
        
        analysis_session = result.scalar_one_or_none()
        
        if not analysis_session:
            return ApiResponse(
                success=False,
                message="Analysis report not found",
                data=None
            )
        
        return ApiResponse(
            success=True,
            message="Analysis report fetched successfully",
            data=AnalysisResponse.model_validate(analysis_session)
        )
        
    except Exception as e:
        logger.error(f"Failed to get analysis report: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message="Failed to get analysis report",
            data=None
        )


@router.get("/{session_id}/sections")
async def get_report_sections(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    section_type: Optional[str] = Query(None, description="Filter by section type")
):
    """Get report sections for a specific analysis."""
    try:
        # Verify user has access to this analysis
        analysis_result = db.execute(
            select(AnalysisSession).where(
                and_(
                    AnalysisSession.session_id == session_id,
                    AnalysisSession.user_id == current_user.id
                )
            )
        )
        
        analysis_session = analysis_result.scalar_one_or_none()
        
        if not analysis_session:
            return ApiResponse(
                success=False,
                message="Analysis session not found",
                data=None
            )
        
        # Build sections query
        sections_query = select(ReportSection).where(
            ReportSection.session_id == session_id
        )
        
        if section_type:
            sections_query = sections_query.where(
                ReportSection.section_type == section_type
            )
        
        sections_query = sections_query.order_by(ReportSection.created_at)
        
        # Execute query
        sections_result = db.execute(sections_query)
        sections = sections_result.scalars().all()
        
        section_responses = [ReportSectionResponse.model_validate(section) for section in sections]
        
        return ApiResponse(
            success=True,
            message="Report sections fetched successfully",
            data=section_responses
        )
        
    except Exception as e:
        logger.error(f"Failed to get report sections: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message="Failed to get report sections",
            data=None
        )


@router.get("/{session_id}/export")
async def export_analysis_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    format: str = Query("json", description="Export format: json, pdf, html")
):
    """Export analysis report in various formats."""
    try:
        # Get complete analysis data - eager loading for export
        result = db.execute(
            select(AnalysisSession).where(
                and_(
                    AnalysisSession.session_id == session_id,
                    AnalysisSession.user_id == current_user.id
                )
            ).options(
                selectinload(AnalysisSession.report_sections),
                selectinload(AnalysisSession.agent_executions)
            )
        )
        
        analysis_session = result.scalar_one_or_none()
        
        if not analysis_session:
            return ApiResponse(
                success=False,
                message="Analysis report not found",
                data=None
            )
        
        # Export based on format
        if format.lower() == "json":
            from fastapi.responses import JSONResponse
            from datetime import datetime

            export_data = {
                "session_info": AnalysisResponse.model_validate(analysis_session).model_dump(),
                "export_timestamp": datetime.utcnow().isoformat(),
                "export_format": "json",
                "version": "1.0"
            }
            
            return JSONResponse(
                content=ApiResponse(
                    success=True,
                    message="Analysis report exported as JSON",
                    data=export_data
                ).model_dump(),
                headers={
                    "Content-Disposition": f"attachment; filename=analysis_{session_id[:8]}.json"
                }
            )
        
        elif format.lower() == "pdf":
            return ApiResponse(
                success=False,
                message="PDF export not yet implemented",
                data=None
            )
        
        elif format.lower() == "html":
            return ApiResponse(
                success=False,
                message="HTML export not yet implemented",
                data=None
            )
        
        else:
            return ApiResponse(
                success=False,
                message=f"Unsupported export format: {format}",
                data=None
            )
        
    except Exception as e:
        logger.error(f"Failed to export analysis report: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message="Failed to export analysis report",
            data=None
        )


@router.get("/stats/summary")
async def get_analysis_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    days: int = Query(30, ge=1, le=365, description="Period in days")
):
    """Get analysis statistics for user."""
    try:
        from datetime import timedelta
        
        cutoff_date = get_kst_now() - timedelta(days=days)
        
        # Build base query
        base_query = select(AnalysisSession).where(
            and_(
                AnalysisSession.user_id == current_user.id,
                AnalysisSession.created_at >= cutoff_date
            )
        )
        
        if ticker:
            base_query = base_query.where(AnalysisSession.ticker.contains(ticker.upper()))
        
        # Get total count
        count_result = db.execute(
            select(func.count()).select_from(base_query.subquery())
        )
        total_analyses = count_result.scalar()
        
        # Get decision distribution
        decisions_query = select(
            AnalysisSession.final_decision,
            func.count().label('count')
        ).where(
            and_(
                AnalysisSession.user_id == current_user.id,
                AnalysisSession.created_at >= cutoff_date,
                AnalysisSession.final_decision.isnot(None)
            )
        )
        
        if ticker:
            decisions_query = decisions_query.where(AnalysisSession.ticker.contains(ticker.upper()))
        
        decisions_query = decisions_query.group_by(AnalysisSession.final_decision)
        
        decisions_result = db.execute(decisions_query)
        decision_distribution = {
            row.final_decision: row.count 
            for row in decisions_result
        }
        
        # Get average confidence
        confidence_query = select(
            func.avg(AnalysisSession.confidence_score)
        ).where(
            and_(
                AnalysisSession.user_id == current_user.id,
                AnalysisSession.created_at >= cutoff_date,
                AnalysisSession.confidence_score.isnot(None)
            )
        )
        
        if ticker:
            confidence_query = confidence_query.where(AnalysisSession.ticker.contains(ticker.upper()))
        
        confidence_result = db.execute(confidence_query)
        average_confidence = confidence_result.scalar()
        
        stats_data = AnalysisStatsResponse(
            username=current_user.username,
            ticker=ticker,
            period_days=days,
            total_analyses=total_analyses,
            decision_distribution=decision_distribution,
            average_confidence=float(average_confidence) if average_confidence else None
        )
        
        return ApiResponse(
            success=True,
            message="Analysis statistics fetched successfully",
            data=stats_data
        )
        
    except Exception as e:
        logger.error(f"Failed to get analysis stats: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message="Failed to get analysis statistics",
            data=None
        )


@router.delete("/{session_id}")
async def delete_analysis_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete analysis report."""
    try:
        # Get analysis session
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
            return ApiResponse(
                success=False,
                message="Analysis report not found",
                data=None
            )
        
        # Delete the analysis session (cascading deletes will handle related data)
        db.delete(analysis_session)
        db.commit()
        
        logger.info(f"Deleted analysis report {session_id[:8]} for user {current_user.username}")
        
        return ApiResponse(
            success=True,
            message="Analysis report deleted successfully",
            data=None
        )
        
    except Exception as e:
        logger.error(f"Failed to delete analysis report: {e}", exc_info=True)
        return ApiResponse(
            success=False,
            message="Failed to delete analysis report",
            data=None
        )
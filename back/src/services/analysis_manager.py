"""Analysis management service for running trading analysis."""

import asyncio
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass
import sys
import os
from pathlib import Path

# Add project root to path for trading system imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from src.core.database import get_database_manager
from src.core.security import User
from src.models.base import get_kst_now
from src.models.analysis import AnalysisSession, ReportSection, AgentExecution, AnalysisStatus, AgentStatus, ProgressEvent, MessageLog
from src.schemas.analysis import AnalysisConfigRequest, AnalysisMessage, ToolCallMessage, AgentUpdateMessage
from sqlalchemy import select, and_, func

# Import TradingAgents
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


@dataclass
class AnalysisTask:
    """Analysis task data structure."""
    session_id: str
    config: AnalysisConfigRequest
    user: User
    status: str = "pending"
    started_at: Optional[datetime] = None
    graph: Optional[Any] = None
    task: Optional[asyncio.Task] = None


class AnalysisManager:
    """Manager for running and controlling analysis sessions."""
    
    def __init__(self, max_concurrent_analyses: int = 5):
        self.max_concurrent_analyses = max_concurrent_analyses
        self.active_analyses: Dict[str, AnalysisTask] = {}
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.db_manager = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize the analysis manager."""
        if not self._initialized:
            self.db_manager = get_database_manager()
            self._initialized = True
            logger.info("Analysis manager initialized")
    
    async def run_analysis(
        self,
        session_id: str,
        config: AnalysisConfigRequest,
        user: User
    ) -> None:
        """Run analysis in background task."""
        if not self._initialized:
            await self.initialize()
        
        # Check concurrent limit
        if len(self.active_analyses) >= self.max_concurrent_analyses:
            raise Exception("Maximum concurrent analyses reached")
        
        # Create analysis task
        task = AnalysisTask(
            session_id=session_id,
            config=config,
            user=user
        )
        
        # Start analysis
        task.task = asyncio.create_task(self._execute_analysis(task))
        self.active_analyses[session_id] = task
        
        logger.info(f"Started analysis {session_id[:8]} for user {user.username}")
    
    async def _execute_analysis(self, analysis_task: AnalysisTask) -> None:
        """Execute the actual analysis."""
        session_id = analysis_task.session_id
        config = analysis_task.config
        
        try:
            # Update database status using proper ORM queries
            with self.db_manager.get_session() as db:
                from sqlalchemy import select, update
                
                # Get analysis session
                result = db.execute(
                    select(AnalysisSession).where(AnalysisSession.session_id == session_id)
                )
                analysis_session = result.scalar_one_or_none()
                
                if not analysis_session:
                    raise Exception(f"Analysis session {session_id} not found")
                
                # Update status to running
                analysis_session.start_analysis()
                analysis_task.status = "running"
                analysis_task.started_at = get_kst_now()
                
                # Create initial progress event
                initial_event = ProgressEvent(
                    session_id=session_id,
                    event_type="analysis_started",
                    message="Analysis session started",
                    stage="initialization",
                    progress_percentage=0.0
                )
                db.add(initial_event)
                
                db.commit()
            
            # Import trading system components
            try:
                from tradingagents.graph.trading_graph import TradingAgentsGraph
                from tradingagents.default_config import DEFAULT_CONFIG
            except ImportError as e:
                logger.error(f"Failed to import trading system: {e}")
                await self._fail_analysis(analysis_task, "Failed to import trading system")
                return
            
            # Create configuration for trading graph
            full_config = DEFAULT_CONFIG.copy()
            full_config.update({
                "max_debate_rounds": config.research_depth,
                "max_risk_discuss_rounds": config.research_depth,
                "llm_provider": config.llm_provider.value,
                "session_id": session_id[:8]  # Short ID for collections
            })
            
            # Initialize trading graph
            graph = TradingAgentsGraph(
                [analyst.value for analyst in config.analysts],
                config=full_config,
                debug=True
            )
            
            analysis_task.graph = graph
            
            # Create initial state
            init_state = graph.propagator.create_initial_state(
                config.ticker, 
                config.analysis_date
            )
            graph_args = graph.propagator.get_graph_args()
            
            # Update progress to data collection stage
            with self.db_manager.get_session() as db:
                result = db.execute(
                    select(AnalysisSession).where(AnalysisSession.session_id == session_id)
                )
                analysis_session = result.scalar_one_or_none()
                if analysis_session:
                    analysis_session.update_progress("data_collection", None, 10.0, "Starting data collection phase")
                    
                    # Create stage change event
                    stage_event = ProgressEvent(
                        session_id=session_id,
                        event_type="stage_change",
                        message="Entered data collection phase",
                        stage="data_collection",
                        progress_percentage=10.0
                    )
                    db.add(stage_event)
                    db.commit()
            
            # Process analysis stream
            await self._process_analysis_stream(
                analysis_task,
                graph,
                init_state,
                graph_args
            )
            
            # Complete analysis
            await self._complete_analysis(analysis_task)
            
        except Exception as e:
            logger.error(f"Analysis {session_id[:8]} failed: {e}", exc_info=True)
            await self._fail_analysis(analysis_task, str(e))
        finally:
            # Cleanup
            if session_id in self.active_analyses:
                del self.active_analyses[session_id]
            if session_id in self.message_queues:
                del self.message_queues[session_id]
    
    async def _process_analysis_stream(
        self,
        analysis_task: AnalysisTask,
        graph: Any,
        init_state: Any,
        graph_args: Dict[str, Any]
    ) -> None:
        """Process the analysis stream and update database."""
        session_id = analysis_task.session_id
        
        # Create message queue for real-time updates
        self.message_queues[session_id] = asyncio.Queue()
        
        # Process graph stream
        trace = []
        
        for chunk in graph.graph.stream(init_state, **graph_args):
            # Check if analysis was cancelled
            if analysis_task.status == "cancelled":
                break
            
            if len(chunk.get("messages", [])) > 0:
                last_message = chunk["messages"][-1]
                
                # Extract content
                if hasattr(last_message, "content"):
                    content = self._extract_content_string(last_message.content)
                    msg_type = "reasoning"
                else:
                    content = str(last_message)
                    msg_type = "system"
                
                
                # Store message in database
                agent_name = None
                if hasattr(last_message, 'name'):
                    agent_name = last_message.name
                elif 'agent' in chunk:
                    agent_name = chunk.get('agent')
                    
                await self._store_message_log(analysis_task, msg_type, content, agent_name)
                
                # Handle tool calls
                if hasattr(last_message, "tool_calls"):
                    for tool_call in last_message.tool_calls:
                        tool_name = tool_call.name if hasattr(tool_call, 'name') else tool_call.get("name", "unknown")
                        tool_args = tool_call.args if hasattr(tool_call, 'args') else tool_call.get("args", {})
                        
                        tool_message = ToolCallMessage(
                            id=str(uuid.uuid4()),
                            timestamp=get_kst_now(),
                            tool_name=tool_name,
                            args=tool_args
                        )
                        
                        
                        
                        # Store tool call in message log
                        await self._store_message_log(
                            analysis_task, 
                            "tool_call", 
                            f"Tool called: {tool_name}",
                            agent_name,
                            tool_name,
                            tool_args
                        )
                
                # Update report sections
                await self._update_report_sections(analysis_task, chunk)
                
                # Update agent statuses and progress
                await self._update_agent_statuses(analysis_task, chunk)
                
                # Update overall progress based on completed agents
                await self._update_overall_progress(analysis_task)
            
            trace.append(chunk)
        
        # Store final state
        analysis_task.final_state = trace[-1] if trace else {}
    
    async def _update_report_sections(
        self,
        analysis_task: AnalysisTask,
        chunk: Dict[str, Any]
    ) -> None:
        """Update report sections in database."""
        session_id = analysis_task.session_id
        
        # Report section mappings
        section_mappings = {
            "market_report": ("Market Analyst", "market_report"),
            "sentiment_report": ("Social Analyst", "sentiment_report"),
            "news_report": ("News Analyst", "news_report"),
            "fundamentals_report": ("Fundamentals Analyst", "fundamentals_report"),
        }
        
        # Investment debate state mappings
        investment_debate_mappings = {}
        if "investment_debate_state" in chunk:
            debate_state = chunk["investment_debate_state"]
            if "bull_history" in debate_state and debate_state["bull_history"]:
                investment_debate_mappings["bull_history"] = ("Bull Researcher", "bull_analysis")
            if "bear_history" in debate_state and debate_state["bear_history"]:
                investment_debate_mappings["bear_history"] = ("Bear Researcher", "bear_analysis")
            if "judge_decision" in debate_state and debate_state["judge_decision"]:
                investment_debate_mappings["judge_decision"] = ("Investment Judge", "judge_decision")
        
        # Final decision mappings
        final_decision_mappings = {}
        if "final_trade_decision" in chunk and chunk["final_trade_decision"]:
            final_decision_mappings["final_trade_decision"] = ("Risk Manager", "final_decision")
        if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
            final_decision_mappings["trader_investment_plan"] = ("Trader", "investment_plan")
        
        with self.db_manager.get_session() as db:
            for chunk_key, (agent_name, section_type) in section_mappings.items():
                if chunk_key in chunk and chunk[chunk_key]:
                    # Upsert: Check if report section already exists
                    existing_section = db.execute(
                        select(ReportSection).where(
                            and_(
                                ReportSection.session_id == session_id,
                                ReportSection.section_type == section_type,
                                ReportSection.agent_name == agent_name
                            )
                        )
                    ).scalar_one_or_none()
                    
                    if existing_section:
                        # Update existing section
                        existing_section.content = chunk[chunk_key]
                        existing_section.updated_at = get_kst_now()
                    else:
                        # Create new section
                        report_section = ReportSection(
                            session_id=session_id,
                            section_type=section_type,
                            agent_name=agent_name,
                            content=chunk[chunk_key]
                        )
                        db.add(report_section)
                    
                    # Create report completion event
                    report_event = ProgressEvent(
                        session_id=session_id,
                        event_type="report_completed",
                        message=f"{agent_name} completed {section_type} report",
                        agent_name=agent_name,
                        event_data={
                            "section_type": section_type,
                            "content_length": len(chunk[chunk_key])
                        }
                    )
                    db.add(report_event)
                    
                    
            
            # Process investment debate sections
            for debate_key, (agent_name, section_type) in investment_debate_mappings.items():
                content = chunk["investment_debate_state"][debate_key]
                
                # Upsert: Check if report section already exists
                existing_section = db.execute(
                    select(ReportSection).where(
                        and_(
                            ReportSection.session_id == session_id,
                            ReportSection.section_type == section_type,
                            ReportSection.agent_name == agent_name
                        )
                    )
                ).scalar_one_or_none()
                
                if existing_section:
                    # Update existing section
                    existing_section.content = content
                    existing_section.updated_at = get_kst_now()
                else:
                    # Create new section
                    report_section = ReportSection(
                        session_id=session_id,
                        section_type=section_type,
                        agent_name=agent_name,
                        content=content
                    )
                    db.add(report_section)
                
                # Create report completion event
                report_event = ProgressEvent(
                    session_id=session_id,
                    event_type="report_completed",
                    message=f"{agent_name} completed {section_type} report",
                    agent_name=agent_name,
                    event_data={
                        "section_type": section_type,
                        "content_length": len(content)
                    }
                )
                db.add(report_event)
                
                
            
            # Process final decision sections
            for decision_key, (agent_name, section_type) in final_decision_mappings.items():
                content = chunk[decision_key]
                
                # Upsert: Check if report section already exists
                existing_section = db.execute(
                    select(ReportSection).where(
                        and_(
                            ReportSection.session_id == session_id,
                            ReportSection.section_type == section_type,
                            ReportSection.agent_name == agent_name
                        )
                    )
                ).scalar_one_or_none()
                
                if existing_section:
                    # Update existing section
                    existing_section.content = content
                    existing_section.updated_at = get_kst_now()
                else:
                    # Create new section
                    report_section = ReportSection(
                        session_id=session_id,
                        section_type=section_type,
                        agent_name=agent_name,
                        content=content
                    )
                    db.add(report_section)
                
                # Create report completion event
                report_event = ProgressEvent(
                    session_id=session_id,
                    event_type="report_completed",
                    message=f"{agent_name} completed {section_type} report",
                    agent_name=agent_name,
                    event_data={
                        "section_type": section_type,
                        "content_length": len(content)
                    }
                )
                db.add(report_event)
                
              
            
            db.commit()
    
    async def _update_agent_statuses(
        self,
        analysis_task: AnalysisTask,
        chunk: Dict[str, Any]
    ) -> None:
        """Update agent execution statuses."""
        session_id = analysis_task.session_id
        
        # Determine which agents completed based on chunk content
        completed_agents = []
        
        # Basic analyst reports
        if "market_report" in chunk and chunk["market_report"]:
            completed_agents.append("Market Analyst")
        
        if "sentiment_report" in chunk and chunk["sentiment_report"]:
            completed_agents.append("Social Analyst")
        
        if "news_report" in chunk and chunk["news_report"]:
            completed_agents.append("News Analyst")
        
        if "fundamentals_report" in chunk and chunk["fundamentals_report"]:
            completed_agents.append("Fundamentals Analyst")
        
        # Investment debate agents
        if "investment_debate_state" in chunk:
            debate_state = chunk["investment_debate_state"]
            if "bull_history" in debate_state and debate_state["bull_history"]:
                completed_agents.append("Bull Researcher")
            if "bear_history" in debate_state and debate_state["bear_history"]:
                completed_agents.append("Bear Researcher")
            if "judge_decision" in debate_state and debate_state["judge_decision"]:
                completed_agents.append("Investment Judge")
        
        # Final decision agents
        if "final_trade_decision" in chunk and chunk["final_trade_decision"]:
            completed_agents.append("Risk Manager")
        
        if "trader_investment_plan" in chunk and chunk["trader_investment_plan"]:
            completed_agents.append("Trader")
        
        # Update agent executions with upsert
        with self.db_manager.get_session() as db:
            for agent_name in completed_agents:
                # Check if agent execution already exists
                existing_execution = db.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.session_id == session_id,
                            AgentExecution.agent_name == agent_name
                        )
                    )
                ).scalar_one_or_none()
                
                if existing_execution:
                    # Update existing execution
                    existing_execution.status = AgentStatus.COMPLETED
                    existing_execution.completed_at = get_kst_now()
                    existing_execution.progress_percentage = 100.0
                else:
                    # Create new execution
                    agent_execution = AgentExecution(
                        session_id=session_id,
                        agent_name=agent_name,
                        status=AgentStatus.COMPLETED,
                        started_at=analysis_task.started_at,
                        completed_at=get_kst_now(),
                        progress_percentage=100.0
                    )
                    db.add(agent_execution)
                
                # Create progress event
                progress_event = ProgressEvent(
                    session_id=session_id,
                    event_type="agent_completed",
                    message=f"{agent_name} completed analysis",
                    agent_name=agent_name,
                    progress_percentage=100.0
                )
                db.add(progress_event)
                
                # Update session progress
                result = db.execute(
                    select(AnalysisSession).where(AnalysisSession.session_id == session_id)
                )
                analysis_session = result.scalar_one_or_none()
                if analysis_session:
                    analysis_session.current_agent = agent_name
                    analysis_session.agents_completed = (analysis_session.agents_completed or 0) + 1
                
            
            
            db.commit()
    
    async def _update_overall_progress(self, analysis_task: AnalysisTask) -> None:
        """Update overall analysis progress based on completed agents."""
        session_id = analysis_task.session_id
        
        with self.db_manager.get_session() as db:
            # Get analysis session
            result = db.execute(
                select(AnalysisSession).where(AnalysisSession.session_id == session_id)
            )
            analysis_session = result.scalar_one_or_none()
            
            if not analysis_session:
                return
            
            # Calculate progress based on selected analysts
            total_agents = len(analysis_session.selected_analysts or [])
            completed_agents = analysis_session.agents_completed or 0
            
            if total_agents > 0:
                # Base progress calculation: 10% initialization + 70% analysis + 20% completion
                base_progress = 10.0  # Already set in initialization
                analysis_progress = (completed_agents / total_agents) * 70.0
                total_progress = base_progress + analysis_progress
                
                # Update stage based on progress
                if total_progress < 20:
                    stage = "data_collection"
                elif total_progress < 80:
                    stage = "analysis"
                else:
                    stage = "decision_making"
                
                # Update session progress
                old_progress = analysis_session.progress_percentage or 0
                if total_progress > old_progress:
                    analysis_session.update_progress(
                        stage, 
                        analysis_session.current_agent,
                        total_progress,
                        f"Completed {completed_agents}/{total_agents} agents"
                    )
                    
                    # Create milestone event for significant progress
                    if total_progress - old_progress >= 10:
                        milestone_event = ProgressEvent(
                            session_id=session_id,
                            event_type="milestone",
                            message=f"Analysis {total_progress:.0f}% complete",
                            stage=stage,
                            progress_percentage=total_progress,
                            event_data={
                                "completed_agents": completed_agents,
                                "total_agents": total_agents
                            }
                        )
                        db.add(milestone_event)
                
                # Estimate completion time
                analysis_session.estimate_completion_time()
            
            db.commit()
    
    async def _complete_analysis(self, analysis_task: AnalysisTask) -> None:
        """Complete analysis and update database."""
        session_id = analysis_task.session_id
        
        try:
            # Extract final decision and confidence
            final_decision = None
            confidence_score = None
            
            if hasattr(analysis_task, 'final_state') and analysis_task.final_state:
                # This would use the actual graph's signal processing methods
                # final_decision = analysis_task.graph.process_signal(final_state)
                # confidence_score = analysis_task.graph.extract_confidence_score(final_state)
                pass
            
            # Calculate execution time
            execution_time = None
            if analysis_task.started_at:
                execution_time = (get_kst_now() - analysis_task.started_at).total_seconds()
            
            # Update database with completion status
            with self.db_manager.get_session() as db:
                from sqlalchemy import select
                
                # Get and update analysis session
                result = db.execute(
                    select(AnalysisSession).where(AnalysisSession.session_id == session_id)
                )
                analysis_session = result.scalar_one_or_none()
                
                if analysis_session:
                    analysis_session.complete_analysis(final_decision, confidence_score)
                    db.commit()
            
            analysis_task.status = "completed"
            
            # Create completion progress event
            with self.db_manager.get_session() as db:
                # Update final progress
                result = db.execute(
                    select(AnalysisSession).where(AnalysisSession.session_id == session_id)
                )
                analysis_session = result.scalar_one_or_none()
                if analysis_session:
                    analysis_session.update_progress(
                        "completed", 
                        None, 
                        100.0, 
                        "Analysis completed successfully"
                    )
                
                completion_event = ProgressEvent(
                    session_id=session_id,
                    event_type="analysis_completed",
                    message="Analysis completed successfully",
                    progress_percentage=100.0,
                    event_data={
                        "final_decision": final_decision,
                        "confidence_score": confidence_score,
                        "execution_time_seconds": execution_time
                    }
                )
                db.add(completion_event)
                
                # Store completion message
                completion_message = MessageLog(
                    session_id=session_id,
                    message_type="system",
                    content=f"Analysis completed. Decision: {final_decision or 'N/A'}, Confidence: {confidence_score or 'N/A'}",
                    sequence_number=analysis_session.message_count + 1 if analysis_session else 1
                )
                db.add(completion_message)
                
                db.commit()
            
         
            
            logger.info(f"Analysis {session_id[:8]} completed successfully")
            
        except Exception as e:
            logger.error(f"Failed to complete analysis {session_id[:8]}: {e}")
            await self._fail_analysis(analysis_task, f"Completion error: {str(e)}")
    
    async def _fail_analysis(self, analysis_task: AnalysisTask, error_message: str) -> None:
        """Mark analysis as failed."""
        session_id = analysis_task.session_id
        analysis_task.status = "failed"
        
        # Update database with error
        with self.db_manager.get_session() as db:
            from sqlalchemy import select
            
            # Get and update analysis session with failure
            result = db.execute(
                select(AnalysisSession).where(AnalysisSession.session_id == session_id)
            )
            analysis_session = result.scalar_one_or_none()
            
            if analysis_session:
                analysis_session.fail_analysis(error_message)
                db.commit()
        
        # Create error progress event
        with self.db_manager.get_session() as db:
            error_event = ProgressEvent(
                session_id=session_id,
                event_type="analysis_failed",
                message=f"Analysis failed: {error_message}",
                event_data={"error_message": error_message}
            )
            db.add(error_event)
            
            # Store error message
            error_message_log = MessageLog(
                session_id=session_id,
                message_type="error",
                content=f"Analysis failed: {error_message}",
                sequence_number=1  # Will be updated by _store_message_log
            )
            db.add(error_message_log)
            
            db.commit()
        
      
        logger.error(f"Analysis {session_id[:8]} failed: {error_message}")
    
    
    def _extract_content_string(self, content: Any) -> str:
        """Extract string content from various message formats."""
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    if item.get('type') == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item.get('type') == 'tool_use':
                        text_parts.append(f"[Tool: {item.get('name', 'unknown')}]")
                else:
                    text_parts.append(str(item))
            return ' '.join(text_parts)
        else:
            return str(content)
    
    async def stop_analysis(self, session_id: str) -> bool:
        """Stop running analysis."""
        if session_id in self.active_analyses:
            analysis_task = self.active_analyses[session_id]
            analysis_task.status = "cancelled"
            
            if analysis_task.task and not analysis_task.task.done():
                analysis_task.task.cancel()
            
            logger.info(f"Stopped analysis {session_id[:8]}")
            return True
        
        return False
    
    async def pause_analysis(self, session_id: str) -> bool:
        """Pause running analysis."""
        if session_id in self.active_analyses:
            analysis_task = self.active_analyses[session_id]
            analysis_task.status = "paused"
            logger.info(f"Paused analysis {session_id[:8]}")
            return True
        
        return False
    
    async def resume_analysis(self, session_id: str) -> bool:
        """Resume paused analysis."""
        if session_id in self.active_analyses:
            analysis_task = self.active_analyses[session_id]
            analysis_task.status = "running"
            logger.info(f"Resumed analysis {session_id[:8]}")
            return True
        
        return False
    
    async def get_analysis_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get runtime status of analysis."""
        if session_id in self.active_analyses:
            analysis_task = self.active_analyses[session_id]
            return {
                "status": analysis_task.status,
                "started_at": analysis_task.started_at,
                "current_agent": None,  # Would be tracked during execution
                "last_message": None   # Would be tracked during execution
            }
        
        return None
   
    async def _store_message_log(
        self,
        analysis_task: AnalysisTask,
        message_type: str,
        content: str,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None
    ) -> None:
        """Store message log in database."""
        session_id = analysis_task.session_id
        
        with self.db_manager.get_session() as db:
            # Get current sequence number
            result = db.execute(
                select(func.max(MessageLog.sequence_number)).where(
                    MessageLog.session_id == session_id
                )
            )
            max_seq = result.scalar() or 0
            
            # Create message log entry
            message_log = MessageLog(
                session_id=session_id,
                message_type=message_type,
                content=content,
                agent_name=agent_name,
                tool_name=tool_name,
                tool_args=tool_args,
                sequence_number=max_seq + 1
            )
            db.add(message_log)
            
            # Update session message count
            result = db.execute(
                select(AnalysisSession).where(AnalysisSession.session_id == session_id)
            )
            analysis_session = result.scalar_one_or_none()
            if analysis_session:
                analysis_session.message_count = (analysis_session.message_count or 0) + 1
                analysis_session.last_message = content[:1000]  # Store truncated version
                analysis_session.last_message_timestamp = get_kst_now()
            
            db.commit()
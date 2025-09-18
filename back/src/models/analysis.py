"""Analysis-related database src.models."""

import datetime
import uuid
from enum import Enum
from typing import Optional, Dict, Any, List
from sqlalchemy import String, Integer, Float, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .base import Base, get_kst_now, JSONType


class AnalysisStatus(str, Enum):
    """Analysis session status enumeration."""
    PENDING = "pending"
    RUNNING = "running" 
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class AgentStatus(str, Enum):
    """Agent execution status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TradeDecision(str, Enum):
    """Trade decision enumeration."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class ReportSectionType(str, Enum):
    """Report section type enumeration."""
    MARKET_REPORT = "market_report"
    SENTIMENT_REPORT = "sentiment_report"
    NEWS_REPORT = "news_report"
    FUNDAMENTALS_REPORT = "fundamentals_report"
    INVESTMENT_PLAN = "investment_plan"
    TRADER_INVESTMENT_PLAN = "trader_investment_plan"
    FINAL_TRADE_DECISION = "final_trade_decision"
    RISK_ANALYSIS = "risk_analysis"
    PORTFOLIO_RECOMMENDATION = "portfolio_recommendation"


class AnalysisSession(Base):
    """Analysis session model for tracking trading analysis runs."""
    
    __tablename__ = "analysis_sessions"
    
    # Primary identification
    session_id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    
    # Analysis parameters
    ticker: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    analysis_date: Mapped[datetime.datetime] = mapped_column(DateTime, nullable=False, index=True)
    
    # Analysis configuration
    config_snapshot: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    selected_analysts: Mapped[Optional[List[str]]] = mapped_column(JSONType, nullable=True)
    research_depth: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    llm_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Session status and timing
    status: Mapped[AnalysisStatus] = mapped_column(String(20), default=AnalysisStatus.PENDING, index=True)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    execution_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Progress tracking (NEW)
    current_stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # initialization, data_collection, analysis, decision_making
    current_agent: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # currently active agent
    progress_percentage: Mapped[Optional[float]] = mapped_column(Float, default=0.0)  # 0.0 to 100.0
    estimated_completion_seconds: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)  # estimated remaining time
    
    # Message tracking (NEW)
    last_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # last message from analysis
    last_message_timestamp: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    message_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)  # total messages generated
    
    # Results
    final_decision: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # 0.0 to 1.0
    confidence_level: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)  # Low, Medium, High
    
    # Analysis metrics
    llm_call_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tool_call_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    agents_completed: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    agents_failed: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    
    # Performance metrics (NEW)
    total_tokens_used: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    peak_memory_mb: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Error information
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    
    # Metadata
    client_ip: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="analysis_sessions")
    report_sections: Mapped[List["ReportSection"]] = relationship(
        "ReportSection", back_populates="analysis_session", cascade="all, delete-orphan"
    )
    agent_executions: Mapped[List["AgentExecution"]] = relationship(
        "AgentExecution", back_populates="analysis_session", cascade="all, delete-orphan"
    )
    progress_events: Mapped[List["ProgressEvent"]] = relationship(
        "ProgressEvent", back_populates="analysis_session", cascade="all, delete-orphan"
    )
    message_logs: Mapped[List["MessageLog"]] = relationship(
        "MessageLog", back_populates="analysis_session", cascade="all, delete-orphan"
    )
    
    def start_analysis(self) -> None:
        """Mark analysis as started."""
        self.status = AnalysisStatus.RUNNING
        self.started_at = get_kst_now()
        self.current_stage = "initialization"
        self.progress_percentage = 0.0
    
    def complete_analysis(self, final_decision: Optional[str] = None, 
                         confidence_score: Optional[float] = None) -> None:
        """Mark analysis as completed."""
        self.status = AnalysisStatus.COMPLETED
        self.completed_at = get_kst_now()
        if self.started_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
        if final_decision:
            self.final_decision = final_decision
        if confidence_score:
            self.confidence_score = confidence_score
            self.confidence_level = self._get_confidence_level(confidence_score)
    
    def fail_analysis(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark analysis as failed."""
        self.status = AnalysisStatus.FAILED
        self.completed_at = get_kst_now()
        if self.started_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
        self.error_message = error_message
        self.error_details = error_details
    
    def cancel_analysis(self) -> None:
        """Cancel analysis."""
        self.status = AnalysisStatus.CANCELLED
        self.completed_at = get_kst_now()
        if self.started_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
    
    def pause_analysis(self) -> None:
        """Pause analysis."""
        self.status = AnalysisStatus.PAUSED
    
    def resume_analysis(self) -> None:
        """Resume paused analysis."""
        self.status = AnalysisStatus.RUNNING
    
    def _get_confidence_level(self, score: float) -> str:
        """Convert confidence score to level."""
        if score >= 0.8:
            return "High"
        elif score >= 0.6:
            return "Medium"
        else:
            return "Low"
    
    @property
    def is_running(self) -> bool:
        """Check if analysis is currently running."""
        return self.status == AnalysisStatus.RUNNING
    
    @property
    def is_completed(self) -> bool:
        """Check if analysis is completed."""
        return self.status == AnalysisStatus.COMPLETED
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Get analysis duration in minutes."""
        if self.execution_time_seconds:
            return round(self.execution_time_seconds / 60, 2)
        return None
    
    def update_progress(self, stage: str, agent: Optional[str] = None, 
                      progress: Optional[float] = None, message: Optional[str] = None) -> None:
        """Update analysis progress."""
        self.current_stage = stage
        if agent:
            self.current_agent = agent
        if progress is not None:
            self.progress_percentage = min(100.0, max(0.0, progress))
        if message:
            self.last_message = message
            self.last_message_timestamp = get_kst_now()
            self.message_count = (self.message_count or 0) + 1
    
    def estimate_completion_time(self) -> Optional[int]:
        """Estimate remaining completion time in seconds."""
        if not self.started_at or not self.progress_percentage or self.progress_percentage <= 0:
            return None
        
        elapsed = (get_kst_now() - self.started_at).total_seconds()
        if self.progress_percentage >= 100:
            return 0
        
        estimated_total = elapsed / (self.progress_percentage / 100)
        remaining = max(0, estimated_total - elapsed)
        self.estimated_completion_seconds = int(remaining)
        return self.estimated_completion_seconds


class ReportSection(Base):
    """Report section model for storing analysis outputs."""
    
    __tablename__ = "report_sections"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.session_id"), nullable=False, index=True)
    
    # Section identification
    section_type: Mapped[ReportSectionType] = mapped_column(String(50), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Content
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_length: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)  # For deduplication
    
    # Metadata
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_final: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Analysis metadata
    llm_model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    processing_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    analysis_session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="report_sections")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.content:
            self.content_length = len(self.content)
            # Generate content hash for deduplication
            import hashlib
            self.content_hash = hashlib.sha256(self.content.encode()).hexdigest()[:16]


class AgentExecution(Base):
    """Agent execution tracking model."""
    
    __tablename__ = "agent_executions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.session_id"), nullable=False, index=True)
    
    # Agent identification
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    agent_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # analyst, researcher, trader, risk
    agent_team: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Execution status and timing
    status: Mapped[AgentStatus] = mapped_column(String(20), default=AgentStatus.PENDING)
    started_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime, nullable=True)
    execution_time_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Progress tracking (NEW)
    current_task: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)  # what the agent is currently doing
    progress_percentage: Mapped[Optional[float]] = mapped_column(Float, default=0.0)  # 0.0 to 100.0
    
    # Execution metrics
    llm_calls: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tool_calls: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # cost for this agent execution
    
    # Results and errors
    output_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_details: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    
    # Configuration
    model_config: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    
    # Relationships
    analysis_session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="agent_executions")
    
    def start_execution(self, task: Optional[str] = None) -> None:
        """Mark agent execution as started."""
        self.status = AgentStatus.RUNNING
        self.started_at = get_kst_now()
        self.progress_percentage = 0.0
        if task:
            self.current_task = task
    
    def complete_execution(self, output_summary: Optional[str] = None) -> None:
        """Mark agent execution as completed."""
        self.status = AgentStatus.COMPLETED
        self.completed_at = get_kst_now()
        if self.started_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
        if output_summary:
            self.output_summary = output_summary
    
    def fail_execution(self, error_message: str, error_details: Optional[Dict[str, Any]] = None) -> None:
        """Mark agent execution as failed."""
        self.status = AgentStatus.FAILED
        self.completed_at = get_kst_now()
        if self.started_at:
            self.execution_time_seconds = (self.completed_at - self.started_at).total_seconds()
        self.error_message = error_message
        self.error_details = error_details
    
    def skip_execution(self, reason: Optional[str] = None) -> None:
        """Mark agent execution as skipped."""
        self.status = AgentStatus.SKIPPED
        if reason:
            self.output_summary = f"Skipped: {reason}"
    
    @property
    def duration_minutes(self) -> Optional[float]:
        """Get execution duration in minutes."""
        if self.execution_time_seconds:
            return round(self.execution_time_seconds / 60, 2)
        return None
    
    def update_progress(self, progress: float, task: Optional[str] = None) -> None:
        """Update agent execution progress."""
        self.progress_percentage = min(100.0, max(0.0, progress))
        if task:
            self.current_task = task


class ProgressEvent(Base):
    """Progress event tracking for real-time updates."""
    
    __tablename__ = "progress_events"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.session_id"), nullable=False, index=True)
    
    # Event information
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)  # stage_change, agent_start, agent_complete, milestone, etc.
    event_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Context
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    stage: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    progress_percentage: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Relationships
    analysis_session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="progress_events")


class MessageLog(Base):
    """Message log for storing analysis messages chronologically."""
    
    __tablename__ = "message_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("analysis_sessions.session_id"), nullable=False, index=True)
    
    # Message information
    message_type: Mapped[str] = mapped_column(String(50), nullable=False)  # system, reasoning, tool_call, error, etc.
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Context
    agent_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tool_args: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    
    # Metadata
    sequence_number: Mapped[int] = mapped_column(Integer, nullable=False)  # for ordering
    
    # Relationships
    analysis_session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="message_logs")


# Import user models to establish relationships (avoid circular imports)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .user import User
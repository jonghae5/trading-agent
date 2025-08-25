"""Analysis-related Pydantic src.schemas."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, ConfigDict
from datetime import datetime
from enum import Enum


class AnalystType(str, Enum):
    """Analyst type enumeration."""
    MARKET = "market"
    SOCIAL = "social"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"
    BEN_GRAHAM = "ben_graham"
    WARREN_BUFFETT = "warren_buffett"


class LLMProvider(str, Enum):
    """LLM provider enumeration."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


class AnalysisStatus(str, Enum):
    """Analysis status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class AgentStatus(str, Enum):
    """Agent status enumeration."""
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
    BEN_GRAHAM_REPORT = "ben_graham_report"
    WARREN_BUFFETT_REPORT = "warren_buffett_report"
    BULL_ANALYSIS = "bull_analysis"
    BEAR_ANALYSIS = "bear_analysis"
    JUDGE_DECISION = "judge_decision"
    FINAL_DECISION = "final_decision"
    INVESTMENT_PLAN = "investment_plan"
    TRADER_INVESTMENT_PLAN = "trader_investment_plan"
    FINAL_TRADE_DECISION = "final_trade_decision"


class AnalysisConfigRequest(BaseModel):
    """Analysis configuration request."""
    ticker: str = Field(..., min_length=1, max_length=20, description="Stock ticker symbol")
    analysis_date: str = Field(..., description="Analysis date in YYYY-MM-DD format")
    analysts: List[AnalystType] = Field(..., min_items=1, description="Selected analysts")
    research_depth: int = Field(3, ge=1, le=10, description="Research depth (1-10)")
    llm_provider: LLMProvider = Field(LLMProvider.OPENAI, description="LLM provider")
    shallow_thinker: str = Field("gpt-4o", description="Model for quick analysis")
    deep_thinker: str = Field("gpt-4o", description="Model for deep analysis")
    backend_url: Optional[str] = Field(None, description="Custom backend URL")
    
    @validator('ticker')
    def validate_ticker(cls, v):
        """Validate ticker format."""
        ticker = v.upper().strip()
        if not ticker.isalnum():
            raise ValueError('Ticker must contain only alphanumeric characters')
        if len(ticker) > 10:
            raise ValueError('Ticker must be 10 characters or less')
        return ticker
    
    @validator('analysis_date')
    def validate_analysis_date(cls, v):
        """Validate analysis date format."""
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('Analysis date must be in YYYY-MM-DD format')


class AnalysisStartRequest(BaseModel):
    """Analysis start request."""
    config: AnalysisConfigRequest
    client_metadata: Optional[Dict[str, Any]] = None


class AnalysisControlRequest(BaseModel):
    """Analysis control request."""
    session_id: str = Field(..., description="Analysis session ID")
    action: str = Field(..., description="Control action: stop, pause, resume")


class AgentExecutionResponse(BaseModel):
    """Agent execution response."""
    id: int
    agent_name: str
    agent_type: Optional[str] = None
    agent_team: Optional[str] = None
    status: AgentStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    
    # Progress tracking (NEW)
    current_task: Optional[str] = None
    progress_percentage: Optional[float] = None
    
    llm_calls: Optional[int] = None
    tool_calls: Optional[int] = None
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None
    output_summary: Optional[str] = None
    error_message: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class ReportSectionResponse(BaseModel):
    """Report section response."""
    id: int
    section_type: ReportSectionType
    agent_name: str
    content: str
    content_length: int
    version: int
    is_final: bool
    llm_model: Optional[str] = None
    processing_time_seconds: Optional[float] = None
    confidence_score: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisResponse(BaseModel):
    """Analysis session response."""
    session_id: str
    username: str
    ticker: str
    analysis_date: datetime
    status: AnalysisStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time_seconds: Optional[float] = None
    
    # Progress tracking (NEW)
    current_stage: Optional[str] = None
    current_agent: Optional[str] = None
    progress_percentage: Optional[float] = None
    estimated_completion_seconds: Optional[int] = None
    
    # Message tracking (NEW)
    last_message: Optional[str] = None
    last_message_timestamp: Optional[datetime] = None
    message_count: Optional[int] = None
    
    final_decision: Optional[str] = None
    confidence_score: Optional[float] = None
    confidence_level: Optional[str] = None
    llm_call_count: Optional[int] = None
    tool_call_count: Optional[int] = None
    agents_completed: Optional[int] = None
    agents_failed: Optional[int] = None
    
    # Performance metrics (NEW)
    total_tokens_used: Optional[int] = None
    total_cost_usd: Optional[float] = None
    peak_memory_mb: Optional[float] = None
    
    error_message: Optional[str] = None
    config_snapshot: Optional[Dict[str, Any]] = None
    created_at: datetime
    
    # Related data
    report_sections: Optional[List[ReportSectionResponse]] = None
    agent_executions: Optional[List[AgentExecutionResponse]] = None
    progress_events: Optional[List["ProgressEventResponse"]] = None
    message_logs: Optional[List["MessageLogResponse"]] = None
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisStatusResponse(BaseModel):
    """Analysis status response."""
    session_id: str
    status: AnalysisStatus
    current_stage: Optional[str] = None  # NEW
    current_agent: Optional[str] = None
    progress_percentage: Optional[float] = None
    started_at: Optional[datetime] = None
    elapsed_seconds: Optional[float] = None
    estimated_remaining_seconds: Optional[float] = None
    
    # Enhanced metrics (NEW)
    llm_call_count: int = 0
    tool_call_count: int = 0
    total_tokens_used: int = 0
    total_cost_usd: Optional[float] = None
    message_count: int = 0
    
    agents_status: Dict[str, AgentStatus] = {}
    agents_progress: Dict[str, float] = {}  # NEW: progress per agent
    agents_tasks: Dict[str, str] = {}      # NEW: current task per agent
    
    last_message: Optional[str] = None
    last_message_timestamp: Optional[datetime] = None  # NEW
    error_message: Optional[str] = None


class AnalysisListResponse(BaseModel):
    """Analysis list response."""
    sessions: List[AnalysisResponse]
    total: int
    page: int = 1
    per_page: int = 50
    pages: int
    has_next: bool
    has_prev: bool


class AnalysisMetricsResponse(BaseModel):
    """Analysis metrics response."""
    total_analyses: int
    completed_analyses: int
    failed_analyses: int
    running_analyses: int
    average_execution_time_minutes: Optional[float] = None
    success_rate_percentage: float
    most_analyzed_ticker: Optional[str] = None
    decision_distribution: Dict[str, int] = {}
    average_confidence_score: Optional[float] = None


class AnalysisMessage(BaseModel):
    """Analysis message for real-time streaming."""
    id: str
    timestamp: datetime
    type: str  # system, reasoning, tool, error, analysis
    content: str
    agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolCallMessage(BaseModel):
    """Tool call message for real-time streaming."""
    id: str
    timestamp: datetime
    tool_name: str
    args: Dict[str, Any]
    result: Optional[Any] = None
    error: Optional[str] = None


class AgentUpdateMessage(BaseModel):
    """Agent status update message."""
    agent_name: str
    status: AgentStatus
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ReportUpdateMessage(BaseModel):
    """Report section update message."""
    section_type: ReportSectionType
    agent_name: str
    content: str
    is_final: bool
    timestamp: datetime


class AnalysisCompletedMessage(BaseModel):
    """Analysis completion message."""
    session_id: str
    status: AnalysisStatus
    final_decision: Optional[str] = None
    confidence_score: Optional[float] = None
    execution_time_seconds: Optional[float] = None
    timestamp: datetime


class ProgressEventResponse(BaseModel):
    """Progress event response."""
    id: int
    event_type: str
    event_data: Optional[Dict[str, Any]] = None
    message: Optional[str] = None
    agent_name: Optional[str] = None
    stage: Optional[str] = None
    progress_percentage: Optional[float] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class MessageLogResponse(BaseModel):
    """Message log response."""
    id: int
    message_type: str
    content: str
    agent_name: Optional[str] = None
    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    sequence_number: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AnalysisStatsResponse(BaseModel):
    """User analysis statistics."""
    username: str
    ticker: Optional[str] = None
    period_days: int
    total_analyses: int
    decision_distribution: Dict[str, int]
    average_confidence: Optional[float] = None
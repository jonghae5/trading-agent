// Core trading system types
export interface User {
  id: number
  username: string
}

// Analysis Configuration Types
export enum AnalystType {
  MARKET = 'market',
  SOCIAL = 'social',
  NEWS = 'news',
  FUNDAMENTALS = 'fundamentals'
}

export enum LLMProvider {
  OPENAI = 'openai',
  ANTHROPIC = 'anthropic',
  GOOGLE = 'google',
  OPENROUTER = 'openrouter',
  OLLAMA = 'ollama'
}

export interface AnalysisConfig {
  ticker: string
  analysisDate: string
  analysts: AnalystType[]
  researchDepth: number
  llmProvider: LLMProvider
  shallowThinker: string
  deepThinker: string
  backendUrl: string
  customInstructions?: string
}

// Agent Status Types
export enum AgentStatus {
  PENDING = 'pending',
  IN_PROGRESS = 'in_progress',
  COMPLETED = 'completed',
  ERROR = 'error'
}

export interface Agent {
  name: string
  status: AgentStatus
  team: AgentTeam
  displayName: string
}

export enum AgentTeam {
  ANALYSIS = 'analysis',
  RESEARCH = 'research',
  TRADING = 'trading',
  RISK = 'risk',
  PORTFOLIO = 'portfolio'
}

// Analysis Stream Types
export interface AnalysisMessage {
  id: string
  timestamp: string
  type: 'system' | 'reasoning' | 'tool' | 'error' | 'analysis'
  content: string
  agent?: string
}

export interface ToolCall {
  id: string
  timestamp: string
  toolName: string
  args: Record<string, any>
}

// Report Types
export interface ReportSection {
  type: ReportSectionType
  agentName: string
  content: string
  timestamp: Date
}

export enum ReportSectionType {
  MARKET_REPORT = 'market_report',
  SENTIMENT_REPORT = 'sentiment_report',
  NEWS_REPORT = 'news_report',
  FUNDAMENTALS_REPORT = 'fundamentals_report',
  INVESTMENT_PLAN = 'investment_plan',
  TRADER_INVESTMENT_PLAN = 'trader_investment_plan',
  FINAL_TRADE_DECISION = 'final_trade_decision'
}

export interface AnalysisSession {
  id: string
  username: string
  ticker: string
  analysisDate: string
  config: AnalysisConfig
  finalDecision?: string
  confidenceScore?: string
  executionTime?: number
  createdAt: Date
  completedAt?: Date
  reports: ReportSection[]
}

// Stream Processing Types
export interface AnalysisState {
  isRunning: boolean
  isPaused: boolean
  currentAgent?: string
  progress: number
  startTime?: Date
  endTime?: Date
  messages: AnalysisMessage[]
  toolCalls: ToolCall[]
  agentStatus: Record<string, AgentStatus>
  reportSections: Record<ReportSectionType, ReportSection | null>
  llmCallCount: number
  toolCallCount: number
}

// API Response Types
export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface StockSearchResult {
  symbol: string
  name: string
  exchange: string
  currency: string
  type: string
}

export interface ErrorData {
  message?: string
  detail?: string
  [key: string]: unknown
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

// Market Data Types
export interface MarketData {
  ticker: string
  price: number
  change: number
  changePercent: number
  volume: number
  marketCap: number
  pe: number
  timestamp: Date
}

export interface EconomicIndicator {
  name: string
  value: number
  change: number
  changePercent: number
  date: Date
}

// Theme and UI Types
export enum Theme {
  LIGHT = 'light',
  DARK = 'dark'
}

export interface UIPreferences {
  theme: Theme
  sidebarCollapsed: boolean
  autoRefresh: boolean
  notifications: boolean
}

// Real-time Socket Events
export interface SocketEvents {
  // Client to Server
  'analysis:start': AnalysisConfig
  'analysis:stop': void
  'analysis:pause': void
  'analysis:resume': void

  // Server to Client
  'analysis:status': AnalysisState
  'analysis:message': AnalysisMessage
  'analysis:tool-call': ToolCall
  'analysis:agent-update': { agent: string; status: AgentStatus }
  'analysis:report-update': { section: ReportSectionType; content: string }
  'analysis:completed': AnalysisSession
  'analysis:error': { error: string; details?: any }
}

// Form Validation Types
export interface ValidationError {
  field: string
  message: string
}

export interface FormState<T> {
  data: T
  errors: ValidationError[]
  isValid: boolean
  isDirty: boolean
  isSubmitting: boolean
}

// Enhanced Analysis Types for Real-time Features
export interface MessageLog {
  id: number
  message_type: 'system' | 'reasoning' | 'tool_call' | 'error' | 'analysis'
  content: string
  agent_name?: string
  tool_name?: string
  tool_args?: Record<string, any>
  sequence_number: number
  created_at: Date
}

export interface ProgressEvent {
  id: number
  event_type:
    | 'stage_change'
    | 'agent_started'
    | 'agent_completed'
    | 'milestone'
    | 'report_completed'
    | 'error_occurred'
    | 'system_event'
  event_data?: Record<string, any>
  message?: string
  agent_name?: string
  stage?: string
  progress_percentage?: number
  created_at: Date
}

export interface EnhancedAgentExecution {
  id: number
  agent_name: string
  agent_type?: string
  agent_team?: string
  status: AgentStatus
  started_at?: Date
  completed_at?: Date
  execution_time_seconds?: number

  // Enhanced progress tracking
  current_task?: string
  progress_percentage?: number

  llm_calls?: number
  tool_calls?: number
  tokens_used?: number
  cost_usd?: number
  output_summary?: string
  error_message?: string
}

export interface EnhancedAnalysisStatus {
  session_id: string
  status:
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'cancelled'
    | 'paused'

  // Enhanced progress information
  current_stage?: string
  current_agent?: string
  progress_percentage?: number
  estimated_completion_seconds?: number

  // Message tracking
  last_message?: string
  last_message_timestamp?: Date
  message_count?: number

  // Detailed metrics
  llm_call_count: number
  tool_call_count: number
  total_tokens_used: number
  total_cost_usd?: number

  // Agent status with enhanced data
  agents_status: Record<string, AgentStatus>
  agents_progress: Record<string, number>
  agents_tasks: Record<string, string>

  started_at?: Date
  elapsed_seconds?: number
  estimated_remaining_seconds?: number
  error_message?: string

  // Related data arrays
  message_logs?: MessageLog[]
  progress_events?: ProgressEvent[]
  agent_executions?: EnhancedAgentExecution[]
}

export interface AnalysisMetrics {
  session_id: string
  llm_call_count: number
  tool_call_count: number
  message_count: number
  total_tokens_used: number
  total_cost_usd?: number
  peak_memory_mb?: number
  agents_completed: number
  agents_failed: number
  execution_time_seconds?: number

  // Real-time metrics
  tokens_per_minute?: number
  calls_per_minute?: number
  average_response_time_ms?: number
  error_rate_percentage?: number
}

// Real-time streaming message types
export interface StreamMessage {
  type:
    | 'message'
    | 'progress'
    | 'agent_update'
    | 'metrics'
    | 'error'
    | 'completed'
  session_id: string
  timestamp: Date
  data: any
}

export interface MessageStreamMessage extends StreamMessage {
  type: 'message'
  data: MessageLog
}

export interface ProgressStreamMessage extends StreamMessage {
  type: 'progress'
  data: ProgressEvent
}

export interface AgentUpdateStreamMessage extends StreamMessage {
  type: 'agent_update'
  data: {
    agent_name: string
    status: AgentStatus
    current_task?: string
    progress_percentage?: number
  }
}

export interface MetricsStreamMessage extends StreamMessage {
  type: 'metrics'
  data: AnalysisMetrics
}

// News Types for Fred API Integration
export interface NewsArticle {
  id: string
  title: string
  summary?: string
  sentiment: 'positive' | 'negative' | 'neutral'
  source: string
  published_at: string
  relevance_score: number
  tags: string[]
  url?: string
  ticker_sentiment?: Record<string, any>
}

export interface NewsCategory {
  id: string
  name: string
  description: string
  icon: string
  count: number
}

export interface NewsSearchFilters {
  query?: string
  sentiment?: 'positive' | 'negative' | 'neutral' | 'all'
  source?: string
  dateFrom?: string
  dateTo?: string
  limit?: number
}

export interface NewsSearchResult {
  articles: NewsArticle[]
  total: number
  hasMore: boolean
  searchQuery?: string
}

export interface NewsResponse {
  success: boolean
  data: {
    latest_news: NewsArticle[]
  }
  message?: string
}

// Utility Types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>

export type OptionalFields<T, K extends keyof T> = Omit<T, K> &
  Partial<Pick<T, K>>

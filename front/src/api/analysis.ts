/**
 * Analysis API endpoints
 */

import { apiClient } from './client'
import {
  AnalystType,
  LLMProvider,
  EnhancedAnalysisStatus,
  MessageLog,
  ProgressEvent,
  AnalysisMetrics,
  EnhancedAgentExecution
} from '../types'

export interface AnalysisConfig {
  ticker: string
  analysis_date: string
  analysts: AnalystType[]
  research_depth: number
  llm_provider: LLMProvider
  shallow_model?: string
  deep_model?: string
  custom_instructions?: string
}

export interface AnalysisStartRequest {
  config: AnalysisConfig
  client_metadata?: {
    ip?: string
    user_agent?: string
  }
}

export interface AnalysisControlRequest {
  session_id: string
  action: 'stop' | 'pause'
}

export interface AnalysisResponse {
  session_id: string
  user_id: number
  username: string
  ticker: string
  analysis_date: string
  status:
    | 'pending'
    | 'running'
    | 'completed'
    | 'failed'
    | 'cancelled'
    | 'paused'
  config_snapshot: AnalysisConfig
  selected_analysts: string[]
  research_depth: number
  llm_provider: string
  created_at: string
  started_at?: string
  completed_at?: string
  execution_time_seconds?: number
  llm_call_count?: number
  tool_call_count?: number
  agents_completed?: number
  confidence_score?: number
  final_decision?: 'buy' | 'sell' | 'hold'
  error_message?: string
  client_ip?: string
  user_agent?: string
}

export interface AnalysisStatusResponse {
  session_id: string
  status: string
  current_agent?: string
  progress_percentage: number
  started_at?: string
  elapsed_seconds?: number
  estimated_remaining_seconds?: number
  llm_call_count: number
  tool_call_count: number
  agents_status: Record<string, string>
  last_message?: string
  error_message?: string
}

export interface AnalysisListResponse {
  sessions: AnalysisResponse[]
  total: number
  page: number
  per_page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

export interface AnalysisMetricsResponse {
  total_analyses: number
  completed_analyses: number
  failed_analyses: number
  running_analyses: number
  average_execution_time_minutes?: number
  success_rate_percentage: number
  most_analyzed_ticker?: string
  decision_distribution: Record<string, number>
  average_confidence_score?: number
}

export interface ReportSection {
  id: number
  session_id: string
  section_name: string
  agent_name: string
  content: string
  created_at: string
  order_index: number
}

export interface AgentExecution {
  id: number
  session_id: string
  agent_name: string
  status: string
  started_at?: string
  completed_at?: string
  execution_time_seconds?: number
  llm_calls_count: number
  tool_calls_count: number
  error_message?: string
  output_data?: any
}

export const analysisApi = {
  async startAnalysis(
    request: AnalysisStartRequest
  ): Promise<AnalysisResponse> {
    return await apiClient.post<AnalysisResponse>(
      '/api/v1/analysis/start',
      request
    )
  },

  async controlAnalysis(
    request: AnalysisControlRequest
  ): Promise<{ success: boolean; message: string }> {
    return await apiClient.post('/api/v1/analysis/control', request)
  },

  async getAnalysisStatus(sessionId: string): Promise<AnalysisStatusResponse> {
    return await apiClient.get<AnalysisStatusResponse>(
      `/api/v1/analysis/status/${sessionId}`
    )
  },

  // Enhanced analysis status with real-time data
  async getEnhancedAnalysisStatus(
    sessionId: string
  ): Promise<EnhancedAnalysisStatus> {
    return await apiClient.get<EnhancedAnalysisStatus>(
      `/api/v1/analysis/enhanced-status/${sessionId}`
    )
  },

  // Get message logs for a session
  async getMessageLogs(
    sessionId: string,
    params?: {
      page?: number
      per_page?: number
      message_type?: string
      agent_name?: string
      order?: 'asc' | 'desc'
    }
  ): Promise<{
    items: MessageLog[]
    total: number
    page: number
    per_page: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }> {
    return await apiClient.get(`/api/v1/analysis/${sessionId}/messages`, params)
  },

  // Get progress events for a session
  async getProgressEvents(
    sessionId: string,
    params?: {
      page?: number
      per_page?: number
      event_type?: string
      agent_name?: string
      stage?: string
    }
  ): Promise<{
    items: ProgressEvent[]
    total: number
    page: number
    per_page: number
    pages: number
    has_next: boolean
    has_prev: boolean
  }> {
    return await apiClient.get(`/api/v1/analysis/${sessionId}/events`, params)
  },

  // Get enhanced agent executions
  async getEnhancedAgentExecutions(
    sessionId: string
  ): Promise<EnhancedAgentExecution[]> {
    return await apiClient.get<EnhancedAgentExecution[]>(
      `/api/v1/analysis/${sessionId}/agents`
    )
  },

  async getAnalysisSessions(params?: {
    ticker?: string
    status?: string
    page?: number
    per_page?: number
    include_reports?: boolean
    include_agents?: boolean
  }): Promise<AnalysisListResponse> {
    return await apiClient.get<AnalysisListResponse>(
      '/api/v1/analysis/sessions',
      params
    )
  },

  async getAnalysisSession(
    sessionId: string,
    params?: {
      include_reports?: boolean
      include_agents?: boolean
    }
  ): Promise<AnalysisResponse> {
    return await apiClient.get<AnalysisResponse>(
      `/api/v1/analysis/${sessionId}`,
      params
    )
  },

  async deleteAnalysisSession(
    sessionId: string
  ): Promise<{ success: boolean; message: string }> {
    return await apiClient.delete(`/api/v1/analysis/${sessionId}`)
  },

  async getAnalysisMetricsSummary(
    days: number = 30
  ): Promise<AnalysisMetricsResponse> {
    return await apiClient.get<AnalysisMetricsResponse>(
      '/api/v1/analysis/metrics/summary',
      { days }
    )
  },

  async validateAnalysisConfig(config: AnalysisConfig): Promise<{
    success: boolean
    message: string
    data: {
      valid: boolean
      errors: string[]
      warnings: string[]
    }
  }> {
    return await apiClient.get('/api/v1/analysis/config/validate', { config })
  },

  // Get live session data for analysis page
  async getLiveSessionData(
    sessionId: string,
    params?: {
      include_messages?: boolean
      message_limit?: number
    }
  ): Promise<{
    success: boolean
    message: string
    data: {
      session_id: string
      status: string
      ticker: string
      analysis_date: string
      current_agent?: string
      progress_percentage: number
      started_at?: string
      completed_at?: string
      elapsed_seconds?: number
      estimated_remaining_seconds?: number
      llm_call_count: number
      tool_call_count: number
      agents_status: Record<string, string>
      agents_completed: number
      agents_failed: number
      selected_analysts: string[]
      final_decision?: string
      confidence_score?: number
      confidence_level?: string
      error_message?: string
      last_message?: string
      last_message_timestamp?: string
      created_at: string
      messages?: MessageLog[]
      report_sections: ReportSection[]
      agent_executions: AgentExecution[]
    }
  }> {
    return await apiClient.get(`/api/v1/analysis/${sessionId}/live`, params)
  }
}

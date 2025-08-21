/**
 * History/Reports API functions
 */

import { apiClient, ApiResponse, handleApiResponse } from './client'
import { AnalysisListResponse } from './analysis'

// Types for analysis history
export interface AnalysisSession {
  session_id: string
  username: string
  ticker: string
  analysis_date: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  selected_analysts: string[]
  research_depth: number
  llm_provider: string
  config_snapshot: Record<string, any>

  // Timing information
  created_at: string
  started_at?: string
  completed_at?: string
  execution_time_seconds?: number

  // Results
  final_decision?: string
  confidence_score?: number

  // Metrics
  llm_call_count?: number
  tool_call_count?: number
  agents_completed?: number

  // Error information
  error_message?: string

  // Related data (when included)
  report_sections?: HistoryReportSection[]
  agent_executions?: HistoryAgentExecution[]
}

export interface HistoryReportSection {
  id: number
  section_type: string
  agent_name: string
  content: string
  content_length: number
  version: number
  is_final: boolean
  llm_model?: string
  processing_time_seconds?: number
  confidence_score?: number
  created_at: string
}

export interface HistoryAgentExecution {
  execution_id: string
  session_id: string
  agent_name: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  started_at?: string
  completed_at?: string
  execution_time_seconds?: number
  llm_calls?: number
  tool_calls?: number
  error_message?: string
}

export interface HistoryAnalysisListResponse {
  sessions: AnalysisSession[]
  total: number
  page: number
  per_page: number
  pages: number
  has_next: boolean
  has_prev: boolean
}

export interface AnalysisStatsResponse {
  username: string
  ticker?: string
  period_days: number
  total_analyses: number
  decision_distribution: Record<string, number>
  average_confidence?: number
}

// History API functions
export const historyApi = {
  // Get analysis history with pagination and filters (lightweight - no related data)
  async getHistory(
    params: {
      ticker?: string | null
      page?: number
      per_page?: number
    } = {}
  ): Promise<HistoryAnalysisListResponse> {
    const response = await apiClient.get<
      ApiResponse<HistoryAnalysisListResponse>
    >('/api/v1/reports/history', params)

    return handleApiResponse(response)
  },

  // Get specific analysis report by session ID (includes all related data)
  async getAnalysisReport(sessionId: string): Promise<AnalysisSession> {
    const response = await apiClient.get<ApiResponse<AnalysisSession>>(
      `/api/v1/reports/${sessionId}`
    )
    return handleApiResponse(response)
  },

  // Get report sections for a specific analysis
  async getReportSections(
    sessionId: string,
    sectionType?: string
  ): Promise<HistoryReportSection[]> {
    const params = sectionType ? { section_type: sectionType } : undefined
    const response = await apiClient.get<ApiResponse<HistoryReportSection[]>>(
      `/api/v1/reports/${sessionId}/sections`,
      params
    )
    return handleApiResponse(response)
  },

  // Get analysis statistics
  async getAnalysisStats(
    params: {
      ticker?: string
      days?: number
    } = {}
  ): Promise<AnalysisStatsResponse> {
    const response = await apiClient.get<ApiResponse<AnalysisStatsResponse>>(
      '/api/v1/reports/stats/summary',
      params
    )
    return handleApiResponse(response)
  },

  // Export analysis report
  async exportAnalysisReport(
    sessionId: string,
    format: 'json' | 'pdf' | 'html' = 'json'
  ): Promise<any> {
    const response = await apiClient.get(
      `/api/v1/reports/${sessionId}/export`,
      { format }
    )
    return response // Return raw response for download handling
  },

  // Delete analysis report
  async deleteAnalysisReport(sessionId: string): Promise<void> {
    const response = await apiClient.delete<ApiResponse>(
      `/api/v1/reports/${sessionId}`
    )
    handleApiResponse(response)
  }
}

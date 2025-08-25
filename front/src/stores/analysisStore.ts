import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import {
  AnalysisConfig,
  AnalysisState,
  AnalysisMessage,
  ToolCall,
  AgentStatus,
  ReportSectionType,
  ReportSection,
  AnalystType,
  LLMProvider
} from '../types'
import {
  DEFAULT_TICKER,
  DEFAULT_RESEARCH_DEPTH,
  DEFAULT_ANALYSTS
} from '../lib/constants'
import {
  generateId,
  getKSTDate,
  getKSTTimestamp,
  newKSTDate
} from '../lib/utils'
import { analysisApi, AnalysisResponse, AnalysisStatusResponse } from '../api'

interface ConfigState {
  config: AnalysisConfig
  isConfigValid: boolean
}

interface ConfigActions {
  updateConfig: (updates: Partial<AnalysisConfig>) => void
  validateConfig: () => boolean
  resetConfig: () => void
}

interface AnalysisStreamState {
  isRunning: boolean
  isPaused: boolean
  currentAgent: string | null
  progress: number
  startTime: Date | null
  endTime: Date | null
  messages: AnalysisMessage[]
  toolCalls: ToolCall[]
  agentStatus: Record<string, AgentStatus>
  reportSections: Record<ReportSectionType, ReportSection | null>
  llmCallCount: number
  toolCallCount: number
  error: string | null
  currentSessionId: string | null
  analysisHistory: AnalysisResponse[]
  isLoading: boolean
}

interface AnalysisStreamActions {
  startAnalysis: () => Promise<void>
  stopAnalysis: () => Promise<void>
  pauseAnalysis: () => Promise<void>
  addMessage: (message: Omit<AnalysisMessage, 'id'>) => void
  addToolCall: (toolCall: Omit<ToolCall, 'id'>) => void
  updateAgentStatus: (agent: string, status: AgentStatus) => void
  updateReportSection: (
    section: ReportSectionType,
    content: string,
    agentName: string
  ) => void
  completeAnalysis: (finalState?: any) => void
  setError: (error: string) => void
  clearError: () => void
  resetAnalysis: () => void
  calculateProgress: () => number
  loadAnalysisHistory: () => Promise<void>
  getAnalysisStatus: (
    sessionId: string
  ) => Promise<AnalysisStatusResponse | null>
  deleteAnalysisSession: (sessionId: string) => Promise<void>
  refreshCurrentSession: () => Promise<void>
}

type AnalysisStore = ConfigState &
  ConfigActions &
  AnalysisStreamState &
  AnalysisStreamActions

const initialConfig: AnalysisConfig = {
  ticker: DEFAULT_TICKER,
  analysisDate: getKSTDate().toISOString().split('T')[0],
  analysts: DEFAULT_ANALYSTS,
  researchDepth: DEFAULT_RESEARCH_DEPTH,
  llmProvider: LLMProvider.OPENAI,
  shallowThinker: 'gpt-4o',
  deepThinker: 'gpt-4o',
  backendUrl: 'https://api.openai.com/v1'
}

const initialAgentStatus: Record<string, AgentStatus> = {
  'Market Analyst': AgentStatus.PENDING,
  'Social Analyst': AgentStatus.PENDING,
  'News Analyst': AgentStatus.PENDING,
  'Fundamentals Analyst': AgentStatus.PENDING,
  'Bull Researcher': AgentStatus.PENDING,
  'Bear Researcher': AgentStatus.PENDING,
  'Research Manager': AgentStatus.PENDING,
  Trader: AgentStatus.PENDING,
  'Risky Analyst': AgentStatus.PENDING,
  'Neutral Analyst': AgentStatus.PENDING,
  'Safe Analyst': AgentStatus.PENDING,
  'Portfolio Manager': AgentStatus.PENDING
}

const initialReportSections: Record<ReportSectionType, ReportSection | null> = {
  [ReportSectionType.MARKET_REPORT]: null,
  [ReportSectionType.SENTIMENT_REPORT]: null,
  [ReportSectionType.NEWS_REPORT]: null,
  [ReportSectionType.FUNDAMENTALS_REPORT]: null,
  [ReportSectionType.BEN_GRAHAM_REPORT]: null,
  [ReportSectionType.WARREN_BUFFETT_REPORT]: null,
  [ReportSectionType.INVESTMENT_PLAN]: null,
  [ReportSectionType.TRADER_INVESTMENT_PLAN]: null,
  [ReportSectionType.FINAL_TRADE_DECISION]: null
}

export const useAnalysisStore = create<AnalysisStore>()(
  subscribeWithSelector((set, get) => ({
    // Config State
    config: initialConfig,
    isConfigValid: false,

    // Analysis Stream State
    isRunning: false,
    isPaused: false,
    currentAgent: null,
    progress: 0,
    startTime: null,
    endTime: null,
    messages: [],
    toolCalls: [],
    agentStatus: { ...initialAgentStatus },
    reportSections: { ...initialReportSections },
    llmCallCount: 0,
    toolCallCount: 0,
    error: null,
    currentSessionId: null,
    analysisHistory: [],
    isLoading: false,

    // Config Actions
    updateConfig: (updates) => {
      set((state) => ({
        config: { ...state.config, ...updates }
      }))
      get().validateConfig()
    },

    validateConfig: () => {
      const { config } = get()

      const isValid =
        config.ticker.length > 0 &&
        config.analysisDate.length > 0 &&
        config.analysts.length > 0 &&
        config.researchDepth > 0 &&
        config.llmProvider !== null &&
        config.shallowThinker.length > 0 &&
        config.deepThinker.length > 0

      set({ isConfigValid: isValid })
      return isValid
    },

    resetConfig: () => {
      set({
        config: initialConfig,
        isConfigValid: false
      })
    },

    // Analysis Stream Actions
    startAnalysis: async () => {
      if (!get().isConfigValid) {
        set({ error: 'Configuration is invalid. Please check your settings.' })
        return
      }

      set({ isLoading: true, error: null })

      try {
        const { config } = get()

        // Prepare analysis config for API
        const analysisConfig = {
          ticker: config.ticker,
          analysis_date: config.analysisDate,
          analysts: config.analysts,
          research_depth: config.researchDepth,
          llm_provider: config.llmProvider,
          shallow_model: config.shallowThinker,
          deep_model: config.deepThinker,
          custom_instructions: config.customInstructions || undefined
        }

        // Start analysis via API
        const response = await analysisApi.startAnalysis({
          config: analysisConfig,
          client_metadata: {
            user_agent: navigator.userAgent
          }
        })

        // Update state with new session
        set({
          currentSessionId: response.session_id,
          isRunning: true,
          isPaused: false,
          startTime: newKSTDate(response.created_at),
          endTime: null,
          messages: [],
          toolCalls: [],
          agentStatus: { ...initialAgentStatus },
          reportSections: { ...initialReportSections },
          llmCallCount: 0,
          toolCallCount: 0,
          progress: 0,
          isLoading: false
        })

        // Start polling for updates
        // The auto-refresh in Header will handle periodic updates

        // Add initial system messages
        get().addMessage({
          timestamp: getKSTTimestamp(),
          type: 'system',
          content: `Starting analysis for ${config.ticker} on ${
            config.analysisDate
          } (Session: ${response.session_id.slice(0, 8)})`,
          agent: 'System'
        })

        get().addMessage({
          timestamp: getKSTTimestamp(),
          type: 'system',
          content: `Selected analysts: ${config.analysts.join(', ')}`,
          agent: 'System'
        })
      } catch (error) {
        console.error('Failed to start analysis:', error)
        set({
          error:
            error instanceof Error ? error.message : 'Failed to start analysis',
          isLoading: false,
          isRunning: false
        })
      }
    },

    stopAnalysis: async () => {
      const { currentSessionId } = get()
      if (!currentSessionId) return

      try {
        await analysisApi.controlAnalysis({
          session_id: currentSessionId,
          action: 'stop'
        })

        // Stop any active polling

        set({
          isRunning: false,
          isPaused: false,
          endTime: getKSTDate()
        })

        get().addMessage({
          timestamp: getKSTTimestamp(),
          type: 'system',
          content: 'Analysis stopped by user',
          agent: 'System'
        })
      } catch (error) {
        console.error('Failed to stop analysis:', error)
        set({ error: 'Failed to stop analysis' })
      }
    },

    pauseAnalysis: async () => {
      const { currentSessionId } = get()
      if (!currentSessionId) return

      try {
        await analysisApi.controlAnalysis({
          session_id: currentSessionId,
          action: 'pause'
        })

        set({ isPaused: true })

        get().addMessage({
          timestamp: getKSTTimestamp(),
          type: 'system',
          content: 'Analysis paused',
          agent: 'System'
        })
      } catch (error) {
        console.error('Failed to pause analysis:', error)
        set({ error: 'Failed to pause analysis' })
      }
    },

    addMessage: (message) => {
      const newMessage: AnalysisMessage = {
        ...message,
        id: generateId()
      }

      set((state) => ({
        messages: [...state.messages, newMessage],
        llmCallCount:
          message.type === 'reasoning'
            ? state.llmCallCount + 1
            : state.llmCallCount
      }))
    },

    addToolCall: (toolCall) => {
      const newToolCall: ToolCall = {
        ...toolCall,
        id: generateId()
      }

      set((state) => ({
        toolCalls: [...state.toolCalls, newToolCall],
        toolCallCount: state.toolCallCount + 1
      }))
    },

    updateAgentStatus: (agent, status) => {
      set((state) => ({
        agentStatus: {
          ...state.agentStatus,
          [agent]: status
        },
        currentAgent:
          status === AgentStatus.IN_PROGRESS ? agent : state.currentAgent
      }))

      // Recalculate progress
      const newProgress = get().calculateProgress()
      set({ progress: newProgress })

      get().addMessage({
        timestamp: getKSTTimestamp(),
        type: 'system',
        content: `${agent} status updated to ${status}`,
        agent: 'System'
      })
    },

    updateReportSection: (section, content, agentName) => {
      const reportSection: ReportSection = {
        type: section,
        agentName,
        content,
        timestamp: getKSTDate()
      }

      set((state) => ({
        reportSections: {
          ...state.reportSections,
          [section]: reportSection
        }
      }))

      get().addMessage({
        timestamp: getKSTTimestamp(),
        type: 'analysis',
        content: `${agentName} completed ${section} report`,
        agent: agentName
      })
    },

    completeAnalysis: (finalState) => {
      // Mark all agents as completed
      const completedStatus = Object.keys(get().agentStatus).reduce(
        (acc, agent) => ({
          ...acc,
          [agent]: AgentStatus.COMPLETED
        }),
        {}
      )

      set({
        isRunning: false,
        isPaused: false,
        endTime: getKSTDate(),
        agentStatus: completedStatus,
        progress: 100,
        currentAgent: null
      })

      const { startTime, endTime } = get()
      const duration =
        endTime && startTime
          ? Math.round((endTime.getTime() - startTime.getTime()) / 1000)
          : 0

      get().addMessage({
        timestamp: getKSTTimestamp(),
        type: 'system',
        content: `Analysis completed successfully in ${duration} seconds`,
        agent: 'System'
      })
    },

    setError: (error) => {
      set({
        error,
        isRunning: false,
        isPaused: false
      })

      // Mark all in-progress agents as error
      const errorStatus = Object.entries(get().agentStatus).reduce(
        (acc, [agent, status]) => ({
          ...acc,
          [agent]:
            status === AgentStatus.IN_PROGRESS ? AgentStatus.ERROR : status
        }),
        {}
      )

      set({ agentStatus: errorStatus })

      get().addMessage({
        timestamp: getKSTTimestamp(),
        type: 'error',
        content: `Analysis error: ${error}`,
        agent: 'System'
      })
    },

    clearError: () => {
      set({ error: null })
    },

    resetAnalysis: () => {
      const { currentSessionId } = get()

      // Clear session data

      set({
        isRunning: false,
        isPaused: false,
        currentAgent: null,
        progress: 0,
        startTime: null,
        endTime: null,
        messages: [],
        toolCalls: [],
        agentStatus: { ...initialAgentStatus },
        reportSections: { ...initialReportSections },
        llmCallCount: 0,
        toolCallCount: 0,
        error: null,
        currentSessionId: null
      })
    },

    calculateProgress: () => {
      const { agentStatus, startTime, isRunning } = get()
      const agents = Object.keys(agentStatus)

      if (agents.length === 0) return 0

      // Calculate agent-based progress
      const completed = agents.filter(
        (agent) => agentStatus[agent] === AgentStatus.COMPLETED
      ).length
      const agentProgress = Math.round((completed / agents.length) * 100)

      // If running, also calculate time-based progress (10% per minute)
      if (isRunning && startTime) {
        const elapsedMinutes =
          (getKSTDate().getTime() - startTime.getTime()) / (1000 * 60)
        const timeProgress = Math.min(Math.floor(elapsedMinutes * 10), 100)

        // Use the higher of agent progress or time progress, but never exceed 100%
        return Math.min(Math.max(agentProgress, timeProgress), 100)
      }

      return agentProgress
    },

    loadAnalysisHistory: async () => {
      try {
        set({ isLoading: true })

        // If there's a current session, get data for it
        const { currentSessionId, isRunning: currentIsRunning } = get()
        if (currentSessionId) {
          let sessionData = null

          if (currentIsRunning) {
            // Use live endpoint for running sessions
            const liveResponse = await analysisApi.getLiveSessionData(
              currentSessionId,
              {
                include_messages: true,
                message_limit: 100
              }
            )

            if (liveResponse.success && liveResponse.data) {
              sessionData = liveResponse.data
            }
          } else {
            // Use regular endpoint for completed sessions
            try {
              const sessionResponse = await analysisApi.getAnalysisSession(
                currentSessionId,
                {
                  include_reports: true,
                  include_agents: true
                }
              )

              if (sessionResponse) {
                sessionData = {
                  session_id: sessionResponse.session_id,
                  status: sessionResponse.status,
                  ticker: sessionResponse.ticker,
                  analysis_date: sessionResponse.analysis_date,
                  current_agent: null,
                  progress_percentage: 100, // Completed sessions are 100%
                  started_at: sessionResponse.started_at,
                  completed_at: sessionResponse.completed_at,
                  elapsed_seconds: sessionResponse.execution_time_seconds,
                  llm_call_count: sessionResponse.llm_call_count || 0,
                  tool_call_count: sessionResponse.tool_call_count || 0,
                  agents_status: {},
                  agents_completed: sessionResponse.agents_completed || 0,
                  agents_failed: 0,
                  selected_analysts: sessionResponse.selected_analysts || [],
                  final_decision: sessionResponse.final_decision,
                  confidence_score: sessionResponse.confidence_score,
                  confidence_level: 'high',
                  error_message: sessionResponse.error_message,
                  last_message: null,
                  last_message_timestamp: null,
                  created_at: sessionResponse.created_at,
                  messages: [],
                  report_sections: [],
                  agent_executions: []
                }
              }
            } catch (error) {
              console.log('Session may not exist or be accessible:', error)
            }
          }

          if (sessionData) {
            // Update current session state, but preserve isRunning if we're using live data
            const updateData: any = {
              progress: sessionData.progress_percentage,
              currentAgent: sessionData.current_agent || null,
              llmCallCount: sessionData.llm_call_count,
              toolCallCount: sessionData.tool_call_count,
              isPaused: sessionData.status === 'paused',
              error: sessionData.error_message || null,
              startTime: sessionData.started_at
                ? newKSTDate(sessionData.started_at)
                : null,
              endTime: sessionData.completed_at
                ? newKSTDate(sessionData.completed_at)
                : null
            }

            // Only update isRunning if we're not currently running or if the session is definitely completed
            if (
              !currentIsRunning ||
              sessionData.status === 'completed' ||
              sessionData.status === 'failed' ||
              sessionData.status === 'cancelled'
            ) {
              updateData.isRunning = sessionData.status === 'running'
            }

            set(updateData)

            // Update messages if provided
            if (sessionData.messages) {
              const convertedMessages = sessionData.messages.map(
                (msg: any) => ({
                  id: generateId(),
                  timestamp: msg.created_at || getKSTTimestamp(),
                  type:
                    (msg.message_type as
                      | 'system'
                      | 'reasoning'
                      | 'analysis'
                      | 'error') || 'system',
                  content: msg.content,
                  agent: msg.agent_name || 'System'
                })
              )

              set({ messages: convertedMessages })
            }
          }
        }

        // Also get session history
        const response = await analysisApi.getAnalysisSessions({
          page: 1,
          per_page: 50,
          include_reports: false,
          include_agents: false
        })

        set({
          analysisHistory: response.sessions,
          isLoading: false
        })
      } catch (error) {
        console.error('Failed to load analysis history:', error)
        set({
          error: 'Failed to load analysis history',
          isLoading: false
        })
      }
    },

    getAnalysisStatus: async (sessionId: string) => {
      try {
        return await analysisApi.getAnalysisStatus(sessionId)
      } catch (error) {
        console.error('Failed to get analysis status:', error)
        return null
      }
    },

    deleteAnalysisSession: async (sessionId: string) => {
      try {
        await analysisApi.deleteAnalysisSession(sessionId)

        // Remove from history
        set((state) => ({
          analysisHistory: state.analysisHistory.filter(
            (session) => session.session_id !== sessionId
          )
        }))

        // If this is the current session, reset
        if (get().currentSessionId === sessionId) {
          get().resetAnalysis()
        }
      } catch (error) {
        console.error('Failed to delete analysis session:', error)
        set({ error: 'Failed to delete analysis session' })
      }
    },

    refreshCurrentSession: async () => {
      const { currentSessionId, isRunning: currentIsRunning } = get()
      if (!currentSessionId) return

      try {
        let data = null

        if (currentIsRunning) {
          // Use live endpoint for running sessions
          const response = await analysisApi.getLiveSessionData(
            currentSessionId,
            {
              include_messages: true,
              message_limit: 100
            }
          )

          if (response.success && response.data) {
            data = response.data
          }
        } else {
          // Use regular endpoint for completed sessions
          const sessionResponse = await analysisApi.getAnalysisSession(
            currentSessionId,
            {
              include_reports: true,
              include_agents: true
            }
          )

          if (sessionResponse) {
            data = {
              session_id: sessionResponse.session_id,
              status: sessionResponse.status,
              ticker: sessionResponse.ticker,
              analysis_date: sessionResponse.analysis_date,
              current_agent: null,
              progress_percentage: 100, // Completed sessions are 100%
              started_at: sessionResponse.started_at,
              completed_at: sessionResponse.completed_at,
              elapsed_seconds: sessionResponse.execution_time_seconds,
              llm_call_count: sessionResponse.llm_call_count || 0,
              tool_call_count: sessionResponse.tool_call_count || 0,
              agents_status: {},
              agents_completed: sessionResponse.agents_completed || 0,
              agents_failed: 0,
              selected_analysts: sessionResponse.selected_analysts || [],
              final_decision: sessionResponse.final_decision,
              confidence_score: sessionResponse.confidence_score,
              confidence_level: 'high',
              error_message: sessionResponse.error_message,
              last_message: null,
              last_message_timestamp: null,
              created_at: sessionResponse.created_at,
              messages: [],
              report_sections: [],
              agent_executions: []
            }
          }
        }

        if (data) {
          // Update current session state, but preserve isRunning if we're using live data
          const updateData: any = {
            progress: data.progress_percentage,
            currentAgent: data.current_agent || null,
            llmCallCount: data.llm_call_count,
            toolCallCount: data.tool_call_count,
            isPaused: data.status === 'paused',
            error: data.error_message || null,
            startTime: data.started_at ? newKSTDate(data.started_at) : null,
            endTime: data.completed_at ? newKSTDate(data.completed_at) : null
          }

          // Only update isRunning if we're not currently running or if the session is definitely completed
          if (
            !currentIsRunning ||
            data.status === 'completed' ||
            data.status === 'failed' ||
            data.status === 'cancelled'
          ) {
            updateData.isRunning = data.status === 'running'
          }

          set(updateData)

          // Update agent statuses
          if (data.agents_status) {
            const updatedAgentStatus: Record<string, AgentStatus> = {}
            Object.entries(data.agents_status).forEach(([agent, status]) => {
              switch (status) {
                case 'running':
                  updatedAgentStatus[agent] = AgentStatus.IN_PROGRESS
                  break
                case 'completed':
                  updatedAgentStatus[agent] = AgentStatus.COMPLETED
                  break
                case 'failed':
                  updatedAgentStatus[agent] = AgentStatus.ERROR
                  break
                default:
                  updatedAgentStatus[agent] = AgentStatus.PENDING
              }
            })

            set((state) => ({
              agentStatus: {
                ...state.agentStatus,
                ...updatedAgentStatus
              }
            }))
          }

          // Update messages if provided
          if (data.messages) {
            const convertedMessages: AnalysisMessage[] = data.messages.map(
              (msg: any) => ({
                id: generateId(),
                timestamp: msg.created_at || new Date().toISOString(),
                type:
                  (msg.message_type as
                    | 'system'
                    | 'reasoning'
                    | 'analysis'
                    | 'error') || 'system',
                content: msg.content,
                agent: msg.agent_name || 'System'
              })
            )

            set({ messages: convertedMessages })
          }

          // Update report sections
          if (data.report_sections && data.report_sections.length > 0) {
            const updatedReportSections = { ...get().reportSections }

            data.report_sections.forEach((section) => {
              // Map section type from API to frontend enum
              const sectionType = Object.values(ReportSectionType).find(
                (type) =>
                  type.toLowerCase().replace(/_/g, ' ') ===
                  section.section_name.toLowerCase()
              ) as ReportSectionType

              if (sectionType) {
                updatedReportSections[sectionType] = {
                  type: sectionType,
                  agentName: section.agent_name,
                  content: section.content,
                  timestamp: newKSTDate(section.created_at)
                }
              }
            })

            set({ reportSections: updatedReportSections })
          }
        }
      } catch (error) {
        console.error('Failed to refresh current session:', error)
        // Don't set error state for refresh failures to avoid disrupting running analyses
      }
    }
  }))
)

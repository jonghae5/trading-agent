import { AnalystType, LLMProvider } from '../types'

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || ''

// Session Configuration
export const SESSION_DURATION_HOURS = 1
export const MAX_LOGIN_ATTEMPTS = 5
export const BLOCK_DURATION_MINUTES = 15

// UI Configuration
export const MAX_MESSAGE_BUFFER_SIZE = 500
export const MAX_LOG_DISPLAY_SIZE = 50
export const DEFAULT_TICKER = 'SPY'
export const DEFAULT_RESEARCH_DEPTH = 3
export const MIN_PASSWORD_LENGTH = 8
export const MAX_TICKER_LENGTH = 10

// Auto-refresh intervals (in milliseconds)
export const SESSION_CHECK_INTERVAL = 60000 // 1 minute
export const STATUS_UPDATE_INTERVAL = 5000 // 5 seconds
export const MARKET_DATA_INTERVAL = 30000 // 30 seconds

// LLM Provider URLs
export const PROVIDER_URLS: Record<LLMProvider, string> = {
  [LLMProvider.OPENAI]: 'https://api.openai.com/v1',
  [LLMProvider.ANTHROPIC]: 'https://api.anthropic.com/',
  [LLMProvider.GOOGLE]: 'https://generativelanguage.googleapis.com/v1',
  [LLMProvider.OPENROUTER]: 'https://openrouter.ai/api/v1',
  [LLMProvider.OLLAMA]: 'http://localhost:11434/v1'
}

// LLM Model Options
export const LLM_OPTIONS = {
  [LLMProvider.OPENAI]: {
    shallow: [
      { name: 'GPT-5 - Latest model', value: 'gpt-5' },
      { name: 'GPT-4o-mini - Fast and efficient', value: 'gpt-4o-mini' },
      { name: 'GPT-4.1-nano - Ultra-lightweight', value: 'gpt-4.1-nano' },
      { name: 'GPT-4.1-mini - Compact model', value: 'gpt-4.1-mini' },
      { name: 'GPT-4o - Standard model', value: 'gpt-4o' }
    ],
    deep: [
      { name: 'GPT-5 - Latest model', value: 'gpt-5' },
      { name: 'GPT-4.1-nano - Ultra-lightweight', value: 'gpt-4.1-nano' },
      { name: 'GPT-4.1-mini - Compact model', value: 'gpt-4.1-mini' },
      { name: 'GPT-4o - Standard model', value: 'gpt-4o' },
      { name: 'o4-mini - Specialized reasoning', value: 'o4-mini' },
      { name: 'o3-mini - Advanced reasoning', value: 'o3-mini' },
      { name: 'o3 - Full advanced reasoning', value: 'o3' },
      { name: 'o1 - Premier reasoning', value: 'o1' }
    ]
  },
  [LLMProvider.ANTHROPIC]: {
    shallow: [
      {
        name: 'Claude Haiku 3.5 - Fast inference',
        value: 'claude-3-5-haiku-latest'
      },
      {
        name: 'Claude Sonnet 3.5 - Highly capable',
        value: 'claude-3-5-sonnet-latest'
      },
      {
        name: 'Claude Sonnet 3.7 - Exceptional reasoning',
        value: 'claude-3-7-sonnet-latest'
      },
      { name: 'Claude Sonnet 4 - High performance', value: 'claude-sonnet-4-0' }
    ],
    deep: [
      {
        name: 'Claude Haiku 3.5 - Fast inference',
        value: 'claude-3-5-haiku-latest'
      },
      {
        name: 'Claude Sonnet 3.5 - Highly capable',
        value: 'claude-3-5-sonnet-latest'
      },
      {
        name: 'Claude Sonnet 3.7 - Exceptional reasoning',
        value: 'claude-3-7-sonnet-latest'
      },
      {
        name: 'Claude Sonnet 4 - High performance',
        value: 'claude-sonnet-4-0'
      },
      { name: 'Claude Opus 4 - Most powerful', value: 'claude-opus-4-0' }
    ]
  },
  [LLMProvider.GOOGLE]: {
    shallow: [
      {
        name: 'Gemini 2.0 Flash-Lite - Cost efficient',
        value: 'gemini-2.0-flash-lite'
      },
      { name: 'Gemini 2.0 Flash - Next generation', value: 'gemini-2.0-flash' },
      {
        name: 'Gemini 2.5 Flash - Adaptive thinking',
        value: 'gemini-2.5-flash'
      }
    ],
    deep: [
      {
        name: 'Gemini 2.0 Flash-Lite - Cost efficient',
        value: 'gemini-2.0-flash-lite'
      },
      { name: 'Gemini 2.0 Flash - Next generation', value: 'gemini-2.0-flash' },
      {
        name: 'Gemini 2.5 Flash - Adaptive thinking',
        value: 'gemini-2.5-flash'
      },
      { name: 'Gemini 2.5 Pro', value: 'gemini-2.5-pro' }
    ]
  },
  [LLMProvider.OPENROUTER]: {
    shallow: [
      { name: 'GPT-4o-mini', value: 'openai/gpt-4o-mini' },
      { name: 'Claude Haiku 3.5', value: 'anthropic/claude-3-5-haiku' }
    ],
    deep: [
      { name: 'GPT-4o', value: 'openai/gpt-4o' },
      { name: 'Claude Sonnet 3.5', value: 'anthropic/claude-3-5-sonnet' }
    ]
  },
  [LLMProvider.OLLAMA]: {
    shallow: [
      { name: 'Llama 3.2 3B', value: 'llama3.2:3b' },
      { name: 'Qwen 2.5 3B', value: 'qwen2.5:3b' }
    ],
    deep: [
      { name: 'Llama 3.2 7B', value: 'llama3.2:7b' },
      { name: 'Qwen 2.5 7B', value: 'qwen2.5:7b' }
    ]
  }
}

// Research Depth Options
export const RESEARCH_DEPTH_OPTIONS = [
  { label: '🌊 Shallow (1 round)', value: 1 },
  { label: '⛰️ Medium (3 rounds)', value: 3 },
  { label: '🌋 Deep (5 rounds)', value: 5 }
]

// Default Analyst Selection
export const DEFAULT_ANALYSTS = [
  AnalystType.MARKET,
  AnalystType.SOCIAL,
  AnalystType.NEWS,
  AnalystType.FUNDAMENTALS,
  AnalystType.BEN_GRAHAM,
  AnalystType.WARREN_BUFFETT
]

// Agent Names and Teams
export const AGENT_TEAMS = {
  analysis: [
    'Market Analyst',
    'Social Analyst',
    'News Analyst',
    'Fundamentals Analyst'
  ],
  research: ['Bull Researcher', 'Bear Researcher', 'Research Manager'],
  trading: ['Trader'],
  risk: ['Risky Analyst', 'Neutral Analyst', 'Safe Analyst'],
  portfolio: ['Portfolio Manager']
}

// Status Colors and Icons
export const STATUS_CONFIG = {
  pending: {
    color: 'text-gray-500',
    bgColor: 'bg-gray-100',
    icon: '⏳',
    label: 'Pending'
  },
  in_progress: {
    color: 'text-blue-600',
    bgColor: 'bg-blue-100',
    icon: '🔄',
    label: 'In Progress'
  },
  completed: {
    color: 'text-green-600',
    bgColor: 'bg-green-100',
    icon: '✅',
    label: 'Completed'
  },
  error: {
    color: 'text-red-600',
    bgColor: 'bg-red-100',
    icon: '❌',
    label: 'Error'
  }
}

// Theme Configuration
export const THEME_COLORS = {
  light: {
    primary: 'bg-blue-600',
    secondary: 'bg-gray-100',
    accent: 'bg-green-500',
    background: 'bg-white',
    surface: 'bg-gray-50',
    text: {
      primary: 'text-gray-900',
      secondary: 'text-gray-600',
      muted: 'text-gray-400'
    }
  },
  dark: {
    primary: 'bg-blue-500',
    secondary: 'bg-gray-800',
    accent: 'bg-green-400',
    background: 'bg-gray-900',
    surface: 'bg-gray-800',
    text: {
      primary: 'text-gray-100',
      secondary: 'text-gray-300',
      muted: 'text-gray-500'
    }
  }
}

// Validation Rules
export const VALIDATION_RULES = {
  ticker: {
    required: true,
    pattern: /^[A-Z0-9]{1,10}$/,
    message: 'Ticker must be 1-10 alphanumeric characters'
  },
  password: {
    required: true,
    minLength: MIN_PASSWORD_LENGTH,
    message: `Password must be at least ${MIN_PASSWORD_LENGTH} characters`
  },
  username: {
    required: true,
    maxLength: 50,
    message: 'Username is required and must be less than 50 characters'
  }
}

// Chart Colors
export const CHART_COLORS = {
  primary: '#3b82f6',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#06b6d4',
  gradient: {
    primary: ['#3b82f6', '#1d4ed8'],
    success: ['#10b981', '#059669'],
    warning: ['#f59e0b', '#d97706'],
    danger: ['#ef4444', '#dc2626']
  }
}

// Socket Event Names
export const SOCKET_EVENTS = {
  // Client to Server
  ANALYSIS_START: 'analysis:start',
  ANALYSIS_STOP: 'analysis:stop',
  ANALYSIS_PAUSE: 'analysis:pause',

  // Server to Client
  ANALYSIS_STATUS: 'analysis:status',
  ANALYSIS_MESSAGE: 'analysis:message',
  ANALYSIS_TOOL_CALL: 'analysis:tool-call',
  ANALYSIS_AGENT_UPDATE: 'analysis:agent-update',
  ANALYSIS_REPORT_UPDATE: 'analysis:report-update',
  ANALYSIS_COMPLETED: 'analysis:completed',
  ANALYSIS_ERROR: 'analysis:error',

  // Connection Events
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  CONNECT_ERROR: 'connect_error'
} as const

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error occurred. Please check your connection.',
  UNAUTHORIZED: 'Your session has expired. Please log in again.',
  VALIDATION_ERROR: 'Please check your input and try again.',
  SERVER_ERROR: 'Server error occurred. Please try again later.',
  ANALYSIS_FAILED:
    'Analysis failed. Please check your configuration and try again.',
  SESSION_EXPIRED: 'Your session has expired. Please log in again.',
  INVALID_TICKER: 'Please enter a valid ticker symbol.',
  INVALID_DATE: 'Please select a valid analysis date.',
  NO_ANALYSTS_SELECTED: 'Please select at least one analyst.'
} as const

// Success Messages
export const SUCCESS_MESSAGES = {
  LOGIN_SUCCESS: 'Login successful! Welcome back.',
  LOGOUT_SUCCESS: 'Logged out successfully.',
  CONFIG_SAVED: 'Configuration saved successfully.',
  ANALYSIS_STARTED: 'Analysis started successfully.',
  ANALYSIS_COMPLETED: 'Analysis completed successfully!',
  SETTINGS_UPDATED: 'Settings updated successfully.'
} as const

import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { format, formatDistanceToNow, isValid, parseISO } from 'date-fns'
import {
  AnalystType,
  LLMProvider,
  ReportSectionType,
  AgentTeam
} from '../types'

/**
 * Merge Tailwind CSS classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format date to Korean Standard Time (KST)
 */
export function formatKST(
  date: Date | string,
  formatStr: string = 'yyyy-MM-dd HH:mm:ss'
): string {
  const parsedDate = typeof date === 'string' ? parseISO(date) : date
  if (!isValid(parsedDate)) return 'Invalid Date'
  return format(parsedDate, formatStr) + ' KST'
}

/**
 * Format relative time from now
 */
export function formatRelativeTime(date: Date | string): string {
  const parsedDate = typeof date === 'string' ? parseISO(date) : date
  if (!isValid(parsedDate)) return 'Unknown time'
  return formatDistanceToNow(parsedDate, { addSuffix: true })
}

/**
 * Get current KST date - Intl API를 사용한 한국시간
 */
export function getKSTDate(): Date {
  return new Date(
    new Date().toLocaleString('en-US', { timeZone: 'Asia/Seoul' })
  )
}

/**
 * Create a new Date in Korean timezone
 */
export function newKSTDate(dateInput?: string | number | Date): Date {
  if (!dateInput) {
    return getKSTDate()
  }

  const date = new Date(dateInput)
  return new Date(date.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }))
}

/**
 * Get current KST timestamp as ISO string
 */
export function getKSTTimestamp(): string {
  return getKSTDate().toISOString()
}

/**
 * Sanitize ticker symbol
 */
export function sanitizeTicker(ticker: string): string {
  if (!ticker) return ''
  return ticker
    .toUpperCase()
    .replace(/[^A-Z0-9]/g, '')
    .slice(0, 10)
}

/**
 * Validate ticker symbol
 */
export function validateTicker(ticker: string): boolean {
  if (!ticker) return false
  return /^[A-Z0-9]{1,10}$/.test(ticker)
}

/**
 * Validate date input
 */
export function validateDate(date: string): boolean {
  if (!date) return false
  const parsedDate = parseISO(date)
  return isValid(parsedDate) && parsedDate <= getKSTDate()
}

/**
 * Sanitize log message to prevent injection
 */
export function sanitizeMessage(message: string): string {
  if (!message) return ''

  // Remove control characters and limit length
  const sanitized = message
    .replace(/[\x00-\x1f\x7f-\x9f]/g, '') // Remove control characters
    .replace(/\n|\r/g, ' ') // Replace newlines with spaces
    .trim()

  return sanitized.length > 1000 ? sanitized.slice(0, 1000) + '...' : sanitized
}

/**
 * Get analyst display name
 */
export function getAnalystDisplayName(analyst: AnalystType): string {
  const names: Record<AnalystType, string> = {
    [AnalystType.MARKET]: '📈 Market Analyst',
    [AnalystType.SOCIAL]: '💬 Social Media Analyst',
    [AnalystType.NEWS]: '📰 News Analyst',
    [AnalystType.FUNDAMENTALS]: '📊 Fundamentals Analyst',
    [AnalystType.BEN_GRAHAM]: '📚 Ben Graham Analyst',
    [AnalystType.WARREN_BUFFETT]: '🦉 Warren Buffett Analyst'
  }
  return names[analyst] || analyst
}

/**
 * Get LLM provider display name
 */
export function getProviderDisplayName(provider: LLMProvider): string {
  const names: Record<LLMProvider, string> = {
    [LLMProvider.OPENAI]: 'OpenAI',
    [LLMProvider.ANTHROPIC]: 'Anthropic',
    [LLMProvider.GOOGLE]: 'Google',
    [LLMProvider.OPENROUTER]: 'OpenRouter',
    [LLMProvider.OLLAMA]: 'Ollama'
  }
  return names[provider] || provider
}

/**
 * Get report section display name
 */
export function getReportSectionName(section: ReportSectionType): string {
  const names: Record<ReportSectionType, string> = {
    [ReportSectionType.MARKET_REPORT]: 'Market Analysis',
    [ReportSectionType.SENTIMENT_REPORT]: 'Sentiment Analysis',
    [ReportSectionType.NEWS_REPORT]: 'News Analysis',
    [ReportSectionType.FUNDAMENTALS_REPORT]: 'Fundamentals Analysis',
    [ReportSectionType.BEN_GRAHAM_REPORT]: 'Ben Graham Analysis',
    [ReportSectionType.WARREN_BUFFETT_REPORT]: 'Warren Buffett Analysis',
    [ReportSectionType.INVESTMENT_PLAN]: 'Investment Plan',
    [ReportSectionType.TRADER_INVESTMENT_PLAN]: 'Trading Strategy',
    [ReportSectionType.FINAL_TRADE_DECISION]: 'Final Decision'
  }
  return names[section] || section
}

/**
 * Get agent team by agent name
 */
export function getAgentTeam(agentName: string): AgentTeam {
  if (agentName.includes('Analyst')) return AgentTeam.ANALYSIS
  if (
    agentName.includes('Researcher') ||
    agentName.includes('Research Manager')
  )
    return AgentTeam.RESEARCH
  if (agentName.includes('Trader')) return AgentTeam.TRADING
  if (
    agentName.includes('Risk') ||
    agentName.includes('Safe') ||
    agentName.includes('Neutral')
  )
    return AgentTeam.RISK
  if (agentName.includes('Portfolio')) return AgentTeam.PORTFOLIO
  return AgentTeam.ANALYSIS
}

/**
 * Get team display name
 */
export function getTeamDisplayName(team: AgentTeam): string {
  const names: Record<AgentTeam, string> = {
    [AgentTeam.ANALYSIS]: '📈 Analysis Team',
    [AgentTeam.RESEARCH]: '🔬 Research Team',
    [AgentTeam.TRADING]: '💼 Trading Team',
    [AgentTeam.RISK]: '🛡️ Risk Management',
    [AgentTeam.PORTFOLIO]: '📊 Portfolio Team'
  }
  return names[team] || team
}

/**
 * Calculate analysis progress percentage
 */
export function calculateProgress(agentStatus: Record<string, string>): number {
  const agents = Object.keys(agentStatus)
  if (agents.length === 0) return 0

  const completed = agents.filter(
    (agent) => agentStatus[agent] === 'completed'
  ).length
  return Math.round((completed / agents.length) * 100)
}

/**
 * Format execution time in human readable format
 */
export function formatExecutionTime(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`
  }

  const minutes = Math.floor(seconds / 60)
  const remainingSeconds = seconds % 60

  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`
  }

  const hours = Math.floor(minutes / 60)
  const remainingMinutes = minutes % 60

  return `${hours}h ${remainingMinutes}m`
}

/**
 * Format large numbers with appropriate suffixes
 */
export function formatNumber(num: number, decimals: number = 2): string {
  if (num >= 1e12) {
    return (num / 1e12).toFixed(decimals) + 'T'
  }
  if (num >= 1e9) {
    return (num / 1e9).toFixed(decimals) + 'B'
  }
  if (num >= 1e6) {
    return (num / 1e6).toFixed(decimals) + 'M'
  }
  if (num >= 1e3) {
    return (num / 1e3).toFixed(decimals) + 'K'
  }
  return num.toFixed(decimals)
}

/**
 * Format percentage with proper sign
 */
export function formatPercentage(value: number, decimals: number = 2): string {
  const sign = value >= 0 ? '+' : ''
  return `${sign}${value.toFixed(decimals)}%`
}

/**
 * Generate unique ID
 */
export function generateId(): string {
  return Math.random().toString(36).substr(2, 9)
}

/**
 * Debounce function
 */
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: NodeJS.Timeout | null = null

  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout)
    timeout = setTimeout(() => func(...args), wait)
  }
}

/**
 * Throttle function
 */
export function throttle<T extends (...args: any[]) => any>(
  func: T,
  limit: number
): (...args: Parameters<T>) => void {
  let inThrottle: boolean = false

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      func(...args)
      inThrottle = true
      setTimeout(() => (inThrottle = false), limit)
    }
  }
}

/**
 * Check if session is expired
 */
export function isSessionExpired(expiresAt: Date | string): boolean {
  const expiration =
    typeof expiresAt === 'string' ? parseISO(expiresAt) : expiresAt
  return expiration <= getKSTDate()
}

/**
 * Get remaining session time in minutes
 */
export function getRemainingSessionTime(expiresAt: Date | string): number {
  const expiration =
    typeof expiresAt === 'string' ? parseISO(expiresAt) : expiresAt
  const now = getKSTDate()
  const diffMs = expiration.getTime() - now.getTime()
  return Math.max(0, Math.floor(diffMs / (1000 * 60)))
}

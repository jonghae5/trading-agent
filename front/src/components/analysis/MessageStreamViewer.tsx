import React, { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  MessageSquare,
  Brain,
  Zap,
  AlertCircle,
  TrendingUp,
  Info,
  User,
  Bot,
  Clock,
  Pause,
  Activity,
  Filter,
  ArrowDown,
  Copy,
  ChevronUp,
  Search,
  RefreshCw,
  Database,
  History
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { MessageLog } from '../../types'
import { analysisApi } from '../../api/analysis'

interface MessageStreamViewerProps {
  messages: MessageLog[]
  isRunning: boolean
  isPaused: boolean
  currentAgent: string | null
  sessionId?: string
  onMessageClick?: (message: MessageLog) => void
  className?: string
  showHistoricalData?: boolean // 새로운 prop for 저장된 데이터 표시
}

interface TypewriterTextProps {
  text: string
  speed?: number
  className?: string
  isActive?: boolean
}

interface MessageFilters {
  messageType?: string
  agentName?: string
  searchTerm?: string
}

// Typewriter effect component for latest messages
const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 25,
  className = '',
  isActive = true
}) => {
  const [displayText, setDisplayText] = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (!isActive) {
      setDisplayText(text)
      return
    }

    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayText((prev) => prev + text[currentIndex])
        setCurrentIndex((prev) => prev + 1)
      }, speed)

      return () => clearTimeout(timeout)
    }
  }, [currentIndex, text, speed, isActive])

  useEffect(() => {
    if (isActive) {
      setDisplayText('')
      setCurrentIndex(0)
    }
  }, [text, isActive])

  return (
    <span className={className}>
      {displayText}
      {currentIndex < text.length && isActive && (
        <motion.span
          className="inline-block w-0.5 h-4 bg-current ml-1"
          animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity }}
        />
      )}
    </span>
  )
}

// Message type configuration
const messageTypeConfig = {
  system: {
    icon: Info,
    label: 'System',
    colors: {
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      icon: 'text-blue-600',
      text: 'text-blue-800',
      timestamp: 'text-blue-500',
      badge: 'bg-blue-100 text-blue-700'
    }
  },
  reasoning: {
    icon: Brain,
    label: 'Reasoning',
    colors: {
      bg: 'bg-purple-50',
      border: 'border-purple-200',
      icon: 'text-purple-600',
      text: 'text-purple-800',
      timestamp: 'text-purple-500',
      badge: 'bg-purple-100 text-purple-700'
    }
  },
  tool_call: {
    icon: Zap,
    label: 'Tool Call',
    colors: {
      bg: 'bg-orange-50',
      border: 'border-orange-200',
      icon: 'text-orange-600',
      text: 'text-orange-800',
      timestamp: 'text-orange-500',
      badge: 'bg-orange-100 text-orange-700'
    }
  },
  error: {
    icon: AlertCircle,
    label: 'Error',
    colors: {
      bg: 'bg-red-50',
      border: 'border-red-200',
      icon: 'text-red-600',
      text: 'text-red-800',
      timestamp: 'text-red-500',
      badge: 'bg-red-100 text-red-700'
    }
  },
  analysis: {
    icon: TrendingUp,
    label: 'Analysis',
    colors: {
      bg: 'bg-green-50',
      border: 'border-green-200',
      icon: 'text-green-600',
      text: 'text-green-800',
      timestamp: 'text-green-500',
      badge: 'bg-green-100 text-green-700'
    }
  }
} as const

export const MessageStreamViewer: React.FC<MessageStreamViewerProps> = ({
  messages,
  isRunning,
  isPaused,
  currentAgent,
  sessionId,
  onMessageClick,
  className = '',
  showHistoricalData = true
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [isUserScrolling, setIsUserScrolling] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [filters, setFilters] = useState<MessageFilters>({})
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(
    new Set()
  )

  // 새로운 state들 for 저장된 데이터 관리
  const [historicalMessages, setHistoricalMessages] = useState<MessageLog[]>([])
  const [loadingHistorical, setLoadingHistorical] = useState(false)
  const [historicalPage, setHistoricalPage] = useState(1)
  const [historicalTotal, setHistoricalTotal] = useState(0)
  const [hasMoreHistorical, setHasMoreHistorical] = useState(false)
  const [showHistorical, setShowHistorical] = useState(false)

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = useCallback(() => {
    if (autoScroll && !isUserScrolling && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'end'
      })
    }
  }, [autoScroll, isUserScrolling])

  useEffect(() => {
    scrollToBottom()
  }, [messages.length, scrollToBottom])

  // Handle scroll events to detect user scrolling
  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const handleScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = container
      const isAtBottom = Math.abs(scrollHeight - clientHeight - scrollTop) < 10

      if (isAtBottom) {
        setAutoScroll(true)
        setIsUserScrolling(false)
      } else if (!isUserScrolling) {
        setIsUserScrolling(true)
        setAutoScroll(false)
      }
    }

    container.addEventListener('scroll', handleScroll, { passive: true })
    return () => container.removeEventListener('scroll', handleScroll)
  }, [isUserScrolling])

  // 저장된 메시지 로드 함수
  const loadHistoricalMessages = useCallback(
    async (page: number = 1) => {
      if (!sessionId || !showHistoricalData) return

      setLoadingHistorical(true)
      try {
        const response = await analysisApi.getMessageLogs(sessionId, {
          page,
          per_page: 50,
          message_type: filters.messageType,
          agent_name: filters.agentName,
          order: 'desc' // 최신순
        })

        if (page === 1) {
          setHistoricalMessages(response.items)
        } else {
          setHistoricalMessages((prev) => [...prev, ...response.items])
        }

        setHistoricalTotal(response.total)
        setHasMoreHistorical(response.has_next)
        setHistoricalPage(page)
      } catch (error) {
        console.error('Failed to load historical messages:', error)
      } finally {
        setLoadingHistorical(false)
      }
    },
    [sessionId, showHistoricalData, filters.messageType, filters.agentName]
  )

  // 필터가 변경되면 저장된 메시지 다시 로드
  useEffect(() => {
    if (showHistorical) {
      loadHistoricalMessages(1)
    }
  }, [loadHistoricalMessages, showHistorical])

  // 모든 메시지 합치기 (실시간 + 저장된 메시지)
  const allMessages = useMemo(() => {
    if (!showHistorical) {
      return messages
    }

    // 중복 제거를 위해 ID 기준으로 합치기
    const messageMap = new Map()

    // 먼저 저장된 메시지 추가
    historicalMessages.forEach((msg) => {
      messageMap.set(msg.id, msg)
    })

    // 그 다음 실시간 메시지 추가 (덮어쓰기)
    messages.forEach((msg) => {
      messageMap.set(msg.id, msg)
    })

    return Array.from(messageMap.values()).sort(
      (a, b) => a.sequence_number - b.sequence_number
    )
  }, [messages, historicalMessages, showHistorical])

  // Filter messages based on current filters
  const filteredMessages = useMemo(() => {
    return allMessages.filter((message) => {
      if (filters.messageType && message.message_type !== filters.messageType) {
        return false
      }
      if (filters.agentName && message.agent_name !== filters.agentName) {
        return false
      }
      if (filters.searchTerm) {
        const searchLower = filters.searchTerm.toLowerCase()
        return (
          message.content.toLowerCase().includes(searchLower) ||
          message.agent_name?.toLowerCase().includes(searchLower) ||
          message.tool_name?.toLowerCase().includes(searchLower)
        )
      }
      return true
    })
  }, [allMessages, filters])

  // Get unique agents for filter
  const uniqueAgents = useMemo(() => {
    const agents = new Set(messages.map((m) => m.agent_name).filter(Boolean))
    return Array.from(agents)
  }, [messages])

  // Get latest message for typewriter effect
  const latestMessage = filteredMessages[filteredMessages.length - 1]

  const formatTimestamp = (date: Date) => {
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 1
    })
  }

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  const toggleMessageExpansion = (messageId: number) => {
    setExpandedMessages((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(messageId)) {
        newSet.delete(messageId)
      } else {
        newSet.add(messageId)
      }
      return newSet
    })
  }

  const clearFilters = () => {
    setFilters({})
  }

  return (
    <div className={`flex flex-col h-full ${className}`}>
      <Card className="h-full flex flex-col">
        <CardHeader className="pb-4 space-y-0">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg flex items-center space-x-2">
              <MessageSquare className="h-5 w-5" />
              <span>Live Message Stream</span>
              {sessionId && (
                <span className="text-xs text-gray-500 font-normal">
                  #{sessionId.slice(0, 8)}
                </span>
              )}
            </CardTitle>

            <div className="flex items-center space-x-2">
              {/* Historical data toggle */}
              {sessionId && showHistoricalData && (
                <button
                  onClick={() => setShowHistorical(!showHistorical)}
                  className={`p-2 rounded-lg transition-colors ${
                    showHistorical
                      ? 'bg-green-100 text-green-600'
                      : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                  }`}
                  title="Toggle stored message logs"
                >
                  <Database className="h-4 w-4" />
                </button>
              )}

              {/* Refresh historical data */}
              {showHistorical && sessionId && (
                <button
                  onClick={() => loadHistoricalMessages(1)}
                  disabled={loadingHistorical}
                  className="p-2 rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 transition-colors disabled:opacity-50"
                  title="Refresh stored messages"
                >
                  <RefreshCw
                    className={`h-4 w-4 ${
                      loadingHistorical ? 'animate-spin' : ''
                    }`}
                  />
                </button>
              )}

              {/* Filter toggle */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-2 rounded-lg transition-colors ${
                  showFilters
                    ? 'bg-blue-100 text-blue-600'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                <Filter className="h-4 w-4" />
              </button>

              {/* Status indicator */}
              <div className="flex items-center space-x-3 text-sm">
                {isRunning && (
                  <div className="flex items-center space-x-2">
                    {isPaused ? (
                      <>
                        <Pause className="h-4 w-4 text-amber-600" />
                        <span className="text-amber-600">Paused</span>
                      </>
                    ) : (
                      <>
                        <motion.div
                          className="w-2 h-2 bg-green-500 rounded-full"
                          animate={{
                            scale: [1, 1.3, 1],
                            opacity: [0.7, 1, 0.7]
                          }}
                          transition={{ duration: 1.5, repeat: Infinity }}
                        />
                        <span className="text-green-600">Live</span>
                      </>
                    )}
                  </div>
                )}

                <div className="flex items-center space-x-1 text-gray-600">
                  <Activity className="h-4 w-4" />
                  <span>{filteredMessages.length}</span>
                  {showHistorical && (
                    <span className="text-xs text-gray-500">
                      ({historicalTotal} stored)
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          {/* Filters panel */}
          <AnimatePresence>
            {showFilters && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="overflow-hidden"
              >
                <div className="p-4 bg-gray-50 rounded-lg space-y-3 mt-4">
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    {/* Message type filter */}
                    <div>
                      <label className="text-xs font-medium text-gray-700 mb-1 block">
                        Message Type
                      </label>
                      <select
                        value={filters.messageType || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            messageType: e.target.value || undefined
                          }))
                        }
                        className="w-full text-sm p-2 border border-gray-200 rounded-md"
                      >
                        <option value="">All Types</option>
                        {Object.entries(messageTypeConfig).map(
                          ([type, config]) => (
                            <option key={type} value={type}>
                              {config.label}
                            </option>
                          )
                        )}
                      </select>
                    </div>

                    {/* Agent filter */}
                    <div>
                      <label className="text-xs font-medium text-gray-700 mb-1 block">
                        Agent
                      </label>
                      <select
                        value={filters.agentName || ''}
                        onChange={(e) =>
                          setFilters((prev) => ({
                            ...prev,
                            agentName: e.target.value || undefined
                          }))
                        }
                        className="w-full text-sm p-2 border border-gray-200 rounded-md"
                      >
                        <option value="">All Agents</option>
                        {uniqueAgents.map((agent) => (
                          <option key={agent} value={agent}>
                            {agent}
                          </option>
                        ))}
                      </select>
                    </div>

                    {/* Search */}
                    <div>
                      <label className="text-xs font-medium text-gray-700 mb-1 block">
                        Search
                      </label>
                      <div className="relative">
                        <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
                        <input
                          type="text"
                          value={filters.searchTerm || ''}
                          onChange={(e) =>
                            setFilters((prev) => ({
                              ...prev,
                              searchTerm: e.target.value || undefined
                            }))
                          }
                          placeholder="Search messages..."
                          className="w-full text-sm p-2 pl-8 border border-gray-200 rounded-md"
                        />
                      </div>
                    </div>
                  </div>

                  {(filters.messageType ||
                    filters.agentName ||
                    filters.searchTerm) && (
                    <button
                      onClick={clearFilters}
                      className="text-xs text-blue-600 hover:text-blue-700"
                    >
                      Clear filters
                    </button>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardHeader>

        <CardContent className="flex-1 overflow-hidden p-0 relative">
          {/* Messages container */}
          <div
            ref={containerRef}
            className="h-full overflow-y-auto px-6 pb-6 space-y-3"
          >
            <AnimatePresence initial={false}>
              {filteredMessages.map((message, index) => {
                const config =
                  messageTypeConfig[
                    message.message_type as keyof typeof messageTypeConfig
                  ]
                const IconComponent = config?.icon || MessageSquare
                const colors = config?.colors || messageTypeConfig.system.colors
                const isLatest = message.id === latestMessage?.id
                const isExpanded = expandedMessages.has(message.id)
                const shouldTruncate = message.content.length > 200

                return (
                  <motion.div
                    key={message.id}
                    layout
                    initial={{ opacity: 0, y: 20, scale: 0.95 }}
                    animate={{ opacity: 1, y: 0, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{
                      duration: 0.3,
                      layout: { duration: 0.2 }
                    }}
                    className={`
                      group p-4 rounded-lg border transition-all duration-200 cursor-pointer
                      ${colors.bg} ${colors.border}
                      ${
                        isLatest && isRunning && !isPaused
                          ? 'ring-2 ring-blue-200 shadow-lg'
                          : ''
                      }
                      hover:shadow-md
                    `}
                    onClick={() => onMessageClick?.(message)}
                  >
                    <div className="flex items-start space-x-3">
                      {/* Icon */}
                      <div
                        className={`
                        flex-shrink-0 w-8 h-8 rounded-full ${colors.bg} 
                        flex items-center justify-center border ${colors.border}
                      `}
                      >
                        <IconComponent className={`h-4 w-4 ${colors.icon}`} />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        {/* Header */}
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center space-x-2 flex-wrap">
                            {/* Sequence number with storage indicator */}
                            <span className="text-xs text-gray-400 font-mono flex items-center space-x-1">
                              <span>#{message.sequence_number}</span>
                              {showHistorical &&
                                historicalMessages.some(
                                  (h) => h.id === message.id
                                ) && (
                                  <span title="Stored in database">
                                    <Database className="h-2.5 w-2.5 text-green-500" />
                                  </span>
                                )}
                            </span>

                            {/* Agent */}
                            {message.agent_name ? (
                              <div className="flex items-center space-x-1">
                                <Bot className={`h-3 w-3 ${colors.icon}`} />
                                <span
                                  className={`text-sm font-medium ${colors.text}`}
                                >
                                  {message.agent_name}
                                </span>
                              </div>
                            ) : (
                              <div className="flex items-center space-x-1">
                                <User className={`h-3 w-3 ${colors.icon}`} />
                                <span
                                  className={`text-sm font-medium ${colors.text}`}
                                >
                                  System
                                </span>
                              </div>
                            )}

                            {/* Message type badge */}
                            <span
                              className={`
                              text-xs px-2 py-0.5 rounded-full font-medium
                              ${colors.badge}
                            `}
                            >
                              {config?.label || message.message_type}
                            </span>

                            {/* Tool name if present */}
                            {message.tool_name && (
                              <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-600">
                                {message.tool_name}
                              </span>
                            )}
                          </div>

                          <div className="flex items-center space-x-2">
                            {/* Copy button */}
                            <button
                              onClick={(e) => {
                                e.stopPropagation()
                                copyToClipboard(message.content)
                              }}
                              className="opacity-0 group-hover:opacity-100 p-1 rounded text-gray-400 hover:text-gray-600 transition-all"
                            >
                              <Copy className="h-3 w-3" />
                            </button>

                            {/* Timestamp */}
                            <div className="flex items-center space-x-1">
                              <Clock
                                className={`h-3 w-3 ${colors.timestamp}`}
                              />
                              <span className={`text-xs ${colors.timestamp}`}>
                                {formatTimestamp(new Date(message.created_at))}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* Message content */}
                        <div
                          className={`text-sm leading-relaxed ${colors.text}`}
                        >
                          {isLatest && isRunning && !isPaused ? (
                            <TypewriterText
                              text={message.content}
                              speed={20}
                              isActive={true}
                            />
                          ) : shouldTruncate && !isExpanded ? (
                            <>
                              {message.content.slice(0, 200)}...
                              <button
                                onClick={(e) => {
                                  e.stopPropagation()
                                  toggleMessageExpansion(message.id)
                                }}
                                className="ml-2 text-blue-600 hover:text-blue-700 text-xs"
                              >
                                Show more
                              </button>
                            </>
                          ) : (
                            <>
                              {message.content}
                              {shouldTruncate && isExpanded && (
                                <button
                                  onClick={(e) => {
                                    e.stopPropagation()
                                    toggleMessageExpansion(message.id)
                                  }}
                                  className="ml-2 text-blue-600 hover:text-blue-700 text-xs"
                                >
                                  Show less
                                </button>
                              )}
                            </>
                          )}
                        </div>

                        {/* Tool args if present */}
                        {message.tool_args &&
                          Object.keys(message.tool_args).length > 0 && (
                            <div className="mt-2 p-2 bg-gray-100 rounded text-xs">
                              <div className="font-medium text-gray-700 mb-1">
                                Tool Arguments:
                              </div>
                              <pre className="text-gray-600 overflow-x-auto">
                                {JSON.stringify(message.tool_args, null, 2)}
                              </pre>
                            </div>
                          )}
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </AnimatePresence>

            {/* Typing indicator */}
            {isRunning && !isPaused && currentAgent && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="flex items-center space-x-3 p-4 bg-blue-50 border border-blue-200 rounded-lg"
              >
                <div className="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                  <Bot className="h-4 w-4 text-blue-600" />
                </div>

                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-sm font-medium text-blue-800">
                      {currentAgent}
                    </span>
                    <span className="text-xs text-blue-600">is working...</span>
                  </div>

                  {/* Animated dots */}
                  <div className="flex items-center space-x-1 mt-1">
                    {[0, 1, 2].map((i) => (
                      <motion.div
                        key={i}
                        className="w-1.5 h-1.5 bg-blue-400 rounded-full"
                        animate={{
                          scale: [1, 1.2, 1],
                          opacity: [0.5, 1, 0.5]
                        }}
                        transition={{
                          duration: 0.8,
                          repeat: Infinity,
                          delay: i * 0.2
                        }}
                      />
                    ))}
                  </div>
                </div>
              </motion.div>
            )}

            {/* Load more historical messages */}
            {showHistorical && hasMoreHistorical && (
              <div className="flex justify-center py-4">
                <button
                  onClick={() => loadHistoricalMessages(historicalPage + 1)}
                  disabled={loadingHistorical}
                  className="px-4 py-2 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2"
                >
                  {loadingHistorical ? (
                    <>
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>Loading...</span>
                    </>
                  ) : (
                    <>
                      <History className="h-4 w-4" />
                      <span>Load more stored messages</span>
                    </>
                  )}
                </button>
              </div>
            )}

            {/* Empty state */}
            {filteredMessages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                <MessageSquare className="h-12 w-12 mb-4 text-gray-300" />
                <p className="text-sm">
                  {allMessages.length > 0
                    ? 'No messages match your filters'
                    : 'No messages yet'}
                </p>
                <p className="text-xs text-gray-400 mt-1">
                  {allMessages.length > 0
                    ? 'Try adjusting your filter settings'
                    : 'Real-time updates will appear here'}
                </p>
                {showHistoricalData && sessionId && !showHistorical && (
                  <button
                    onClick={() => setShowHistorical(true)}
                    className="mt-2 text-blue-600 hover:text-blue-700 text-sm flex items-center space-x-1"
                  >
                    <Database className="h-4 w-4" />
                    <span>Show stored messages</span>
                  </button>
                )}
              </div>
            )}

            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>

          {/* Scroll to bottom button */}
          {!autoScroll && filteredMessages.length > 0 && (
            <motion.button
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 20 }}
              onClick={() => {
                setAutoScroll(true)
                setIsUserScrolling(false)
                scrollToBottom()
              }}
              className="
                absolute bottom-4 right-4 p-3 bg-blue-600 text-white 
                rounded-full shadow-lg hover:bg-blue-700 transition-colors
                flex items-center space-x-2
              "
            >
              <ArrowDown className="h-4 w-4" />
              <span className="text-sm">New messages</span>
              <motion.div
                className="w-2 h-2 bg-white rounded-full"
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ duration: 1, repeat: Infinity }}
              />
            </motion.button>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

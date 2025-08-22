import React, { useEffect, useRef, useState } from 'react'
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
  Activity
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { MarkdownRenderer } from '../common/MarkdownRenderer'
import { newKSTDate } from '../../lib/utils'

interface Message {
  id: string
  timestamp: string
  type: 'system' | 'reasoning' | 'tool' | 'error' | 'analysis'
  content: string
  agent?: string
}

interface MessageStreamProps {
  messages: Message[]
  isRunning: boolean
  isPaused: boolean
  currentAgent: string | null
}

interface TypewriterTextProps {
  text: string
  speed?: number
  className?: string
}

// Typewriter effect component
const TypewriterText: React.FC<TypewriterTextProps> = ({
  text,
  speed = 30,
  className = ''
}) => {
  const [displayText, setDisplayText] = useState('')
  const [currentIndex, setCurrentIndex] = useState(0)

  useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayText((prev) => prev + text[currentIndex])
        setCurrentIndex((prev) => prev + 1)
      }, speed)

      return () => clearTimeout(timeout)
    }
  }, [currentIndex, text, speed])

  useEffect(() => {
    // Reset when text changes
    setDisplayText('')
    setCurrentIndex(0)
  }, [text])

  return (
    <span className={className}>
      {displayText}
      {currentIndex < text.length && (
        <motion.span
          className="inline-block w-0.5 h-4 bg-current ml-1"
          animate={{ opacity: [0, 1, 0] }}
          transition={{ duration: 0.8, repeat: Infinity }}
        />
      )}
    </span>
  )
}

export const MessageStream: React.FC<MessageStreamProps> = ({
  messages,
  isRunning,
  isPaused,
  currentAgent
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const [autoScroll, setAutoScroll] = useState(true)
  const [isUserScrolling, setIsUserScrolling] = useState(false)

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (autoScroll && !isUserScrolling) {
      messagesEndRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'end'
      })
    }
  }, [messages, autoScroll, isUserScrolling])

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

    container.addEventListener('scroll', handleScroll)
    return () => container.removeEventListener('scroll', handleScroll)
  }, [isUserScrolling])

  const getMessageIcon = (type: string) => {
    switch (type) {
      case 'system':
        return Info
      case 'reasoning':
        return Brain
      case 'tool':
        return Zap
      case 'error':
        return AlertCircle
      case 'analysis':
        return TrendingUp
      default:
        return MessageSquare
    }
  }

  const getMessageColors = (type: string) => {
    switch (type) {
      case 'system':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          icon: 'text-blue-600',
          text: 'text-blue-800',
          timestamp: 'text-blue-500'
        }
      case 'reasoning':
        return {
          bg: 'bg-purple-50',
          border: 'border-purple-200',
          icon: 'text-purple-600',
          text: 'text-purple-800',
          timestamp: 'text-purple-500'
        }
      case 'tool':
        return {
          bg: 'bg-orange-50',
          border: 'border-orange-200',
          icon: 'text-orange-600',
          text: 'text-orange-800',
          timestamp: 'text-orange-500'
        }
      case 'error':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          icon: 'text-red-600',
          text: 'text-red-800',
          timestamp: 'text-red-500'
        }
      case 'analysis':
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          icon: 'text-green-600',
          text: 'text-green-800',
          timestamp: 'text-green-500'
        }
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          icon: 'text-gray-600',
          text: 'text-gray-800',
          timestamp: 'text-gray-500'
        }
    }
  }

  const formatTime = (timestamp: string) => {
    return newKSTDate(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  // Get recent messages (last 50) for performance
  const recentMessages = messages.slice(-50)
  const latestMessage = recentMessages[recentMessages.length - 1]

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center space-x-2">
            <MessageSquare className="h-5 w-5" />
            <span>Live Analysis Stream</span>
          </CardTitle>

          <div className="flex items-center space-x-3 text-sm">
            {/* Status indicator */}
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
                      animate={{ scale: [1, 1.3, 1], opacity: [0.7, 1, 0.7] }}
                      transition={{ duration: 1.5, repeat: Infinity }}
                    />
                    <span className="text-green-600">Live</span>
                  </>
                )}
              </div>
            )}

            {/* Message count */}
            <div className="flex items-center space-x-1 text-gray-600">
              <Activity className="h-4 w-4" />
              <span>{messages.length}</span>
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden p-0">
        {/* Messages container */}
        <div
          ref={containerRef}
          className="h-full overflow-y-auto px-6 pb-6 space-y-3"
        >
          <AnimatePresence initial={false}>
            {recentMessages.map((message, index) => {
              const IconComponent = getMessageIcon(message.type)
              const colors = getMessageColors(message.type)
              const isLatest = message.id === latestMessage?.id

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
                    p-4 rounded-lg border transition-all duration-200
                    ${colors.bg} ${colors.border}
                    ${isLatest ? 'ring-2 ring-blue-200 shadow-lg' : ''}
                  `}
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
                        <div className="flex items-center space-x-2">
                          {message.agent ? (
                            <div className="flex items-center space-x-1">
                              <Bot className={`h-3 w-3 ${colors.icon}`} />
                              <span
                                className={`text-sm font-medium ${colors.text}`}
                              >
                                {message.agent}
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

                          <span
                            className={`
                            text-xs px-2 py-0.5 rounded-full font-medium
                            ${colors.bg} ${colors.text}
                          `}
                          >
                            {message.type}
                          </span>
                        </div>

                        <div className="flex items-center space-x-1">
                          <Clock className={`h-3 w-3 ${colors.timestamp}`} />
                          <span className={`text-xs ${colors.timestamp}`}>
                            {formatTime(message.timestamp)}
                          </span>
                        </div>
                      </div>

                      {/* Message content */}
                      <div className={`text-sm leading-relaxed ${colors.text}`}>
                        {isLatest && isRunning && !isPaused ? (
                          <TypewriterText text={message.content} speed={20} />
                        ) : message.type === 'analysis' ||
                          message.type === 'reasoning' ? (
                          <div className="prose prose-sm max-w-none">
                            <MarkdownRenderer
                              content={message.content}
                              variant="default"
                            />
                          </div>
                        ) : (
                          message.content
                        )}
                      </div>
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
                  <span className="text-xs text-blue-600">is thinking...</span>
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

          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <MessageSquare className="h-12 w-12 mb-4 text-gray-300" />
              <p className="text-sm">No messages yet</p>
              <p className="text-xs text-gray-400 mt-1">
                Real-time updates will appear here
              </p>
            </div>
          )}

          {/* Scroll anchor */}
          <div ref={messagesEndRef} />
        </div>

        {/* Scroll to bottom button */}
        {!autoScroll && (
          <motion.button
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            onClick={() => {
              setAutoScroll(true)
              setIsUserScrolling(false)
              messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
            }}
            className="
              absolute bottom-4 right-4 p-2 bg-blue-600 text-white 
              rounded-full shadow-lg hover:bg-blue-700 transition-colors
              flex items-center space-x-2
            "
          >
            <span className="text-xs">New messages</span>
            <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
          </motion.button>
        )}
      </CardContent>
    </Card>
  )
}

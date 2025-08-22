import React from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Clock,
  CheckCircle,
  AlertCircle,
  Play,
  Pause,
  Brain,
  Zap,
  MessageSquare,
  TrendingUp,
  Info,
  AlertTriangle
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { AgentStatus } from '../../types'
import { getKSTDate, newKSTDate } from '../../lib/utils'

interface ProgressTimelineProps {
  messages: Array<{
    id: string
    timestamp: string
    type: 'system' | 'reasoning' | 'tool' | 'error' | 'analysis'
    content: string
    agent?: string
  }>
  agentStatus: Record<string, AgentStatus>
  startTime: Date | null
  isPaused: boolean
}

interface TimelineEvent {
  id: string
  timestamp: Date
  type: 'message' | 'agent_status' | 'milestone'
  title: string
  description: string
  icon: React.ElementType
  color: string
  agent?: string
}

export const ProgressTimeline: React.FC<ProgressTimelineProps> = ({
  messages,
  agentStatus,
  startTime,
  isPaused
}) => {
  // Convert messages and agent status changes to timeline events
  const getTimelineEvents = (): TimelineEvent[] => {
    const events: TimelineEvent[] = []

    // Add start event
    if (startTime) {
      events.push({
        id: 'start',
        timestamp: startTime,
        type: 'milestone',
        title: 'Analysis Started',
        description: 'AI analysis session initialized',
        icon: Play,
        color: 'blue'
      })
    }

    // Add message events
    messages.forEach((message) => {
      let icon: React.ElementType = MessageSquare
      let color = 'gray'
      let title = message.type.charAt(0).toUpperCase() + message.type.slice(1)

      switch (message.type) {
        case 'system':
          icon = Info
          color = 'blue'
          break
        case 'reasoning':
          icon = Brain
          color = 'purple'
          title = 'AI Reasoning'
          break
        case 'tool':
          icon = Zap
          color = 'orange'
          title = 'Tool Execution'
          break
        case 'error':
          icon = AlertCircle
          color = 'red'
          title = 'Error'
          break
        case 'analysis':
          icon = TrendingUp
          color = 'green'
          title = 'Analysis Update'
          break
      }

      events.push({
        id: message.id,
        timestamp: newKSTDate(message.timestamp),
        type: 'message',
        title: message.agent ? `${message.agent}: ${title}` : title,
        description:
          message.content.length > 100
            ? message.content.substring(0, 100) + '...'
            : message.content,
        icon,
        color,
        agent: message.agent
      })
    })

    // Add agent status milestones
    Object.entries(agentStatus).forEach(([agentName, status]) => {
      if (status === AgentStatus.COMPLETED) {
        events.push({
          id: `${agentName}-completed`,
          timestamp: getKSTDate(), // In real implementation, you'd track actual completion times
          type: 'agent_status',
          title: `${agentName} Completed`,
          description: `${agentName} has finished its analysis`,
          icon: CheckCircle,
          color: 'green',
          agent: agentName
        })
      }
    })

    // Sort by timestamp (newest first for timeline display)
    return events.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
  }

  const timelineEvents = getTimelineEvents()

  const getColorClasses = (color: string) => {
    const colorMap: Record<
      string,
      { bg: string; border: string; text: string; icon: string }
    > = {
      blue: {
        bg: 'bg-blue-50',
        border: 'border-blue-200',
        text: 'text-blue-800',
        icon: 'text-blue-600'
      },
      green: {
        bg: 'bg-green-50',
        border: 'border-green-200',
        text: 'text-green-800',
        icon: 'text-green-600'
      },
      red: {
        bg: 'bg-red-50',
        border: 'border-red-200',
        text: 'text-red-800',
        icon: 'text-red-600'
      },
      orange: {
        bg: 'bg-orange-50',
        border: 'border-orange-200',
        text: 'text-orange-800',
        icon: 'text-orange-600'
      },
      purple: {
        bg: 'bg-purple-50',
        border: 'border-purple-200',
        text: 'text-purple-800',
        icon: 'text-purple-600'
      },
      gray: {
        bg: 'bg-gray-50',
        border: 'border-gray-200',
        text: 'text-gray-800',
        icon: 'text-gray-600'
      }
    }
    return colorMap[color] || colorMap.gray
  }

  const formatTimeAgo = (timestamp: Date) => {
    const now = getKSTDate()
    const diffMs = now.getTime() - timestamp.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)
    const diffHours = Math.floor(diffMins / 60)

    if (diffSecs < 60) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    if (diffHours < 24) return `${diffHours}h ago`
    return timestamp.toLocaleDateString()
  }

  return (
    <Card className="h-[600px] flex flex-col">
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">Progress Timeline</CardTitle>
          {isPaused && (
            <div className="flex items-center space-x-1 text-amber-600">
              <Pause className="h-4 w-4" />
              <span className="text-sm">Paused</span>
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden">
        <div className="h-full overflow-y-auto pr-2 space-y-4">
          <AnimatePresence>
            {timelineEvents.map((event, index) => {
              const IconComponent = event.icon
              const colors = getColorClasses(event.color)

              return (
                <motion.div
                  key={event.id}
                  layout
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 20 }}
                  transition={{
                    duration: 0.4,
                    delay: index * 0.05 // Stagger animation
                  }}
                  className="relative"
                >
                  {/* Timeline connector */}
                  {index < timelineEvents.length - 1 && (
                    <div className="absolute left-6 top-12 w-px h-8 bg-gray-200" />
                  )}

                  <div className="flex items-start space-x-4">
                    {/* Icon */}
                    <motion.div
                      className={`
                        flex-shrink-0 w-12 h-12 rounded-full border-2 
                        flex items-center justify-center
                        ${colors.bg} ${colors.border}
                      `}
                      whileHover={{ scale: 1.1 }}
                      transition={{ duration: 0.2 }}
                    >
                      <IconComponent className={`h-5 w-5 ${colors.icon}`} />
                    </motion.div>

                    {/* Content */}
                    <div className="flex-1 min-w-0 pb-4">
                      <div className="flex items-center justify-between mb-1">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                          {event.title}
                        </h4>
                        <span className="text-xs text-gray-500 flex-shrink-0 ml-2">
                          {formatTimeAgo(event.timestamp)}
                        </span>
                      </div>

                      <p className="text-sm text-gray-600 leading-relaxed">
                        {event.description}
                      </p>

                      {/* Event type badge */}
                      <div className="mt-2 flex items-center space-x-2">
                        <span
                          className={`
                          inline-flex items-center px-2 py-1 rounded-full text-xs font-medium
                          ${colors.bg} ${colors.text}
                        `}
                        >
                          {event.type.replace('_', ' ')}
                        </span>

                        {event.agent && (
                          <span className="text-xs text-gray-500">
                            by {event.agent}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </motion.div>
              )
            })}
          </AnimatePresence>

          {/* Empty state */}
          {timelineEvents.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <Clock className="h-12 w-12 mb-4 text-gray-300" />
              <p className="text-sm">No events yet</p>
              <p className="text-xs text-gray-400 mt-1">
                Timeline will populate as analysis progresses
              </p>
            </div>
          )}

          {/* Live indicator */}
          {timelineEvents.length > 0 && !isPaused && (
            <motion.div
              className="flex items-center justify-center py-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5 }}
            >
              <div className="flex items-center space-x-2 text-blue-600">
                <motion.div
                  className="w-2 h-2 bg-blue-500 rounded-full"
                  animate={{ scale: [1, 1.5, 1], opacity: [0.5, 1, 0.5] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                />
                <span className="text-xs font-medium">Live Updates</span>
              </div>
            </motion.div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

import React from 'react'
import { motion } from 'framer-motion'
import {
  Brain,
  TrendingUp,
  Users,
  Newspaper,
  BarChart3,
  Target,
  Shield,
  Zap,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { AgentStatus, AnalystType } from '../../types'
import { AnimatedProgressRing } from './AnimatedProgressRing'

import { MessageStream } from './MessageStream'

interface AnalysisProgressVisualizationProps {
  isRunning: boolean
  isPaused: boolean
  currentAgent: string | null
  progress: number
  agentStatus: Record<string, AgentStatus>
  messages: Array<{
    id: string
    timestamp: string
    type: 'system' | 'reasoning' | 'tool' | 'error' | 'analysis'
    content: string
    agent?: string
  }>
  startTime: Date | null
  currentSessionId: string | null
  llmCallCount: number
  toolCallCount: number
  selectedAnalysts: AnalystType[]
}

// Agent icons mapping
const agentIcons: Record<string, React.ElementType> = {
  'Market Analyst': TrendingUp,
  'Social Analyst': Users,
  'News Analyst': Newspaper,
  'Fundamentals Analyst': BarChart3,
  'Bull Researcher': TrendingUp,
  'Bear Researcher': TrendingUp,
  'Research Manager': Brain,
  Trader: Target,
  'Risky Analyst': Zap,
  'Neutral Analyst': Shield,
  'Safe Analyst': Shield,
  'Portfolio Manager': Target
}

// Analysis stages based on typical workflow
const analysisStages = [
  { id: 'initialization', name: 'Initialization', agents: ['System'] },
  {
    id: 'data-collection',
    name: 'Data Collection',
    agents: [
      'Market Analyst',
      'News Analyst',
      'Fundamentals Analyst',
      'Social Analyst'
    ]
  },
  {
    id: 'analysis',
    name: 'Analysis',
    agents: ['Bull Researcher', 'Bear Researcher']
  },
  { id: 'research', name: 'Research', agents: ['Research Manager'] },
  { id: 'decision', name: 'Decision Making', agents: ['Trader'] },
  {
    id: 'risk-assessment',
    name: 'Risk Assessment',
    agents: ['Risky Analyst', 'Neutral Analyst', 'Safe Analyst']
  },
  { id: 'finalization', name: 'Finalization', agents: ['Portfolio Manager'] }
]

export const AnalysisProgressVisualization: React.FC<
  AnalysisProgressVisualizationProps
> = ({
  isRunning,
  isPaused,
  currentAgent,
  progress,
  agentStatus,
  messages,
  startTime,
  currentSessionId,
  llmCallCount,
  toolCallCount,
  selectedAnalysts
}) => {
  // Calculate current stage based on agent progress
  const getCurrentStage = () => {
    if (!isRunning) return null

    const completedAgents = Object.entries(agentStatus)
      .filter(([_, status]) => status === AgentStatus.COMPLETED)
      .map(([name, _]) => name)

    for (let i = analysisStages.length - 1; i >= 0; i--) {
      const stage = analysisStages[i]
      if (stage.agents.some((agent) => completedAgents.includes(agent))) {
        return stage
      }
    }

    return analysisStages[0] // Default to initialization
  }

  const currentStage = getCurrentStage()

  // Calculate elapsed time
  const getElapsedTime = () => {
    if (!startTime) return '00:00'
    const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000)
    const minutes = Math.floor(elapsed / 60)
    const seconds = elapsed % 60
    return `${minutes.toString().padStart(2, '0')}:${seconds
      .toString()
      .padStart(2, '0')}`
  }

  const [elapsedTime, setElapsedTime] = React.useState(getElapsedTime())

  React.useEffect(() => {
    if (!isRunning || isPaused) return

    const interval = setInterval(() => {
      setElapsedTime(getElapsedTime())
    }, 1000)

    return () => clearInterval(interval)
  }, [isRunning, isPaused, startTime])

  if (!isRunning && !isPaused) {
    return null
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      className="space-y-6"
    >
      {/* Main Progress Card */}
      <Card
        className={`${
          isPaused
            ? 'bg-amber-50 border-amber-200'
            : 'bg-blue-50 border-blue-200'
        } transition-colors duration-300`}
      >
        <CardContent className="p-4 md:p-6">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-6 space-y-4 lg:space-y-0">
            <div className="flex items-center space-x-4">
              <div className="relative">
                <AnimatedProgressRing
                  progress={progress}
                  isPaused={isPaused}
                  size={80}
                />
                <div className="absolute inset-0 flex items-center justify-center">
                  <Brain
                    className={`h-6 w-6 ${
                      isPaused ? 'text-amber-600' : 'text-blue-600'
                    }`}
                  />
                </div>
              </div>

              <div className="flex-1">
                <h3
                  className={`text-lg md:text-xl font-bold ${
                    isPaused ? 'text-amber-900' : 'text-blue-900'
                  }`}
                >
                  {isPaused ? 'Analysis Paused' : 'Analysis in Progress'}
                </h3>
                <p
                  className={`text-sm ${
                    isPaused ? 'text-amber-700' : 'text-blue-700'
                  } truncate`}
                >
                  {currentAgent ? `Current: ${currentAgent}` : 'Loading...'}
                </p>
                <p
                  className={`text-xs ${
                    isPaused ? 'text-amber-600' : 'text-blue-600'
                  }`}
                >
                  Session: {currentSessionId?.slice(0, 8) || 'Unknown'}
                </p>
              </div>
            </div>

            {/* Stats */}
            <div className="flex lg:flex-col lg:text-right space-x-6 lg:space-x-0 lg:space-y-1">
              <div className="flex flex-wrap lg:justify-end gap-2 lg:gap-4 text-sm">
                <div className="flex items-center space-x-1">
                  <Clock className="h-4 w-4" />
                  <span className="whitespace-nowrap">{elapsedTime}</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Brain className="h-4 w-4" />
                  <span className="whitespace-nowrap">
                    {llmCallCount} calls
                  </span>
                </div>
                <div className="flex items-center space-x-1">
                  <Zap className="h-4 w-4" />
                  <span className="whitespace-nowrap">
                    {toolCallCount} tools
                  </span>
                </div>
              </div>
              <div
                className={`text-xl md:text-2xl font-bold ${
                  isPaused ? 'text-amber-900' : 'text-blue-900'
                }`}
              >
                {progress}%
              </div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="relative">
            <div
              className={`w-full h-3 rounded-full ${
                isPaused ? 'bg-amber-200' : 'bg-blue-200'
              }`}
            >
              <motion.div
                className={`h-full rounded-full ${
                  isPaused ? 'bg-amber-500' : 'bg-blue-500'
                }`}
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.8, ease: 'easeOut' }}
              />
            </div>

            {/* Progress markers */}
            <div className="absolute top-0 w-full flex justify-between">
              {[0, 25, 50, 75, 100].map((marker) => (
                <div
                  key={marker}
                  className={`w-1 h-3 rounded-full ${
                    progress >= marker
                      ? isPaused
                        ? 'bg-amber-600'
                        : 'bg-blue-600'
                      : 'bg-gray-300'
                  }`}
                />
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Live Analysis Stream Only */}
      <MessageStream
        messages={messages}
        isRunning={isRunning}
        isPaused={isPaused}
        currentAgent={currentAgent}
      />
    </motion.div>
  )
}

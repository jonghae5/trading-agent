/**
 * Loading States Components
 * Reusable loading indicators and skeleton screens
 */

import React from 'react'
import { motion } from 'framer-motion'
import { Loader2, TrendingUp, Brain, BarChart3 } from 'lucide-react'
import { Card, CardContent, CardHeader } from '../ui/card'

interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg'
  text?: string
  className?: string
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  size = 'md',
  text,
  className = ''
}) => {
  const sizeClasses = {
    sm: 'size-4',
    md: 'size-6',
    lg: 'size-8'
  }

  return (
    <div className={`flex items-center justify-center ${className}`}>
      <div className="flex items-center gap-3">
        <Loader2
          className={`${sizeClasses[size]} animate-spin text-blue-500`}
        />
        {text && (
          <span className="text-sm font-medium text-gray-600">{text}</span>
        )}
      </div>
    </div>
  )
}

interface PulseLoaderProps {
  count?: number
  className?: string
}

export const PulseLoader: React.FC<PulseLoaderProps> = ({
  count = 3,
  className = ''
}) => {
  return (
    <div className={`flex items-center gap-2 ${className}`}>
      {Array.from({ length: count }).map((_, i) => (
        <motion.div
          key={i}
          className="w-2 h-2 bg-blue-500 rounded-full"
          animate={{
            scale: [1, 1.5, 1],
            opacity: [0.5, 1, 0.5]
          }}
          transition={{
            duration: 1,
            repeat: Infinity,
            delay: i * 0.2
          }}
        />
      ))}
    </div>
  )
}

// Skeleton components for different content types
export const SkeletonText: React.FC<{ className?: string }> = ({
  className = ''
}) => <div className={`animate-pulse bg-gray-200 rounded h-4 ${className}`} />

export const SkeletonAvatar: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({
  size = 'md'
}) => {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12',
    lg: 'w-16 h-16'
  }

  return (
    <div
      className={`animate-pulse bg-gray-200 rounded-full ${sizeClasses[size]}`}
    />
  )
}

export const SkeletonCard: React.FC = () => (
  <Card>
    <CardHeader>
      <div className="animate-pulse space-y-3">
        <SkeletonText className="w-1/3 h-5" />
        <SkeletonText className="w-2/3 h-4" />
      </div>
    </CardHeader>
    <CardContent>
      <div className="animate-pulse space-y-3">
        <SkeletonText className="w-full" />
        <SkeletonText className="w-5/6" />
        <SkeletonText className="w-4/6" />
      </div>
    </CardContent>
  </Card>
)

export const SkeletonStockItem: React.FC = () => (
  <div className="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
    <div className="flex items-center gap-4">
      <SkeletonAvatar size="sm" />
      <div className="space-y-2">
        <SkeletonText className="w-16 h-4" />
        <SkeletonText className="w-32 h-3" />
      </div>
    </div>
    <div className="text-right space-y-2">
      <SkeletonText className="w-20 h-4" />
      <SkeletonText className="w-16 h-3" />
    </div>
  </div>
)

export const SkeletonChart: React.FC<{ height?: number }> = ({
  height = 300
}) => (
  <Card>
    <CardHeader>
      <div className="animate-pulse space-y-2">
        <SkeletonText className="w-1/4 h-5" />
        <SkeletonText className="w-1/2 h-4" />
      </div>
    </CardHeader>
    <CardContent>
      <div
        className="animate-pulse bg-gray-200 rounded-lg"
        style={{ height }}
      />
    </CardContent>
  </Card>
)

interface AnalysisLoadingProps {
  stage?: string
  progress?: number
}

export const AnalysisLoading: React.FC<AnalysisLoadingProps> = ({
  stage = 'Loading...',
  progress = 0
}) => {
  return (
    <Card className="border-blue-200 bg-blue-50">
      <CardContent className="p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="p-2 bg-blue-100 rounded-lg">
            <Brain className="size-6 text-blue-600 animate-pulse" />
          </div>
          <div>
            <h3 className="font-semibold text-blue-900">
              AI Analysis in Progress
            </h3>
            <p className="text-sm text-blue-700">{stage}</p>
          </div>
        </div>

        {progress > 0 && (
          <div className="space-y-2">
            <div className="flex justify-between text-sm text-blue-700">
              <span>Progress</span>
              <span>{progress}%</span>
            </div>
            <div className="w-full bg-blue-200 rounded-full h-2">
              <motion.div
                className="bg-blue-600 h-2 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5 }}
              />
            </div>
          </div>
        )}

        <div className="flex justify-center mt-4">
          <PulseLoader count={5} />
        </div>
      </CardContent>
    </Card>
  )
}

interface DataLoadingProps {
  type: 'market' | 'chart' | 'analysis' | 'search'
  message?: string
}

export const DataLoading: React.FC<DataLoadingProps> = ({ type, message }) => {
  const getIcon = () => {
    switch (type) {
      case 'market':
        return <TrendingUp className="size-5 text-green-500" />
      case 'chart':
        return <BarChart3 className="size-5 text-blue-500" />
      case 'analysis':
        return <Brain className="size-5 text-purple-500" />
      default:
        return <Loader2 className="size-5 text-gray-500" />
    }
  }

  const getMessage = () => {
    if (message) return message

    switch (type) {
      case 'market':
        return 'Loading market data...'
      case 'chart':
        return 'Loading chart data...'
      case 'analysis':
        return 'Running analysis...'
      case 'search':
        return 'Searching...'
      default:
        return 'Loading...'
    }
  }

  return (
    <div className="flex items-center justify-center p-8">
      <div className="flex items-center gap-3">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: 'linear' }}
        >
          {getIcon()}
        </motion.div>
        <span className="text-sm font-medium text-gray-600">
          {getMessage()}
        </span>
      </div>
    </div>
  )
}

// List loading states
export const StockListLoading: React.FC = () => (
  <div className="space-y-3">
    {Array.from({ length: 6 }).map((_, i) => (
      <SkeletonStockItem key={i} />
    ))}
  </div>
)

export const ChartListLoading: React.FC = () => (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
    {Array.from({ length: 4 }).map((_, i) => (
      <SkeletonChart key={i} />
    ))}
  </div>
)

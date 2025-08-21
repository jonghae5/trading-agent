import React from 'react'
import { motion } from 'framer-motion'
import { Bell, RefreshCw, Menu } from 'lucide-react'

import { Button } from '../ui/button'

import { useUIStore } from '../../stores/uiStore'
import { useAnalysisStore } from '../../stores/analysisStore'
import { cn } from '../../lib/utils'

export const Header: React.FC = () => {
  const { notifications, autoRefresh, setAutoRefresh, setSidebarCollapsed } =
    useUIStore()
  const {
    isRunning,
    progress,
    currentAgent,
    currentSessionId,
    loadAnalysisHistory,
    refreshCurrentSession
  } = useAnalysisStore()

  const handleRefresh = async () => {
    if (isRunning && currentSessionId) {
      // 분석 실행 중일 때는 현재 세션의 라이브 데이터 가져오기
      await refreshCurrentSession()
    } else {
      // 분석이 실행 중이 아닐 때는 히스토리 새로고침
      await loadAnalysisHistory()
    }
  }

  // Ensure proper state hydration on component mount
  React.useEffect(() => {
    console.log('Header mounted with autoRefresh:', autoRefresh)
  }, [])

  React.useEffect(() => {
    let interval: NodeJS.Timeout | null = null

    if (autoRefresh) {
      interval = setInterval(() => {
        handleRefresh()
      }, 10000) // 10초마다 새로고침
    }

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [autoRefresh])

  return (
    <header className="sticky top-0 z-30 bg-white border-b border-gray-100 shadow-sm">
      <div className="px-3 sm:px-6 py-2 sm:py-3">
        <div className="flex items-center justify-between">
          {/* Left: Mobile Menu + Analysis Status */}
          <div className="flex items-center gap-4">
            {/* Mobile Menu Button */}
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSidebarCollapsed(false)}
              className="lg:hidden"
              title="Open sidebar"
            >
              <Menu className="size-5" />
            </Button>

            {/* Analysis Status (compact) */}
            {isRunning && currentSessionId ? (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-2"
              >
                <div className="size-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="text-sm text-blue-600 font-medium hidden sm:inline">
                  Analysis Running
                </span>
                <span className="text-sm text-blue-600 font-medium sm:hidden">
                  Running
                </span>
                {currentAgent && (
                  <span className="text-xs text-gray-500 hidden md:inline">
                    • {currentAgent}
                  </span>
                )}
                <span className="text-xs text-gray-500">{progress}%</span>
              </motion.div>
            ) : currentSessionId ? (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-2"
              >
                <div className="size-2 bg-gray-400 rounded-full" />
                <span className="text-sm text-gray-600 font-medium hidden sm:inline">
                  Analysis Completed
                </span>
                <span className="text-sm text-gray-600 font-medium sm:hidden">
                  Completed
                </span>
              </motion.div>
            ) : null}
          </div>

          {/* Center: Spacer */}
          <div className="flex-1" />

          {/* Right: Actions */}
          <div className="flex items-center gap-1 sm:gap-2">
            {/* Auto Refresh Toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={
                autoRefresh ? () => setAutoRefresh(false) : handleRefresh
              }
              onDoubleClick={() => setAutoRefresh(!autoRefresh)}
              className={cn('relative', autoRefresh && 'text-blue-600')}
              title={
                autoRefresh
                  ? 'Click to stop auto-refresh / Double-click to refresh now'
                  : 'Click to refresh now / Double-click to enable auto-refresh'
              }
            >
              <RefreshCw
                className={cn('size-4', autoRefresh && 'animate-spin')}
              />
              {autoRefresh && (
                <div className="absolute -top-1 -right-1 size-2 bg-green-500 rounded-full" />
              )}
            </Button>

            {/* Notifications */}
            <Button
              variant="ghost"
              size="icon"
              className="relative"
              title="Notifications"
            >
              <Bell className="size-4" />
              {notifications && (
                <div className="absolute -top-1 -right-1 size-2 bg-red-500 rounded-full" />
              )}
            </Button>
          </div>
        </div>

        {/* Analysis Progress Bar */}
        {isRunning && currentSessionId && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-3"
          >
            <div className="w-full bg-gray-200 rounded-full h-2">
              <motion.div
                className="bg-gradient-to-r from-blue-500 to-blue-600 h-2 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.5, ease: 'easeOut' }}
              />
            </div>
            <div className="flex justify-between items-center mt-1">
              <span className="text-xs text-gray-500">Analysis Progress</span>
              <span className="text-xs font-medium text-gray-700">
                {progress}% Complete
              </span>
            </div>
          </motion.div>
        )}
      </div>
    </header>
  )
}

import React, { useEffect, useState, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Brain, Play, Clock } from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import {
  StockAutocomplete,
  StockSearchResult
} from '../components/ui/stock-autocomplete'

import { useAnalysisStore } from '../stores/analysisStore'
import { useAuthStore } from '../stores/authStore'

import { AnalystType, LLMProvider } from '../types'
import {
  AnalysisProgressVisualization,
  FearGreedHistoryChart
} from '../components/analysis'
import {
  fearGreedApi,
  FearGreedIndexData,
  FearGreedHistoricalData
} from '../api/client'
import { economicApi, EconomicEvent } from '../api/economic'
import { getKSTDate, newKSTDate } from '../lib/utils'

// Helper function to get Fear & Greed color
const getFearGreedColor = (value: number): string => {
  if (value <= 25) return '#dc2626' // red-600 - Extreme Fear
  if (value <= 45) return '#ea580c' // orange-600 - Fear
  if (value <= 55) return '#65a30d' // lime-600 - Neutral
  if (value <= 75) return '#16a34a' // green-600 - Greed
  return '#059669' // emerald-600 - Extreme Greed
}

// Helper function to get analyst display name
const getAnalystDisplayName = (analyst: AnalystType): string => {
  switch (analyst) {
    case AnalystType.MARKET:
      return '시장'
    case AnalystType.SOCIAL:
      return '소셜 미디어'
    case AnalystType.NEWS:
      return '뉴스'
    case AnalystType.FUNDAMENTALS:
      return '펀더멘털'

    default:
      return analyst
  }
}

export const Analysis: React.FC = () => {
  const {
    isRunning,
    isPaused,
    currentAgent,
    progress,
    messages,
    agentStatus,
    currentSessionId,
    analysisHistory,
    isLoading,
    error,
    startTime,
    llmCallCount,
    toolCallCount,
    startAnalysis,
    loadAnalysisHistory,
    config,
    updateConfig
  } = useAnalysisStore()

  const { isAuthenticated } = useAuthStore()

  const [selectedAnalysts, setSelectedAnalysts] = useState<AnalystType[]>([
    AnalystType.MARKET,
    AnalystType.SOCIAL,
    AnalystType.NEWS,
    AnalystType.FUNDAMENTALS
  ])

  // Fear & Greed Index state
  const [fearGreedData, setFearGreedData] = useState<FearGreedIndexData | null>(
    null
  )
  const [fearGreedHistory, setFearGreedHistory] =
    useState<FearGreedHistoricalData | null>(null)
  const [fearGreedLoading, setFearGreedLoading] = useState(false)
  const [fearGreedError, setFearGreedError] = useState<string | null>(null)
  const [selectedPeriod, setSelectedPeriod] = useState<
    '1M' | '3M' | '6M' | '1Y'
  >('1M')

  // Economic events state
  const [economicEvents, setEconomicEvents] = useState<EconomicEvent[]>([])

  // Memoized values for performance
  const analystOptions = useMemo(() => Object.values(AnalystType), [])

  const handleAnalystToggle = useCallback((analyst: AnalystType) => {
    setSelectedAnalysts((prev) => {
      const isSelected = prev.includes(analyst)
      if (isSelected) {
        return prev.filter((a) => a !== analyst)
      } else {
        return [...prev, analyst]
      }
    })
  }, [])

  // Load economic events
  const loadEconomicEvents = async () => {
    try {
      // Get events for the last 5 years to match Fear & Greed data range
      const endDate = getKSTDate()
      const startDate = getKSTDate()
      startDate.setFullYear(startDate.getFullYear() - 5)

      const response = await economicApi.getEconomicEvents({
        startDate: startDate.toISOString().split('T')[0],
        endDate: endDate.toISOString().split('T')[0],
        minSeverity: 'medium'
      })

      setEconomicEvents(response.events)
    } catch (error) {
      console.error('Failed to load economic events:', error)
    }
  }

  // Load current Fear & Greed Index (separate from history)
  const loadCurrentFearGreedData = async () => {
    try {
      const summary = await fearGreedApi.getSummary()
      const current = {
        ...summary.current,
        previous_close: summary.historical_comparison?.previous_close || 0,
        one_week_ago: summary.historical_comparison?.one_week_ago || 0
      }
      setFearGreedData(current)
    } catch (error) {
      console.error('Failed to load current Fear & Greed Index:', error)
      // Don't set error for current data to avoid affecting UI
    }
  }

  // Load historical Fear & Greed Index data only
  const loadFearGreedHistory = async (period?: '1M' | '3M' | '6M' | '1Y') => {
    setFearGreedLoading(true)
    setFearGreedError(null)

    try {
      const history = await fearGreedApi.getHistory({
        period: period || selectedPeriod,
        aggregation: 'daily'
      })
      setFearGreedHistory(history)
    } catch (error) {
      console.error('Failed to load Fear & Greed Index history:', error)
      setFearGreedError(
        error instanceof Error
          ? error.message
          : 'Failed to load Fear & Greed history'
      )
    } finally {
      setFearGreedLoading(false)
    }
  }

  // Load analysis history on mount
  useEffect(() => {
    if (isAuthenticated) {
      loadAnalysisHistory()
    }
  }, [isAuthenticated, loadAnalysisHistory])

  // Load initial data on mount and set up periodic refresh
  useEffect(() => {
    const loadInitialData = async () => {
      await Promise.all([
        loadCurrentFearGreedData(),
        loadFearGreedHistory(),
        loadEconomicEvents()
      ])
    }

    loadInitialData()

    // Refresh current Fear & Greed data every 10 minutes (matching backend cache)
    const currentDataInterval = setInterval(
      loadCurrentFearGreedData,
      10 * 60 * 1000
    )

    // Refresh economic events every 30 minutes (less frequent)
    const economicEventsInterval = setInterval(
      loadEconomicEvents,
      30 * 60 * 1000
    )

    return () => {
      clearInterval(currentDataInterval)
      clearInterval(economicEventsInterval)
    }
  }, [])

  // Update progress every minute when analysis is running
  useEffect(() => {
    if (!isRunning) return

    const progressInterval = setInterval(() => {
      const newProgress = useAnalysisStore.getState().calculateProgress()
      useAnalysisStore.setState({ progress: newProgress })
    }, 60 * 1000) // Every minute

    return () => clearInterval(progressInterval)
  }, [isRunning])

  const handleStartAnalysis = async () => {
    // Update config with selected analysts
    updateConfig({
      analysts: selectedAnalysts,
      llmProvider: LLMProvider.OPENAI
    })

    await startAnalysis()
  }

  const handleStockSelect = (stock: StockSearchResult) => {
    updateConfig({ ticker: stock.symbol })
  }

  const handlePeriodChange = async (period: '1M' | '3M' | '6M' | '1Y') => {
    setSelectedPeriod(period)
    // Only reload history, not current data
    await loadFearGreedHistory(period)
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-semibold text-gray-900">
            AI 분석
          </h1>
          <p className="text-gray-600 mt-1 text-sm md:text-base">
            포괄적인 AI 기반 시장 분석 실행
          </p>
        </div>
      </div>

      {/* Dynamic Progress Visualization */}
      <AnalysisProgressVisualization
        isRunning={isRunning}
        isPaused={isPaused}
        currentAgent={currentAgent}
        progress={progress}
        agentStatus={agentStatus}
        messages={messages}
        startTime={startTime}
        currentSessionId={currentSessionId}
        llmCallCount={llmCallCount}
        toolCallCount={toolCallCount}
        selectedAnalysts={selectedAnalysts}
      />

      {/* Error Display */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <Card className="border-red-200 bg-red-50">
            <CardContent className="p-4">
              <div className="flex items-center gap-2 text-red-800">
                <Brain className="size-5" />
                <span className="font-medium">분석 오류</span>
              </div>
              <p className="text-sm text-red-700 mt-1">{error}</p>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Analysis Control */}
      {!isRunning && !isPaused && (
        <div>
          <h2 className="text-lg md:text-xl font-semibold text-gray-900 mb-4">
            새로운 분석 시작
          </h2>
          <Card>
            <CardHeader>
              <CardTitle className="text-lg md:text-xl">분석 설정</CardTitle>
              <CardDescription className="text-sm md:text-base">
                분석을 위한 에이전트와 설정을 선택하세요
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Ticker Input with Autocomplete */}
              <div>
                <label className="block text-sm md:text-base font-medium text-gray-700 mb-2">
                  주식 종목
                </label>
                <StockAutocomplete
                  value={config.ticker}
                  onChange={(value) =>
                    updateConfig({ ticker: value.toUpperCase() })
                  }
                  onSelect={handleStockSelect}
                  placeholder="종목 코드나 회사명으로 검색..."
                />
                <p className="text-xs md:text-sm text-gray-500 mt-1">
                  주식, ETF, 지수를 검색하려면 입력을 시작하세요
                </p>
              </div>

              {/* Analysis Date */}
              <div>
                <label className="block text-sm md:text-base font-medium text-gray-700 mb-2">
                  분석 날짜
                </label>
                <input
                  type="date"
                  value={config.analysisDate}
                  onChange={(e) =>
                    updateConfig({ analysisDate: e.target.value })
                  }
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
              </div>

              {/* Analyst Selection */}
              <div>
                <label className="block text-sm md:text-base font-medium text-gray-700 mb-3">
                  분석가 선택
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {analystOptions.map((analyst) => {
                    const isSelected = selectedAnalysts.includes(analyst)
                    return (
                      <div
                        key={analyst}
                        className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                          isSelected
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                        onClick={() => handleAnalystToggle(analyst)}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => {}} // Handled by div onClick
                            className="rounded text-blue-600"
                          />
                          <span className="text-sm md:text-base font-medium">
                            {getAnalystDisplayName(analyst)}
                          </span>
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>

              {/* Research Depth */}
              <div>
                <label className="block text-sm md:text-base font-medium text-gray-700 mb-2">
                  연구 깊이: {config.researchDepth}
                </label>
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={config.researchDepth}
                  onChange={(e) =>
                    updateConfig({ researchDepth: parseInt(e.target.value) })
                  }
                  className="w-full"
                />
                <div className="flex justify-between text-xs md:text-sm text-gray-500 mt-1">
                  <span>빠름</span>
                  <span>심층</span>
                </div>
              </div>

              {/* Start Button */}
              <Button
                onClick={handleStartAnalysis}
                disabled={
                  isLoading || selectedAnalysts.length === 0 || !config.ticker
                }
                className="w-full"
                size="lg"
              >
                {isLoading ? (
                  <>
                    <Clock className="size-4 mr-2 animate-spin" />
                    분석 시작 중...
                  </>
                ) : (
                  <>
                    <Play className="size-4 mr-2" />
                    분석 시작
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Enhanced Analysis Dashboard */}
      <div className="space-y-6">
        {/* Real-Time Chart and AI Insights */}

        {/* Market Sentiment and Analysis */}
        <div className="grid grid-cols-1 lg:grid-cols-1 gap-6">
          {/* Fear & Greed Index Chart */}

          {/* Current Fear & Greed Status */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.7 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-lg md:text-xl">
                  현재 시장 심리
                </CardTitle>
                <CardDescription className="text-sm md:text-base">
                  실시간 Fear & Greed Index 상태 및 분류
                </CardDescription>
              </CardHeader>
              <CardContent>
                {fearGreedLoading ? (
                  <div className="flex items-center justify-center h-[250px] md:h-[300px]">
                    <div className="text-gray-500 text-sm md:text-base">
                      심리 데이터 로딩 중...
                    </div>
                  </div>
                ) : fearGreedData ? (
                  <div className="space-y-6">
                    {/* Current Value Display */}
                    <div className="text-center">
                      <div
                        className="text-4xl md:text-6xl font-bold mb-2"
                        style={{
                          color: getFearGreedColor(fearGreedData.value)
                        }}
                      >
                        {fearGreedData.value}
                      </div>
                      <div className="text-lg md:text-xl font-semibold text-gray-700 mb-1">
                        {fearGreedData.classification}
                      </div>
                      <div className="text-xs md:text-sm text-gray-500">
                        마지막 업데이트:{' '}
                        {newKSTDate(fearGreedData.timestamp).toLocaleString(
                          'ko-KR'
                        )}
                      </div>
                    </div>

                    {/* Progress Bar */}
                    <div className="space-y-2">
                      <div className="flex justify-between text-xs md:text-sm text-gray-600">
                        <span>극도 공포</span>
                        <span>극도 탐욕</span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-4">
                        <div
                          className="h-4 rounded-full transition-all duration-500"
                          style={{
                            width: `${fearGreedData.value}%`,
                            backgroundColor: getFearGreedColor(
                              fearGreedData.value
                            )
                          }}
                        />
                      </div>
                      <div className="flex justify-between text-xs md:text-sm text-gray-500">
                        <span>0</span>
                        <span>25</span>
                        <span>50</span>
                        <span>75</span>
                        <span>100</span>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-[250px] md:h-[300px]">
                    <div className="text-gray-500 text-sm md:text-base">
                      사용 가능한 심리 데이터 없음
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>

      {/* Fear & Greed Index History */}
      <FearGreedHistoryChart
        fearGreedHistory={fearGreedHistory}
        economicEvents={economicEvents}
        fearGreedLoading={fearGreedLoading}
        fearGreedError={fearGreedError}
        selectedPeriod={selectedPeriod}
        onPeriodChange={handlePeriodChange}
      />

      {/* Analysis History */}
      {analysisHistory.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Recent Analysis Sessions</CardTitle>
              <CardDescription>
                Your recent analysis results and history
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {analysisHistory.slice(0, 5).map((session) => (
                  <div
                    key={session.session_id}
                    className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center gap-4">
                      <div className="p-2 bg-white rounded-lg shadow-sm">
                        <Brain className="size-5 text-gray-600" />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">
                          {session.ticker}
                        </p>
                        <p className="text-sm text-gray-600">
                          {newKSTDate(session.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p
                          className={`font-semibold ${
                            session.status === 'completed'
                              ? 'text-green-600'
                              : session.status === 'failed'
                                ? 'text-red-600'
                                : session.status === 'running'
                                  ? 'text-blue-600'
                                  : 'text-yellow-600'
                          }`}
                        >
                          {session.status.charAt(0).toUpperCase() +
                            session.status.slice(1)}
                        </p>
                        {session.confidence_score && (
                          <p className="text-sm text-gray-500">
                            {Math.round(session.confidence_score * 100)}%
                            confidence
                          </p>
                        )}
                      </div>
                      <div className="text-xs text-gray-400">
                        {session.execution_time_seconds
                          ? `${Math.round(
                              session.execution_time_seconds / 60
                            )}min`
                          : 'In progress'}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </div>
  )
}

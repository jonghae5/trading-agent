import React, { useEffect, useState, useMemo, useCallback } from 'react'
import { motion } from 'framer-motion'
import { Brain, Play, Clock } from 'lucide-react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Scatter
} from 'recharts'

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
import { AnalysisProgressVisualization } from '../components/analysis'
import {
  fearGreedApi,
  FearGreedIndexData,
  FearGreedHistoricalData,
  MarketSentimentSummary
} from '../api/client'
import { economicApi, EconomicEvent } from '../api/economic'

// Helper function to get Fear & Greed color
const getFearGreedColor = (value: number): string => {
  if (value <= 25) return '#dc2626' // red-600 - Extreme Fear
  if (value <= 45) return '#ea580c' // orange-600 - Fear
  if (value <= 55) return '#65a30d' // lime-600 - Neutral
  if (value <= 75) return '#16a34a' // green-600 - Greed
  return '#059669' // emerald-600 - Extreme Greed
}

export const Analysis: React.FC = () => {
  const {
    isRunning,
    isPaused,
    currentAgent,
    progress,
    messages,
    agentStatus,
    reportSections,
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
  const [sentimentSummary, setSentimentSummary] =
    useState<MarketSentimentSummary | null>(null)
  const [fearGreedLoading, setFearGreedLoading] = useState(false)
  const [fearGreedError, setFearGreedError] = useState<string | null>(null)

  // Economic events state
  const [economicEvents, setEconomicEvents] = useState<EconomicEvent[]>([])
  const [eventsLoading, setEventsLoading] = useState(false)

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
    setEventsLoading(true)
    try {
      // Get events for the last 5 years to match Fear & Greed data range
      const endDate = new Date()
      const startDate = new Date()
      startDate.setFullYear(startDate.getFullYear() - 5)

      const response = await economicApi.getEconomicEvents({
        startDate: startDate.toISOString().split('T')[0],
        endDate: endDate.toISOString().split('T')[0],
        minSeverity: 'medium'
      })

      setEconomicEvents(response.events)
    } catch (error) {
      console.error('Failed to load economic events:', error)
    } finally {
      setEventsLoading(false)
    }
  }

  // Load Fear & Greed Index data
  const loadFearGreedData = async () => {
    setFearGreedLoading(true)
    setFearGreedError(null)

    try {
      const [history, summary] = await Promise.all([
        fearGreedApi.getHistory(1825, 'daily'), // Last 5 years, daily data
        fearGreedApi.getSentimentSummary()
      ])

      const current = {
        ...summary.current,
        previous_close: summary.historical_comparison?.previous_close || 0,
        one_week_ago: summary.historical_comparison?.one_week_ago || 0
      }
      setFearGreedData(current)
      setFearGreedHistory(history)
      setSentimentSummary(summary)
    } catch (error) {
      console.error('Failed to load Fear & Greed Index data:', error)
      setFearGreedError(
        error instanceof Error
          ? error.message
          : 'Failed to load Fear & Greed data'
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

  // Load Fear & Greed Index data on mount and periodically
  useEffect(() => {
    const loadAllData = async () => {
      await Promise.all([loadFearGreedData(), loadEconomicEvents()])
    }

    loadAllData()

    // Refresh every 15 minutes
    const interval = setInterval(loadAllData, 15 * 60 * 1000)

    return () => clearInterval(interval)
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
                  showPopularStocks={true}
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
                            {analyst}
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
                        {new Date(fearGreedData.timestamp).toLocaleString(
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
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.8 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Fear & Greed Index History</CardTitle>
            <CardDescription>
              CNN Fear & Greed Index - 5년간 시장 심리 변화 추이
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              {fearGreedLoading ? (
                <div className="flex items-center justify-center h-[400px]">
                  <div className="text-gray-500">
                    Loading historical data...
                  </div>
                </div>
              ) : fearGreedError ? (
                <div className="flex items-center justify-center h-[400px]">
                  <div className="text-red-500">Error: {fearGreedError}</div>
                </div>
              ) : fearGreedHistory?.data && fearGreedHistory.data.length > 0 ? (
                <AreaChart
                  data={fearGreedHistory.data
                    .slice()
                    .reverse()
                    .map((item) => ({
                      date: item.date,
                      value: item.value,
                      classification: item.classification
                    }))}
                  margin={{ top: 20, right: 30, left: 20, bottom: 60 }}
                >
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="date"
                    fontSize={11}
                    interval={Math.floor(fearGreedHistory.data.length / 20)}
                    tickFormatter={(value) => {
                      const date = new Date(value)
                      return `${date.getFullYear()}-${String(
                        date.getMonth() + 1
                      ).padStart(2, '0')}`
                    }}
                    angle={-45}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis
                    domain={[0, 100]}
                    fontSize={12}
                    label={{
                      value: 'Fear & Greed Index',
                      angle: -90,
                      position: 'insideLeft'
                    }}
                    tickFormatter={(value) => `${value}`}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (!active || !payload || !payload.length) return null

                      const data = payload[0].payload

                      // Check if this is scatter data (economic events)
                      const isEventData = payload.some(
                        (p) => p.payload?.eventTitle
                      )

                      if (isEventData) {
                        const eventData = payload.find(
                          (p) => p.payload?.eventTitle
                        )?.payload

                        return (
                          <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-sm">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="text-lg">
                                {eventData.eventIcon}
                              </span>
                              <span className="font-semibold text-sm">
                                {eventData.eventTitle}
                              </span>
                            </div>
                            <p className="text-xs text-gray-600 mb-2">
                              {eventData.eventDescription}
                            </p>
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-xs text-gray-500">
                                {new Date(
                                  eventData.eventDate
                                ).toLocaleDateString('ko-KR')}
                              </span>
                              <span
                                className={`px-2 py-1 rounded text-xs font-medium ${
                                  eventData.severity === 'critical'
                                    ? 'bg-red-100 text-red-800'
                                    : eventData.severity === 'high'
                                      ? 'bg-orange-100 text-orange-800'
                                      : 'bg-yellow-100 text-yellow-800'
                                }`}
                              >
                                {eventData.severity === 'critical'
                                  ? '매우높음'
                                  : eventData.severity === 'high'
                                    ? '높음'
                                    : '보통'}
                              </span>
                            </div>
                            <div className="pt-2 border-t">
                              <div className="text-xs text-gray-700">
                                <strong>Fear & Greed Index:</strong>{' '}
                                {eventData.value}
                              </div>
                              <div
                                className="text-xs"
                                style={{
                                  color: getFearGreedColor(eventData.value)
                                }}
                              >
                                <strong>{eventData.classification}</strong>
                              </div>
                            </div>
                          </div>
                        )
                      }

                      // Regular Fear & Greed tooltip
                      return (
                        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                          <div className="font-medium text-sm">
                            {new Date(label).toLocaleDateString('ko-KR', {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric'
                            })}
                          </div>
                          <div
                            className="text-lg font-bold"
                            style={{ color: getFearGreedColor(data.value) }}
                          >
                            {data.value}
                          </div>
                          <div className="text-sm text-gray-600">
                            {data.classification}
                          </div>
                        </div>
                      )
                    }}
                  />

                  <defs>
                    <linearGradient
                      id="fearGreedGradient"
                      x1="0"
                      y1="0"
                      x2="0"
                      y2="1"
                    >
                      <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.6} />
                      <stop
                        offset="50%"
                        stopColor="#6366f1"
                        stopOpacity={0.4}
                      />
                      <stop
                        offset="100%"
                        stopColor="#3b82f6"
                        stopOpacity={0.2}
                      />
                    </linearGradient>
                  </defs>

                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#1e40af"
                    fill="url(#fearGreedGradient)"
                    strokeWidth={3}
                    name="Fear & Greed Index"
                  />

                  {/* Reference lines for different zones */}
                  <ReferenceLine
                    y={25}
                    stroke="#dc2626"
                    strokeDasharray="3 3"
                    strokeOpacity={0.6}
                    strokeWidth={1}
                  />
                  <ReferenceLine
                    y={45}
                    stroke="#ea580c"
                    strokeDasharray="3 3"
                    strokeOpacity={0.6}
                    strokeWidth={1}
                  />
                  <ReferenceLine
                    y={55}
                    stroke="#65a30d"
                    strokeDasharray="3 3"
                    strokeOpacity={0.6}
                    strokeWidth={1}
                  />
                  <ReferenceLine
                    y={75}
                    stroke="#059669"
                    strokeDasharray="3 3"
                    strokeOpacity={0.6}
                    strokeWidth={1}
                  />

                  {/* Economic Events Overlay */}
                  {economicEvents.length > 0 && (
                    <Scatter
                      data={(() => {
                        interface EventDataPoint {
                          date: string
                          value: number
                          eventTitle: string
                          eventDescription: string
                          eventDate: string
                          eventColor?: string
                          eventIcon?: string
                          severity: string
                          classification: string
                        }
                        const eventData: EventDataPoint[] = []

                        economicEvents.forEach((event) => {
                          const eventDate = new Date(event.date)

                          // Find closest Fear & Greed data point
                          let closestData: any = null
                          let minDiff = Infinity

                          fearGreedHistory.data.forEach((item) => {
                            const itemDate = new Date(item.date)
                            const timeDiff = Math.abs(
                              eventDate.getTime() - itemDate.getTime()
                            )

                            if (timeDiff < minDiff) {
                              minDiff = timeDiff
                              closestData = item
                            }
                          })

                          if (
                            closestData &&
                            minDiff < 90 * 24 * 60 * 60 * 1000
                          ) {
                            // Within 90 days
                            eventData.push({
                              date: event.date,
                              value: closestData.value,
                              eventTitle: event.title,
                              eventDescription: event.description,
                              eventDate: event.detail_date,
                              eventColor: event.color,
                              eventIcon: event.icon,
                              severity: event.severity,
                              classification: closestData.classification
                            })
                          }
                        })

                        return eventData
                      })()}
                      fill="#8884d8"
                      shape={(props: any) => {
                        const { payload, cx, cy } = props
                        if (!payload || !cx || !cy) return <g />

                        let radius = 4
                        if (payload.severity === 'critical') radius = 8
                        else if (payload.severity === 'high') radius = 6

                        return (
                          <circle
                            cx={cx}
                            cy={cy}
                            r={radius}
                            fill={payload.eventColor || '#8884d8'}
                            stroke="white"
                            strokeWidth={2}
                            style={{
                              cursor: 'pointer',
                              filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3))',
                              opacity: 0.9
                            }}
                          />
                        )
                      }}
                    />
                  )}
                </AreaChart>
              ) : (
                <div className="flex items-center justify-center h-[400px]">
                  <div className="text-gray-500">
                    No historical data available
                  </div>
                </div>
              )}
            </ResponsiveContainer>

            {/* Legend */}
            <div className="flex justify-center mt-4 space-x-6 text-xs">
              <div className="flex items-center">
                <div className="w-3 h-3 bg-red-600 rounded mr-1"></div>
                <span>Extreme Fear (0-25)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-orange-600 rounded mr-1"></div>
                <span>Fear (25-45)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-lime-600 rounded mr-1"></div>
                <span>Neutral (45-55)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-green-600 rounded mr-1"></div>
                <span>Greed (55-75)</span>
              </div>
              <div className="flex items-center">
                <div className="w-3 h-3 bg-emerald-600 rounded mr-1"></div>
                <span>Extreme Greed (75-100)</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

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
                          {new Date(session.created_at).toLocaleDateString()}
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

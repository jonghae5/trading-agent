import React, { useState, useEffect, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts'
import { AlertTriangle, Info, Calendar, RefreshCw } from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import { economicApi, economicUtils } from '../api'
import { getKSTDate, newKSTDate } from '../lib/utils'
import type {
  HistoricalDataResponse,
  EconomicObservation
} from '../api/economic'

// Time range options
const TIME_RANGES = {
  '1Y': { label: '1년', years: 1 },
  '5Y': { label: '5년', years: 5 },
  '10Y': { label: '10년', years: 10 },
  '20Y': { label: '20년', years: 20 }
} as const

type TimeRange = keyof typeof TIME_RANGES

// Indicator categories for better organization - Merged for simplicity
const INDICATOR_CATEGORIES = {
  growthEmployment: {
    title: '성장 & 고용',
    description: 'GDP, 산업생산, 실업률, 일자리',
    indicators: ['GDP', 'INDPRO', 'TCU', 'UNRATE', 'PAYEMS', 'ICSA']
  },
  inflationMonetary: {
    title: '인플레이션 & 통화정책',
    description: 'CPI, 인플레이션 기대, 연방기준금리, 수익률곡선',
    indicators: ['CPIAUCSL', 'PCEPILFE', 'T5YIE', 'FEDFUNDS', 'DGS10', 'DGS2', 'T10Y2Y']
  },
  financialRisk: {
    title: '금융 & 시장위험',
    description: '금융상황지수, 회사채 스프레드, VIX, 소비자심리',
    indicators: ['NFCI', 'BAMLH0A0HYM2', 'BAA', 'VIXCLS', 'UMCSENT', 'DPHILBSRMQ']
  },
  realEstateDebt: {
    title: '부동산 & 부채',
    description: '모기지금리, 주택가격, 정부부채, GDP 대비 부채, 기업부채',
    indicators: ['MORTGAGE30US', 'NYUCSFRCONDOSMSAMID', 'GFDEBTN', 'GFDEGDQ188S', 'NCBDBIQ027S']
  },
  fiscal: {
    title: '재정 & 글로벌',
    description: '재정수지, 달러지수, 30년 국채',
    indicators: ['FYFSGDA188S', 'DTWEXBGS', 'DGS30']
  }
} as const

// Indicator display information
const INDICATOR_INFO = {
  // 성장 & 생산성
  GDP: { name: 'GDP (총생산)', unit: '조달러', color: '#10b981', icon: '📈' },
  INDPRO: { name: '산업생산지수', unit: '', color: '#2563eb', icon: '🏭' },
  TCU: { name: '설비가동률', unit: '%', color: '#0891b2', icon: '⚙️' },

  // 고용 & 노동시장
  UNRATE: { name: '실업률', unit: '%', color: '#ef4444', icon: '👥' },
  PAYEMS: { name: '비농업 일자리', unit: '천명', color: '#059669', icon: '👨‍💼' },
  ICSA: { name: '실업수당 신청', unit: '천건', color: '#dc2626', icon: '📄' },

  // 물가 & 인플레이션
  CPIAUCSL: {
    name: 'CPI (소비자물가지수)',
    unit: '%',
    color: '#f59e0b',
    icon: '📊'
  },
  PCEPILFE: { name: '코어 PCE', unit: '%', color: '#ea580c', icon: '🎯' },

  // 통화정책 & 금리
  FEDFUNDS: { name: '연방기준금리', unit: '%', color: '#6366f1', icon: '🏦' },
  DGS10: { name: '10년 국채수익률', unit: '%', color: '#3b82f6', icon: '📈' },
  DGS2: { name: '2년 국채수익률', unit: '%', color: '#06b6d4', icon: '📈' },
  T10Y2Y: {
    name: '수익률곡선 (10년-2년)',
    unit: '%',
    color: '#8b5cf6',
    icon: '📊'
  },

  // 재정정책 & 부채
  GFDEGDQ188S: {
    name: 'GDP 대비 연방부채비율',
    unit: '%',
    color: '#dc2626',
    icon: '💳'
  },
  FYFSGDA188S: {
    name: '연방정부 재정수지',
    unit: '%',
    color: '#059669',
    icon: '💰'
  },
  GFDEBTN: {
    name: '연방정부 총부채',
    unit: '조달러',
    color: '#dc2626',
    icon: '💸'
  },
  NCBDBIQ027S: {
    name: '기업 총부채',
    unit: '조달러',
    color: '#0ea5e9',
    icon: '🏢'
  },

  // 금융시장 & 위험
  VIXCLS: { name: 'VIX 변동성 지수', unit: '', color: '#ef4444', icon: '⚡' },
  DGS30: { name: '30년 국채수익률', unit: '%', color: '#1f2937', icon: '📈' },
  MORTGAGE30US: {
    name: '30년 모기지금리',
    unit: '%',
    color: '#f59e0b',
    icon: '🏘️'
  },
  UMCSENT: {
    name: '미시간대 소비자심리',
    unit: '',
    color: '#16a34a',
    icon: '💭'
  },
  NYUCSFRCONDOSMSAMID: {
    name: 'NYU 콘도/코압 가격지수 (맨해튼)',
    unit: '',
    color: '#0ea5e9',
    icon: '🏢'
  },

  // 인플레이션 기대치
  T5YIE: {
    name: '5년 인플레이션 기대치',
    unit: '%',
    color: '#f97316',
    icon: '🔥'
  },

  // 금융상황지수
  NFCI: {
    name: '시카고연은 금융상황지수',
    unit: '',
    color: '#8b5cf6',
    icon: '📊'
  },

  // 지역 제조업지수
  DPHILBSRMQ: {
    name: '필라델피아연은 제조업지수',
    unit: '',
    color: '#10b981',
    icon: '🏭'
  },
  BAA: {
    name: '무디스 BAA 회사채 수익률',
    unit: '%',
    color: '#f59e0b',
    icon: '📈'
  },
  BAMLH0A0HYM2: {
    name: '고수익 회사채 스프레드',
    unit: '%',
    color: '#dc2626',
    icon: '⚠️'
  },

  // 글로벌 연결성 (연준)
  DTWEXBGS: {
    name: '무역가중 달러지수',
    unit: '',
    color: '#8b5cf6',
    icon: '🌍'
  }
} as const

// Utility functions
const formatValue = (value: number, unit: string): string => {
  if (unit === '%') {
    return `${value.toFixed(2)}%`
  }
  if (unit === '조달러') {
    return `$${(value / 1000).toFixed(1)}조`
  }
  if (unit === '천호') {
    return `${(value / 1000).toFixed(0)}K`
  }
  if (unit === '$/배럴' || unit === '$/온스') {
    return `$${value.toFixed(2)}`
  }
  // Manufacturing and production indices (typically around 100)
  if (unit === '' && value > 30 && value < 200) {
    return value.toFixed(1)
  }
  return value.toFixed(2)
}

const getChangeColor = (change: number) => {
  if (change > 0) return '#10b981'
  if (change < 0) return '#ef4444'
  return '#6b7280'
}

const calculateChange = (data: EconomicObservation[]): number => {
  if (data.length < 2) return 0
  const latest = data[data.length - 1].value
  const previous = data[data.length - 2].value
  return ((latest - previous) / previous) * 100
}

export const Economics: React.FC = () => {
  // State management
  const [selectedTimeRange, setSelectedTimeRange] = useState<TimeRange>('10Y')
  const [selectedCategory, setSelectedCategory] =
    useState<keyof typeof INDICATOR_CATEGORIES>('growth')
  const [historicalData, setHistoricalData] =
    useState<HistoricalDataResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showEvents, setShowEvents] = useState(true)
  const [lastUpdate, setLastUpdate] = useState(getKSTDate())

  // Load economic data
  const loadEconomicData = useCallback(async () => {
    setIsLoading(true)
    setError(null)

    try {
      const startDate = economicUtils.getDateYearsAgo(
        TIME_RANGES[selectedTimeRange].years
      )
      const endDate = getKSTDate().toISOString().split('T')[0]

      const indicators = INDICATOR_CATEGORIES[selectedCategory].indicators

      const data = await economicApi.getHistoricalData({
        indicators: [...indicators],
        startDate,
        endDate,
        includeEvents: showEvents,
        minSeverity: 'medium' // Only show medium+ severity events
      })

      // Aggregate to monthly data for long periods (10Y, 20Y)
      if (economicUtils.shouldAggregateData(startDate, endDate)) {
        const aggregatedData = { ...data }
        Object.keys(aggregatedData.indicators).forEach((indicator) => {
          aggregatedData.indicators[indicator] =
            economicUtils.aggregateToMonthly(
              aggregatedData.indicators[indicator]
            )
        })
        setHistoricalData(aggregatedData)
      } else {
        setHistoricalData(data)
      }
      setLastUpdate(getKSTDate())
    } catch (err) {
      console.error('Failed to load economic data:', err)
      setError('경제 데이터를 불러오는데 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [selectedTimeRange, selectedCategory, showEvents])

  // Load data on component mount and when dependencies change
  useEffect(() => {
    loadEconomicData()
  }, [loadEconomicData])

  const handleRefresh = () => {
    loadEconomicData()
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="space-y-4 mb-6">
        <div>
          <h1 className="text-xl sm:text-2xl font-semibold text-gray-900">
            📊 거시경제 지표
          </h1>
          <p className="text-sm sm:text-base text-gray-600 mt-1">
            FRED API를 통한 실제 경제지표와 주요 경제사건 분석
          </p>
          <div className="mt-3 p-3 bg-blue-50 rounded-lg">
            <h4 className="font-semibold text-sm mb-2 text-blue-800">
              💡 분석 순서 가이드
            </h4>
            <div className="text-xs sm:text-sm text-blue-800">
              <p>
                <strong>1. 성장&고용:</strong> GDP, 산업생산, 실업률, 일자리로 
                경제 성장과 고용상황 종합 분석
              </p>
              <p>
                <strong>2. 인플레이션&통화정책:</strong> CPI, 인플레이션 기대치, 
                연준금리, 수익률곡선으로 물가와 통화정책 방향 예측
              </p>
              <p>
                <strong>3. 금융&시장위험:</strong> 금융상황지수, 회사채 스프레드, 
                VIX, 소비자심리로 금융시스템 안정성과 시장 위험도 체크
              </p>
              <p>
                <strong>4. 부동산&부채:</strong> 모기지금리, 주택가격, 정부부채, 
                GDP 대비 부채비율로 부동산시장과 레버리지 위험 분석
              </p>
              <p>
                <strong>5. 재정&글로벌:</strong> 재정수지, 달러지수, 30년 국채로 
                재정정책과 글로벌 거시경제 리스크 평가
              </p>
            </div>
          </div>
        </div>

        {/* Controls - Mobile Optimized */}
        <div className="space-y-3">
          {/* Time Range Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 sm:hidden">
              기간 선택
            </label>
            <div className="grid grid-cols-2 sm:flex sm:items-center gap-1 bg-gray-100 rounded-lg p-1">
              {Object.entries(TIME_RANGES).map(([key, range]) => (
                <button
                  key={key}
                  onClick={() => setSelectedTimeRange(key as TimeRange)}
                  className={`px-2 sm:px-3 py-2 sm:py-1 text-xs sm:text-sm rounded-md transition-colors font-medium ${
                    selectedTimeRange === key
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  {range.label}
                </button>
              ))}
            </div>
          </div>

          {/* Category Selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2 sm:hidden">
              지표 카테고리
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:flex lg:items-center gap-1 bg-gray-100 rounded-lg p-1">
              {Object.entries(INDICATOR_CATEGORIES).map(([key, category]) => (
                <button
                  key={key}
                  onClick={() =>
                    setSelectedCategory(
                      key as keyof typeof INDICATOR_CATEGORIES
                    )
                  }
                  className={`px-2 sm:px-3 py-2 sm:py-1 text-xs sm:text-sm rounded-md transition-colors whitespace-nowrap font-medium ${
                    selectedCategory === key
                      ? 'bg-white text-blue-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                  title={category.description}
                >
                  {category.title}
                </button>
              ))}
            </div>
            {/* Category Description */}
            <div className="mt-2 text-xs text-gray-600 sm:hidden">
              {INDICATOR_CATEGORIES[selectedCategory]?.description ||
                '지표 설명을 불러오는 중...'}
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-3">
            {/* Events Toggle */}
            <Button
              variant={showEvents ? 'default' : 'outline'}
              size="sm"
              onClick={() => setShowEvents(!showEvents)}
              className="w-full sm:w-auto"
            >
              <AlertTriangle className="size-4 mr-2" />
              경제사건 {showEvents ? '켜짐' : '꺼짐'}
            </Button>

            {/* Refresh Section */}
            <div className="flex flex-col sm:flex-row sm:items-center gap-2">
              <div className="text-xs sm:text-sm text-gray-500 text-center sm:text-left">
                <Calendar className="inline size-4 mr-1" />
                <span className="hidden sm:inline">
                  {lastUpdate.toLocaleString('ko-KR')}
                </span>
                <span className="sm:hidden">
                  {lastUpdate.toLocaleString('ko-KR', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={isLoading}
                className="w-full sm:w-auto"
              >
                <RefreshCw
                  className={`size-4 mr-2 ${isLoading ? 'animate-spin' : ''}`}
                />
                새로고침
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-red-50 border border-red-200 rounded-lg p-4"
        >
          <div className="flex items-center gap-2 text-red-800">
            <AlertTriangle className="size-5" />
            <span className="font-medium">데이터 로딩 오류</span>
          </div>
          <p className="text-red-600 mt-1">{error}</p>
        </motion.div>
      )}

      {/* Loading State */}
      {isLoading && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center justify-center py-12"
        >
          <div className="text-center">
            <RefreshCw className="size-8 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-gray-600">경제 데이터를 불러오는 중...</p>
          </div>
        </motion.div>
      )}

      {/* Data Display */}
      {historicalData && !isLoading && (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {INDICATOR_CATEGORIES[selectedCategory].indicators.map(
              (indicator, index) => {
                const data = historicalData.indicators[indicator] || []
                const info =
                  INDICATOR_INFO[indicator as keyof typeof INDICATOR_INFO]
                const latest = data[data.length - 1]
                const change = calculateChange(data)

                if (!latest || !info) return null

                return (
                  <motion.div
                    key={indicator}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium flex items-center gap-2">
                          <span className="text-lg">{info.icon}</span>
                          {info.name}
                        </CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="text-2xl font-bold">
                          {formatValue(latest.value, info.unit)}
                        </div>
                        <div
                          className="text-sm flex items-center gap-1"
                          style={{ color: getChangeColor(change) }}
                        >
                          전기 대비 {change > 0 ? '+' : ''}
                          {change.toFixed(2)}%
                        </div>
                        <ResponsiveContainer width="100%" height={60}>
                          <AreaChart data={data.slice(-20)}>
                            <Area
                              type="monotone"
                              dataKey="value"
                              stroke={info.color}
                              fill={info.color}
                              fillOpacity={0.1}
                              strokeWidth={2}
                            />
                          </AreaChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                  </motion.div>
                )
              }
            )}
          </div>

          {/* Main Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {INDICATOR_CATEGORIES[selectedCategory].indicators
              .slice(0, 10)
              .map((indicator, index) => {
                const data = historicalData.indicators[indicator] || []
                const info =
                  INDICATOR_INFO[indicator as keyof typeof INDICATOR_INFO]
                const events = showEvents ? historicalData.events : []

                if (!data.length || !info) return null

                return (
                  <motion.div
                    key={indicator}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.5 + index * 0.1 }}
                  >
                    <Card>
                      <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                          <span className="text-xl">{info.icon}</span>
                          {info.name}
                        </CardTitle>
                        <CardDescription>
                          {TIME_RANGES[selectedTimeRange].label} 동안의 추이
                        </CardDescription>
                      </CardHeader>
                      <CardContent>
                        <ResponsiveContainer width="100%" height={300}>
                          <LineChart
                            data={(() => {
                              // Combine line data with event data for better rendering
                              const combinedData = [...data]

                              // Add event points to the dataset with priority sorting
                              const priorityEvents = events
                                .filter((event) =>
                                  ['critical', 'high', 'medium'].includes(
                                    event.severity
                                  )
                                )
                                .sort((a, b) => {
                                  // Sort by severity first (critical > high > medium)
                                  const severityOrder = {
                                    critical: 0,
                                    high: 1,
                                    medium: 2,
                                    low: 3
                                  }
                                  if (
                                    severityOrder[a.severity] !==
                                    severityOrder[b.severity]
                                  ) {
                                    return (
                                      severityOrder[a.severity] -
                                      severityOrder[b.severity]
                                    )
                                  }
                                  // Then by date
                                  return (
                                    newKSTDate(a.date).getTime() -
                                    newKSTDate(b.date).getTime()
                                  )
                                })

                              priorityEvents.forEach((event) => {
                                const eventDate = newKSTDate(event.date)

                                // Find closest data point for Y position
                                let yValue = null
                                const exactMatch = data.find((d) => {
                                  const dataDate = newKSTDate(d.date)
                                  return (
                                    Math.abs(
                                      dataDate.getTime() - eventDate.getTime()
                                    ) <
                                    30 * 24 * 60 * 60 * 1000
                                  )
                                })

                                if (exactMatch) {
                                  yValue = exactMatch.value
                                } else {
                                  // Interpolate between closest points
                                  const beforePoint = data
                                    .filter(
                                      (d) => newKSTDate(d.date) <= eventDate
                                    )
                                    .slice(-1)[0]
                                  const afterPoint = data.filter(
                                    (d) => newKSTDate(d.date) >= eventDate
                                  )[0]

                                  if (beforePoint && afterPoint) {
                                    yValue =
                                      (beforePoint.value + afterPoint.value) / 2
                                  } else if (beforePoint) {
                                    yValue = beforePoint.value
                                  } else if (afterPoint) {
                                    yValue = afterPoint.value
                                  }
                                }

                                if (yValue !== null) {
                                  combinedData.push({
                                    date: event.date,
                                    value: yValue,
                                    isEvent: true,
                                    eventData: event
                                  } as any)
                                }
                              })

                              return combinedData.sort(
                                (a, b) =>
                                  new Date(a.date).getTime() -
                                  new Date(b.date).getTime()
                              )
                            })()}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="date"
                              fontSize={12}
                              tickFormatter={(value) => {
                                const date = newKSTDate(value)
                                return date.getFullYear().toString()
                              }}
                            />
                            <YAxis fontSize={12} />
                            <Tooltip
                              content={({ active, payload, label }) => {
                                if (!active || !payload || !payload.length)
                                  return null

                                const data = payload[0].payload

                                if (data.isEvent) {
                                  const event = data.eventData
                                  return (
                                    <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3 max-w-sm">
                                      <div className="flex items-center gap-2 mb-2">
                                        <span className="text-lg">
                                          {event.icon}
                                        </span>
                                        <span className="font-semibold text-sm">
                                          {event.title}
                                        </span>
                                      </div>
                                      <p className="text-xs text-gray-600 mb-2">
                                        {event.description}
                                      </p>
                                      <div className="flex items-center justify-between">
                                        <span className="text-xs text-gray-500">
                                          {newKSTDate(
                                            event.detail_date
                                          ).toLocaleDateString('ko-KR')}
                                        </span>
                                        <span
                                          className={`px-2 py-1 rounded text-xs font-medium ${
                                            event.severity === 'critical'
                                              ? 'bg-red-100 text-red-800'
                                              : event.severity === 'high'
                                                ? 'bg-orange-100 text-orange-800'
                                                : 'bg-yellow-100 text-yellow-800'
                                          }`}
                                        >
                                          {event.severity === 'critical'
                                            ? '매우높음'
                                            : event.severity === 'high'
                                              ? '높음'
                                              : '보통'}
                                        </span>
                                      </div>
                                      <div className="mt-2 pt-2 border-t">
                                        <div className="text-xs text-gray-700">
                                          <strong>{info.name}:</strong>{' '}
                                          {formatValue(data.value, info.unit)}
                                        </div>
                                      </div>
                                    </div>
                                  )
                                }

                                return (
                                  <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                                    <div className="font-medium text-sm">
                                      {newKSTDate(label).toLocaleDateString(
                                        'ko-KR'
                                      )}
                                    </div>
                                    <div
                                      className="text-lg font-bold"
                                      style={{ color: info.color }}
                                    >
                                      {formatValue(
                                        Number(payload[0].value) || 0,
                                        info.unit
                                      )}
                                    </div>
                                  </div>
                                )
                              }}
                            />
                            <Line
                              type="monotone"
                              dataKey="value"
                              stroke={info.color}
                              strokeWidth={2}
                              dot={(props: any) => {
                                if (props.payload?.isEvent) {
                                  const event = props.payload.eventData
                                  return (
                                    <circle
                                      cx={props.cx}
                                      cy={props.cy}
                                      r={
                                        event.severity === 'critical'
                                          ? 8
                                          : event.severity === 'high'
                                            ? 6
                                            : 4
                                      }
                                      fill={event.color}
                                      stroke="#ffffff"
                                      strokeWidth={2}
                                      style={{
                                        cursor: 'pointer',
                                        filter:
                                          'drop-shadow(0 2px 4px rgba(0,0,0,0.3))'
                                      }}
                                    />
                                  )
                                }
                                return <></>
                              }}
                            />
                          </LineChart>
                        </ResponsiveContainer>

                        {/* Event Legend */}
                        {events.length > 0 && (
                          <div className="mt-4 space-y-2">
                            <h4 className="text-sm font-medium text-gray-700">
                              주요 경제사건
                            </h4>
                            <div className="space-y-1">
                              {events.slice(0, 3).map((event, eventIndex) => (
                                <div
                                  key={eventIndex}
                                  className="flex items-center gap-2 text-xs"
                                >
                                  <div
                                    className="w-3 h-3 rounded-full"
                                    style={{ backgroundColor: event.color }}
                                  />
                                  <span className="text-gray-600">
                                    {newKSTDate(
                                      event.detail_date
                                    ).getFullYear()}
                                    : {event.title}
                                  </span>
                                </div>
                              ))}
                              {events.length > 3 && (
                                <div className="text-xs text-gray-500">
                                  +{events.length - 3}개 더
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </CardContent>
                    </Card>
                  </motion.div>
                )
              })}
          </div>
        </>
      )}

      {/* Economic Events Summary */}
      {historicalData && showEvents && historicalData.events.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
        >
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Info className="size-5 text-blue-600" />
                주요 경제사건 ({TIME_RANGES[selectedTimeRange].label})
              </CardTitle>
              <CardDescription>
                선택된 기간 동안의 주요 경제사건과 위기
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {historicalData.events
                  .filter(
                    (event) =>
                      event.severity === 'critical' || event.severity === 'high'
                  )
                  .slice(0, 9)
                  .map((event, index) => (
                    <div key={index} className="border rounded-lg p-3">
                      <div className="flex items-start gap-3">
                        <div
                          className="w-3 h-3 rounded-full mt-1 flex-shrink-0"
                          style={{ backgroundColor: event.color }}
                        />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-lg">{event.icon}</span>
                            <span className="font-medium text-sm">
                              {event.title}
                            </span>
                          </div>
                          <p className="text-xs text-gray-600 mb-2">
                            {event.description}
                          </p>
                          <div className="flex items-center justify-between text-xs">
                            <span className="text-gray-500">
                              {newKSTDate(event.detail_date).toLocaleDateString(
                                'ko-KR'
                              )}
                            </span>
                            <span
                              className={`px-2 py-1 rounded text-xs font-medium ${
                                event.severity === 'critical'
                                  ? 'bg-red-100 text-red-800'
                                  : event.severity === 'high'
                                    ? 'bg-orange-100 text-orange-800'
                                    : event.severity === 'medium'
                                      ? 'bg-yellow-100 text-yellow-800'
                                      : 'bg-gray-100 text-gray-800'
                              }`}
                            >
                              {event.severity === 'critical'
                                ? '매우높음'
                                : event.severity === 'high'
                                  ? '높음'
                                  : event.severity === 'medium'
                                    ? '보통'
                                    : '낮음'}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </CardContent>
          </Card>
        </motion.div>
      )}

      {/* Footer Note */}
      <div className="text-center text-sm text-gray-500 mt-8">
        <p>💡 데이터 출처: Federal Reserve Economic Data (FRED)</p>
        <p>실제 거래 전 공식 데이터를 확인하시기 바랍니다.</p>
      </div>
    </div>
  )
}

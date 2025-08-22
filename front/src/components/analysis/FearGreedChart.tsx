import React, { memo } from 'react'
import { motion } from 'framer-motion'
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
} from '../ui/card'
import { FearGreedIndexData, FearGreedHistoricalData } from '../../api/client'
import { EconomicEvent } from '../../api/economic'
import { newKSTDate } from '../../lib/utils'

// Helper function to get Fear & Greed color
const getFearGreedColor = (value: number): string => {
  if (value <= 25) return '#dc2626' // red-600 - Extreme Fear
  if (value <= 45) return '#ea580c' // orange-600 - Fear
  if (value <= 55) return '#65a30d' // lime-600 - Neutral
  if (value <= 75) return '#16a34a' // green-600 - Greed
  return '#059669' // emerald-600 - Extreme Greed
}

interface FearGreedChartProps {
  fearGreedData: FearGreedIndexData | null
  fearGreedHistory: FearGreedHistoricalData | null
  economicEvents: EconomicEvent[]
  loading: boolean
  error: string | null
}

export const FearGreedChart = memo<FearGreedChartProps>(
  ({ fearGreedData, fearGreedHistory, economicEvents, loading, error }) => {
    return (
      <div className="space-y-6">
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
              {loading ? (
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
                {loading ? (
                  <div className="flex items-center justify-center h-[400px]">
                    <div className="text-gray-500">
                      Loading historical data...
                    </div>
                  </div>
                ) : error ? (
                  <div className="flex items-center justify-center h-[400px]">
                    <div className="text-red-500">Error: {error}</div>
                  </div>
                ) : fearGreedHistory?.data &&
                  fearGreedHistory.data.length > 0 ? (
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
                        const date = newKSTDate(value)
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
                                  {newKSTDate(
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
                              {newKSTDate(label).toLocaleDateString('ko-KR', {
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
                        <stop
                          offset="0%"
                          stopColor="#3b82f6"
                          stopOpacity={0.6}
                        />
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
                            const eventDate = newKSTDate(event.date)

                            // Find closest Fear & Greed data point
                            let closestData: any = null
                            let minDiff = Infinity

                            fearGreedHistory.data.forEach((item) => {
                              const itemDate = newKSTDate(item.date)
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
                                filter:
                                  'drop-shadow(0 2px 4px rgba(0,0,0,0.3))',
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
      </div>
    )
  }
)

FearGreedChart.displayName = 'FearGreedChart'

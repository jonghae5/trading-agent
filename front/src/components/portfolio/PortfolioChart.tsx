import React from 'react'
import { motion } from 'framer-motion'
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  ComposedChart,
  Legend
} from 'recharts'
import { TrendingUp, Calendar } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { SimulationDataPoint } from '../../api/portfolio'
import { EconomicEvent } from '../../api/economic'

interface PortfolioChartProps {
  simulation: SimulationDataPoint[]
  economicEvents?: EconomicEvent[]
}

export const PortfolioChart: React.FC<PortfolioChartProps> = ({
  simulation,
  economicEvents = []
}) => {
  // 차트 데이터 준비 - 경제 이벤트 포인트 추가
  const chartData = simulation.map((point) => ({
    ...point,
    date: point.date, // YYYY-MM-DD 형식 그대로 사용
    displayDate: new Date(point.date).toLocaleDateString('ko-KR', {
      year: '2-digit',
      month: 'short'
    }),
    fullDate: point.date,
    portfolioValueFormatted: point.portfolio_value.toLocaleString(),
    cumulativeReturnPercent: point.cumulative_return * 100
  }))

  // 성과 지표 계산

  const totalReturn = simulation[simulation.length - 1]?.cumulative_return * 100

  const maxDrawdown =
    Math.min(...simulation.map((p) => p.cumulative_return)) * 100

  const positiveDays = simulation.filter((p) => p.daily_return > 0).length
  const winRate = (positiveDays / simulation.length) * 100

  // 연간 변동성 계산
  const dailyReturns = simulation.map((p) => p.daily_return)
  const avgReturn =
    dailyReturns.reduce((sum, r) => sum + r, 0) / dailyReturns.length
  const variance =
    dailyReturns.reduce((sum, r) => sum + Math.pow(r - avgReturn, 2), 0) /
    dailyReturns.length
  const annualVolatility = Math.sqrt(variance * 252) * 100

  // 시뮬레이션 기간 내의 경제 이벤트 필터링
  const relevantEvents = economicEvents.filter((event) => {
    const eventDate = new Date(event.date)
    const startDate = new Date(simulation[0]?.date)
    const endDate = new Date(simulation[simulation.length - 1]?.date)
    return eventDate >= startDate && eventDate <= endDate
  })

  // 차트에 표시할 이벤트 (최대 5개, 우선순위 높은 순)
  const displayEvents = relevantEvents
    .sort((a, b) => b.priority - a.priority)
    .slice(0, 5)

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload

      // 경제 이벤트 포인트인 경우
      if (data.isEvent && data.event) {
        const event = data.event
        return (
          <div className="bg-white p-4 border rounded-lg shadow-lg max-w-xs">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xl">{event.icon}</span>
              <div className="font-semibold text-gray-900">{event.title}</div>
            </div>
            <div className="space-y-2 text-sm">
              <div className="text-gray-600 leading-relaxed">
                {event.description}
              </div>
              <div className="flex items-center gap-2 pt-2 border-t">
                <span
                  className={`text-xs px-2 py-1 rounded ${
                    event.severity === 'critical'
                      ? 'bg-red-100 text-red-700'
                      : event.severity === 'high'
                        ? 'bg-orange-100 text-orange-700'
                        : event.severity === 'medium'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-gray-100 text-gray-700'
                  }`}
                >
                  {event.severity === 'critical'
                    ? '매우 중요'
                    : event.severity === 'high'
                      ? '중요'
                      : event.severity === 'medium'
                        ? '보통'
                        : '낮음'}
                </span>
                <span className="text-xs text-gray-500">
                  {new Date(event.detail_date).toLocaleDateString('ko-KR')}
                </span>
              </div>
            </div>
          </div>
        )
      }

      // 일반 포트폴리오 데이터 포인트인 경우
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <div className="font-semibold text-gray-900 mb-2">
            {data.fullDate || data.date}
          </div>
          <div className="space-y-1 text-sm">
            <div className="flex justify-between gap-4">
              <span className="text-gray-600">포트폴리오 가치:</span>
              <span className="font-semibold">
                $
                {data.portfolioValueFormatted ||
                  data.portfolio_value?.toLocaleString()}
              </span>
            </div>
            <div className="flex justify-between gap-4">
              <span className="text-gray-600">누적 수익률:</span>
              <span
                className={`font-semibold ${
                  (data.cumulative_return || 0) >= 0
                    ? 'text-green-600'
                    : 'text-red-600'
                }`}
              >
                {(
                  data.cumulativeReturnPercent ||
                  (data.cumulative_return || 0) * 100
                ).toFixed(2)}
                %
              </span>
            </div>
            {data.daily_return && (
              <div className="flex justify-between gap-4">
                <span className="text-gray-600">일일 수익률:</span>
                <span
                  className={`font-semibold ${
                    data.daily_return >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {(data.daily_return * 100).toFixed(2)}%
                </span>
              </div>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <div className="space-y-6">
      {/* 백테스트 성과 요약 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              백테스트 성과 (최근 1년)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-600">총 수익률</div>
                <div
                  className={`text-lg font-bold ${
                    totalReturn >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {totalReturn >= 0 ? '+' : ''}
                  {totalReturn.toFixed(2)}%
                </div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-600">최대 손실</div>
                <div className="text-lg font-bold text-red-600">
                  {maxDrawdown.toFixed(2)}%
                </div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-600">승률</div>
                <div
                  className={`text-lg font-bold ${
                    winRate >= 50 ? 'text-green-600' : 'text-red-600'
                  }`}
                >
                  {winRate.toFixed(1)}%
                </div>
              </div>
              <div className="text-center p-3 bg-gray-50 rounded-lg">
                <div className="text-sm text-gray-600">연간 변동성</div>
                <div className="text-lg font-bold text-orange-600">
                  {annualVolatility.toFixed(1)}%
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* 누적 수익률 차트 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5" />
              누적 수익률 추이
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" opacity={0.3} />
                  <XAxis
                    dataKey="date"
                    fontSize={12}
                    tick={{ fontSize: 11 }}
                    tickFormatter={(value) => {
                      const date = new Date(value)
                      return date.toLocaleDateString('ko-KR', {
                        year: '2-digit',
                        month: 'short'
                      })
                    }}
                  />
                  <YAxis
                    fontSize={12}
                    tickFormatter={(value) => `${value.toFixed(0)}%`}
                    tick={{ fontSize: 11 }}
                  />
                  <Tooltip content={<CustomTooltip />} />

                  <Legend
                    content={() => {
                      return (
                        <div className="flex flex-wrap items-center justify-center gap-2 mt-2 sm:gap-1 sm:mt-1">
                          <div className="flex items-center gap-1 sm:gap-0.5">
                            <div className="w-3 h-0.5 bg-emerald-500 sm:w-2 sm:h-0.5"></div>
                            <span className="text-xs text-gray-600 sm:text-[10px]">
                              포트폴리오 수익률
                            </span>
                          </div>
                          {displayEvents.map((event, index) => (
                            <div
                              key={`legend-${event.title}-${index}`}
                              className="flex items-center gap-1 sm:gap-0.5"
                            >
                              <div
                                className="w-3 h-0.5 sm:w-2 sm:h-0.5"
                                style={{
                                  backgroundColor: event.color,
                                  borderStyle: 'dashed',
                                  borderWidth: '1px 0',
                                  borderColor: event.color,
                                  height: '2px'
                                }}
                              ></div>
                              <span className="text-xs text-gray-600 sm:text-[10px]">
                                {event.icon} {event.title}
                              </span>
                            </div>
                          ))}
                        </div>
                      )
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="cumulativeReturnPercent"
                    stroke="#10b981"
                    strokeWidth={2}
                    dot={false}
                  />
                  {/* 0% 기준선 */}
                  <Line
                    type="monotone"
                    dataKey={() => 0}
                    stroke="#6b7280"
                    strokeWidth={1}
                    strokeDasharray="5 5"
                    dot={false}
                  />

                  {/* 경제 이벤트 마커 */}
                  {displayEvents.map((event, index) => {
                    const eventDate = new Date(event.date)
                    const chartDateStr = eventDate.toISOString().split('T')[0] // YYYY-MM-DD 형식
                    return (
                      <ReferenceLine
                        key={`${event.title}-${index}`}
                        x={chartDateStr}
                        stroke={event.color}
                        strokeWidth={2}
                        strokeDasharray="8 4"
                      />
                    )
                  })}
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* 성과 해석 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.6 }}
      >
        <Card className="bg-green-50 border-green-200">
          <CardContent className="p-4">
            <h4 className="font-semibold text-green-800 mb-2">
              📊 백테스트 결과 해석
            </h4>
            <div className="text-sm text-green-800 space-y-1">
              <p>
                • <strong>과거 성과:</strong> 이 결과는 과거 데이터 기반이며,
                미래 성과를 보장하지 않습니다
              </p>
              <p>
                • <strong>리스크:</strong> 최대 손실{' '}
                {Math.abs(maxDrawdown).toFixed(1)}%를 경험할 수 있습니다
              </p>
              <p>
                • <strong>변동성:</strong> 연간 {annualVolatility.toFixed(1)}%의
                변동성을 보입니다
              </p>
              <p>
                • <strong>실제 투자 시:</strong> 거래 비용, 세금, 시장 충격 등을
                추가로 고려해야 합니다
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

import React from 'react'
import { motion } from 'framer-motion'
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

interface PortfolioWeightsProps {
  weights: Record<string, number>
  tickers: string[]
}

// 색상 팔레트 (더 많은 색상 추가)
const COLORS = [
  '#3b82f6', // blue
  '#ef4444', // red
  '#10b981', // emerald
  '#f59e0b', // amber
  '#8b5cf6', // violet
  '#06b6d4', // cyan
  '#84cc16', // lime
  '#f97316', // orange
  '#ec4899', // pink
  '#6366f1', // indigo
  '#14b8a6', // teal
  '#eab308', // yellow
  '#a855f7', // purple
  '#059669', // emerald-600
  '#dc2626', // red-600
  '#7c3aed', // violet-600
  '#0891b2', // cyan-600
  '#65a30d', // lime-600
  '#ea580c', // orange-600
  '#be185d' // pink-600
]

export const PortfolioWeights: React.FC<PortfolioWeightsProps> = ({
  weights,
  tickers
}) => {
  // 가중치 데이터 준비
  const chartData = Object.entries(weights)
    .filter(([_, weight]) => weight > 0.001) // 0.1% 이상만 표시
    .map(([ticker, weight], index) => ({
      ticker,
      weight: weight * 100,
      value: weight,
      color: COLORS[index % COLORS.length]
    }))
    .sort((a, b) => b.weight - a.weight) // 가중치 내림차순 정렬

  const formatPercentage = (value: number) => `${value.toFixed(1)}%`

  const formatCurrency = (value: number, total: number = 100000) => {
    const amount = value * total
    if (amount >= 1000000) {
      return `$${(amount / 1000000).toFixed(1)}M`
    } else if (amount >= 1000) {
      return `$${(amount / 1000).toFixed(1)}K`
    } else {
      return `$${amount.toFixed(0)}`
    }
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border rounded-lg shadow-lg">
          <div className="font-semibold text-gray-900">{data.ticker}</div>
          <div className="text-sm text-gray-600">
            비중: {formatPercentage(data.weight)}
          </div>
          <div className="text-sm text-gray-600">
            투자금액: {formatCurrency(data.value)} (총 $10K 기준)
          </div>
        </div>
      )
    }
    return null
  }

  const CustomLabel = ({
    cx,
    cy,
    midAngle,
    innerRadius,
    outerRadius,
    percent
  }: any) => {
    if (percent < 0.05) return null // 5% 미만은 라벨 숨김

    const RADIAN = Math.PI / 180
    const radius = innerRadius + (outerRadius - innerRadius) * 0.5
    const x = cx + radius * Math.cos(-midAngle * RADIAN)
    const y = cy + radius * Math.sin(-midAngle * RADIAN)

    return (
      <text
        x={x}
        y={y}
        fill="white"
        textAnchor={x > cx ? 'start' : 'end'}
        dominantBaseline="central"
        fontSize="12"
        fontWeight="bold"
      >
        {`${(percent * 100).toFixed(0)}%`}
      </text>
    )
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="h-5 w-5" />
            포트폴리오 구성
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* 파이 차트 */}
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={chartData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={CustomLabel}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {chartData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip content={<CustomTooltip />} />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* 상세 정보 */}
            <div className="space-y-3">
              <h4 className="font-semibold text-gray-900 mb-4">
                상세 구성 비중
              </h4>
              <div className="max-h-64 overflow-y-auto space-y-2">
                {chartData.map((item, index) => (
                  <motion.div
                    key={item.ticker}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className="w-4 h-4 rounded-full"
                        style={{ backgroundColor: item.color }}
                      />
                      <div>
                        <div className="font-medium text-gray-900">
                          {item.ticker}
                        </div>
                        <div className="text-sm text-gray-500">
                          {formatCurrency(item.value)}
                        </div>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-semibold text-gray-900">
                        {formatPercentage(item.weight)}
                      </div>
                    </div>
                  </motion.div>
                ))}
              </div>

              {/* 요약 정보 */}
              <div className="mt-6 pt-4 border-t border-gray-200">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-600">총 종목 수:</span>
                    <span className="font-semibold ml-2">
                      {chartData.length}개
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">최대 비중:</span>
                    <span className="font-semibold ml-2">
                      {chartData.length > 0
                        ? formatPercentage(chartData[0].weight)
                        : '0%'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">최소 비중:</span>
                    <span className="font-semibold ml-2">
                      {chartData.length > 0
                        ? formatPercentage(
                            chartData[chartData.length - 1].weight
                          )
                        : '0%'}
                    </span>
                  </div>
                  <div>
                    <span className="text-gray-600">투자 스타일:</span>
                    <span className="font-semibold ml-2">
                      {chartData.length <= 2
                        ? '초집중형'
                        : chartData.length <= 4
                          ? '집중형'
                          : chartData.length <= 6
                            ? '균형형'
                            : '분산형'}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 투자 가이드 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <h4 className="font-semibold text-blue-800 mb-2">
              🏛️ 월가 공격적 투자 전략
            </h4>
            <div className="text-sm text-blue-800 space-y-1">
              <p>
                • <strong>집중투자:</strong> 2개 종목 시 각 50%, 3개 종목 시
                최대 35%로 공격적 집중
              </p>
              <p>
                • <strong>리스크-리턴:</strong> 높은 집중도를 통해 초과수익 추구
              </p>
              <p>
                • <strong>포지션 사이징:</strong> 확신 있는 종목에 대한 대형
                포지션
              </p>
              <p>
                • <strong>모니터링:</strong> 집중투자 시 개별 종목 리스크를
                면밀히 관찰 필요
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

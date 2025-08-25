import React from 'react'
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { BarChart3 } from 'lucide-react'
import { EarningSurprise } from '../../api/stocks'

interface EarningSurprisesChartProps {
  data: EarningSurprise[]
  symbol: string
}

const EarningSurprisesChart: React.FC<EarningSurprisesChartProps> = ({
  data,
  symbol
}) => {
  const chartData = data
    .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())
    .map((item) => ({
      ...item,
      period: `Q${item.quarter} ${item.year}`,
      surprisePercent: Math.round(item.surprisePercent * 100) / 100
    }))

  const formatTooltip = (value: number, name: string) => {
    const labelMap: Record<string, string> = {
      actual: 'Actual EPS',
      estimate: 'Estimated EPS',
      surprisePercent: 'Surprise %'
    }

    if (name === 'surprisePercent') {
      return [`${value}%`, labelMap[name] || name]
    }
    return [`$${value}`, labelMap[name] || name]
  }

  const getSurpriseColor = (value: number) => {
    return value >= 0 ? '#16a34a' : '#dc2626'
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="size-5 text-blue-600" />
          실적 서프라이즈 - {symbol}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart
              data={chartData}
              margin={{ top: 20, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" />
              <YAxis yAxisId="eps" orientation="left" />
              <YAxis yAxisId="surprise" orientation="right" />
              <Tooltip formatter={formatTooltip} />
              <Legend />
              <Bar
                yAxisId="eps"
                dataKey="estimate"
                fill="#94a3b8"
                name="Estimated EPS"
                opacity={0.8}
              />
              <Bar
                yAxisId="eps"
                dataKey="actual"
                fill="#3b82f6"
                name="Actual EPS"
              />
              <Line
                yAxisId="surprise"
                type="monotone"
                dataKey="surprisePercent"
                stroke="#f59e0b"
                strokeWidth={3}
                name="Surprise %"
                dot={{ fill: '#f59e0b', strokeWidth: 2, r: 4 }}
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
          <div className="text-center">
            <div className="w-4 h-4 bg-slate-400 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Estimated EPS</span>
          </div>
          <div className="text-center">
            <div className="w-4 h-4 bg-blue-500 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Actual EPS</span>
          </div>
          <div className="text-center">
            <div className="w-4 h-4 bg-amber-500 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Surprise %</span>
          </div>
        </div>

        {chartData.length > 0 && (
          <div className="mt-4 p-3 bg-gray-50 rounded-lg">
            <h4 className="font-semibold text-sm mb-2">최근 실적 요약</h4>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-600">최근 분기: </span>
                <span className="font-medium">
                  {chartData[chartData.length - 1]?.period}
                </span>
              </div>
              <div>
                <span className="text-gray-600">서프라이즈: </span>
                <span
                  className={`font-medium ${
                    (chartData[chartData.length - 1]?.surprisePercent || 0) >= 0
                      ? 'text-green-600'
                      : 'text-red-600'
                  }`}
                >
                  {chartData[chartData.length - 1]?.surprisePercent}%
                </span>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export default EarningSurprisesChart

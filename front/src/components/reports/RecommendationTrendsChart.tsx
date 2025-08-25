import React from 'react'
import {
  ComposedChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { TrendingUp } from 'lucide-react'
import { RecommendationTrend } from '../../api/stocks'

interface RecommendationTrendsChartProps {
  data: RecommendationTrend[]
  symbol: string
}

const RecommendationTrendsChart: React.FC<RecommendationTrendsChartProps> = ({
  data,
  symbol
}) => {
  const chartData = data
    .sort((a, b) => new Date(a.period).getTime() - new Date(b.period).getTime())
    .map((item) => ({
      ...item,
      period: new Date(item.period).toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'short'
      }),
      total: item.strongBuy + item.buy + item.hold + item.sell + item.strongSell
    }))

  const formatTooltip = (value: number, name: string) => {
    const labelMap: Record<string, string> = {
      strongBuy: 'Strong Buy',
      buy: 'Buy',
      hold: 'Hold',
      sell: 'Sell',
      strongSell: 'Strong Sell'
    }
    return [`${value}개`, labelMap[name] || name]
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="size-5 text-green-600" />
          분석가 추천 트렌드 - {symbol}
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
              <YAxis />
              <Tooltip formatter={formatTooltip} />
              <Legend />
              <Bar
                dataKey="strongBuy"
                stackId="a"
                fill="#16a34a"
                name="Strong Buy"
              />
              <Bar dataKey="buy" stackId="a" fill="#22c55e" name="Buy" />
              <Bar dataKey="hold" stackId="a" fill="#eab308" name="Hold" />
              <Bar dataKey="sell" stackId="a" fill="#f97316" name="Sell" />
              <Bar
                dataKey="strongSell"
                stackId="a"
                fill="#dc2626"
                name="Strong Sell"
              />
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        <div className="mt-4 grid grid-cols-5 gap-2 text-sm">
          <div className="text-center">
            <div className="w-4 h-4 bg-green-600 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Strong Buy</span>
          </div>
          <div className="text-center">
            <div className="w-4 h-4 bg-green-500 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Buy</span>
          </div>
          <div className="text-center">
            <div className="w-4 h-4 bg-yellow-500 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Hold</span>
          </div>
          <div className="text-center">
            <div className="w-4 h-4 bg-orange-500 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Sell</span>
          </div>
          <div className="text-center">
            <div className="w-4 h-4 bg-red-600 mx-auto mb-1 rounded"></div>
            <span className="text-gray-600">Strong Sell</span>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

export default RecommendationTrendsChart

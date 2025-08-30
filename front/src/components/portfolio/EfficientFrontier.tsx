import React from 'react'
import { TrendingUp, Target, Zap } from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../ui/card'
import {
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Scatter,
  ReferenceLine,
  Legend,
  ComposedChart
} from 'recharts'

interface EfficientFrontierPoint {
  expected_return: number
  volatility: number
  sharpe_ratio: number
}

interface IndividualAsset {
  ticker: string
  expected_return: number
  volatility: number
}

interface EfficientFrontierData {
  frontier_points: EfficientFrontierPoint[]
  max_sharpe_point: EfficientFrontierPoint | null
  individual_assets: IndividualAsset[]
  risk_free_rate: number
}

interface EfficientFrontierProps {
  efficientFrontier: EfficientFrontierData
  currentPortfolio: {
    expected_return: number
    volatility: number
  }
}

export const EfficientFrontier: React.FC<EfficientFrontierProps> = ({
  efficientFrontier,
  currentPortfolio
}) => {
  // 차트 데이터 준비
  const chartData = efficientFrontier.frontier_points.map((point) => ({
    volatility: point.volatility * 100, // 퍼센트로 변환
    expected_return: point.expected_return * 100, // 퍼센트로 변환
    sharpe_ratio: point.sharpe_ratio,
    type: 'frontier'
  }))

  // 개별 자산 데이터
  const assetsData = efficientFrontier.individual_assets.map((asset) => ({
    volatility: asset.volatility * 100,
    expected_return: asset.expected_return * 100,
    ticker: asset.ticker,
    type: 'asset'
  }))

  // Max Sharpe 포인트
  const maxSharpeData = efficientFrontier.max_sharpe_point
    ? [
        {
          volatility: efficientFrontier.max_sharpe_point.volatility * 100,
          expected_return:
            efficientFrontier.max_sharpe_point.expected_return * 100,
          sharpe_ratio: efficientFrontier.max_sharpe_point.sharpe_ratio,
          type: 'max_sharpe'
        }
      ]
    : []

  // 현재 포트폴리오 데이터
  const currentPortfolioData = [
    {
      volatility: currentPortfolio.volatility * 100,
      expected_return: currentPortfolio.expected_return * 100,
      type: 'current'
    }
  ]

  // CAL (Capital Allocation Line) 데이터 계산
  const calData = efficientFrontier.max_sharpe_point
    ? [
        {
          volatility: 0,
          expected_return: efficientFrontier.risk_free_rate * 100
        },
        {
          volatility: efficientFrontier.max_sharpe_point.volatility * 100,
          expected_return:
            efficientFrontier.max_sharpe_point.expected_return * 100
        },
        {
          volatility: efficientFrontier.max_sharpe_point.volatility * 200,
          expected_return:
            efficientFrontier.max_sharpe_point.expected_return * 200 -
            efficientFrontier.risk_free_rate * 100
        }
      ]
    : []

  // 커스텀 툴팁
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white/95 p-2 border border-gray-200 rounded-lg shadow-xl backdrop-blur-sm">
          <div className="space-y-2">
            <p className="font-semibold text-gray-800 border-b border-gray-100 pb-1">
              {data.ticker
                ? `${data.ticker}`
                : data.type === 'max_sharpe'
                  ? '최적 포트폴리오'
                  : data.type === 'current'
                    ? '현재 포트폴리오'
                    : '효율적 프론티어'}
            </p>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <span className="text-gray-500">변동성</span>
                <p className="font-medium text-orange-600">
                  {label?.toFixed(2)}%
                </p>
              </div>
              <div>
                <span className="text-gray-500">기대수익률</span>
                <p className="font-medium text-blue-600">
                  {data.expected_return?.toFixed(2)}%
                </p>
              </div>
            </div>
            {data.sharpe_ratio && (
              <div className="pt-1 border-t border-gray-100">
                <span className="text-gray-500 text-xs">샤프 비율</span>
                <p className="font-semibold text-green-600">
                  {data.sharpe_ratio?.toFixed(2)}
                </p>
              </div>
            )}
          </div>
        </div>
      )
    }
    return null
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="size-5" />
          효율적 프론티어 (Efficient Frontier)
        </CardTitle>
        <CardDescription>
          위험-수익률 관계를 시각화하여 최적의 포트폴리오를 찾아보세요
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 차트 */}
        <div className="h-[500px] bg-gradient-to-br from-gray-50 to-blue-50 p-4 rounded-xl">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart margin={{ top: 5, right: 5, left: 5, bottom: 5 }}>
              <defs>
                <linearGradient
                  id="frontierGradient"
                  x1="0"
                  y1="0"
                  x2="1"
                  y2="0"
                >
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.8} />
                  <stop offset="100%" stopColor="#1d4ed8" stopOpacity={1} />
                </linearGradient>
                <filter id="glow">
                  <feGaussianBlur stdDeviation="3" result="coloredBlur" />
                  <feMerge>
                    <feMergeNode in="coloredBlur" />
                    <feMergeNode in="SourceGraphic" />
                  </feMerge>
                </filter>
              </defs>

              <CartesianGrid
                strokeDasharray="2 2"
                stroke="#e2e8f0"
                strokeOpacity={0.6}
              />

              <XAxis
                dataKey="volatility"
                type="number"
                scale="linear"
                domain={['dataMin - 2', 'dataMax + 2']}
                label={{
                  value: '연간 변동성 (%)',
                  position: 'insideBottom',
                  offset: -10,
                  style: {
                    textAnchor: 'middle',
                    fontSize: '12px',
                    fill: '#64748b'
                  }
                }}
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(value) => `${value.toFixed(1)}%`}
              />

              <YAxis
                dataKey="expected_return"
                type="number"
                scale="linear"
                domain={['dataMin - 2', 'dataMax + 2']}
                label={{
                  value: '기대 수익률 (%)',
                  angle: -90,
                  position: 'insideLeft',
                  style: {
                    textAnchor: 'middle',
                    fontSize: '12px',
                    fill: '#64748b'
                  }
                }}
                tick={{ fontSize: 11, fill: '#64748b' }}
                tickFormatter={(value) => `${value.toFixed(1)}%`}
              />

              <Tooltip
                content={<CustomTooltip />}
                cursor={{
                  stroke: '#94a3b8',
                  strokeWidth: 2,
                  strokeDasharray: '4 4'
                }}
                wrapperStyle={{ outline: 'none' }}
              />

              <Legend
                wrapperStyle={{
                  paddingTop: '20px',
                  fontSize: '10px'
                }}
                iconType="line"
              />

              {/* 무위험 수익률 선 */}
              <ReferenceLine
                y={efficientFrontier.risk_free_rate * 100}
                stroke="#94a3b8"
                strokeDasharray="4 4"
                strokeWidth={2}
                label={{
                  value: `무위험수익률 (${(
                    efficientFrontier.risk_free_rate * 100
                  ).toFixed(1)}%)`,
                  position: 'insideTopLeft',
                  offset: 10,
                  style: {
                    fontSize: '11px',
                    fill: '#475569',
                    fontWeight: '500',
                    textAnchor: 'start'
                  }
                }}
              />

              {/* CAL (Capital Allocation Line) */}
              {calData.length > 0 && (
                <Line
                  dataKey="expected_return"
                  data={calData}
                  stroke="#06b6d4"
                  strokeWidth={3}
                  strokeDasharray="6 4"
                  dot={false}
                  activeDot={false}
                  connectNulls={false}
                  name="자본배분선 (CAL)"
                  filter="url(#glow)"
                />
              )}

              {/* Efficient Frontier */}
              <Line
                dataKey="expected_return"
                data={chartData}
                stroke="#3b82f6"
                strokeWidth={4}
                dot={false}
                activeDot={false}
                connectNulls={false}
                name="효율적 프론티어"
                filter="url(#glow)"
              />

              <Scatter
                dataKey="expected_return"
                data={currentPortfolioData}
                fill="#8b5cf6"
                shape={(props) => (
                  <svg
                    x={props.cx - 8}
                    y={props.cy - 8}
                    width={16}
                    height={16}
                    viewBox="0 0 16 16"
                  >
                    <polygon
                      points="8,1 15,8 8,15 1,8"
                      fill="#8b5cf6"
                      stroke="#6d28d9"
                      strokeWidth="1"
                    />
                  </svg>
                )}
                name="현재 포트폴리오"
                z={10}
              />

              {/* 개별 자산들 - 먼저 렌더링 */}
              <Scatter
                dataKey="expected_return"
                data={assetsData}
                shape={(props) => (
                  <>
                    <circle
                      cx={props.cx}
                      cy={props.cy}
                      r={4}
                      fill="#10b981"
                      stroke="#047857"
                      strokeWidth={1}
                    />
                    <text
                      x={props.cx}
                      y={props.cy + 20}
                      textAnchor="middle"
                      fontSize="10"
                      fill="#047857"
                      fontWeight="bold"
                    >
                      {props.payload?.ticker}
                    </text>
                  </>
                )}
                fill="#10b981"
                name="개별 자산"
                z={1}
              />

              {/* Max Sharpe 포인트 - 가장 마지막에 렌더링해서 맨 위에 표시 */}
              {maxSharpeData.length > 0 && (
                <Scatter
                  dataKey="expected_return"
                  data={maxSharpeData}
                  fill="#ef4444"
                  // shape="star" // 지원 안됨
                  shape={(props) => (
                    <svg
                      x={props.cx - 8}
                      y={props.cy - 8}
                      width={16}
                      height={16}
                      viewBox="0 0 16 16"
                    >
                      <polygon
                        points="8,1 10,6 15,6 11,9 12,15 8,12 4,15 5,9 1,6 6,6"
                        fill="#ef4444"
                        stroke="#b91c1c"
                        strokeWidth="1"
                      />
                    </svg>
                  )}
                  name="최적 포트폴리오"
                  z={3}
                />
              )}
            </ComposedChart>
          </ResponsiveContainer>
        </div>

        {/* 범례 및 설명 */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-4 h-1 bg-blue-500"></div>
              <span className="font-medium text-blue-800">효율적 프론티어</span>
            </div>
            <p className="text-sm text-blue-700">
              동일한 위험 수준에서 최대 수익률을 제공하는 포트폴리오들의 집합
            </p>
          </div>

          <div className="bg-red-50 p-3 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Target className="size-4 text-red-600" />
              <span className="font-medium text-red-800">최적 포트폴리오</span>
            </div>
            <p className="text-sm text-red-700">
              샤프 비율이 최대인 포트폴리오 (위험 대비 수익률 최적화)
            </p>
          </div>

          <div className="bg-purple-50 p-3 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="size-4 text-purple-600" />
              <span className="font-medium text-purple-800">
                현재 포트폴리오
              </span>
            </div>
            <p className="text-sm text-purple-700">
              선택한 최적화 방법으로 구성된 현재 포트폴리오
            </p>
          </div>
        </div>

        {/* 추가 정보 */}
        <div className="bg-gray-50 p-4 rounded-lg">
          <h5 className="font-medium mb-2 flex items-center gap-2">
            📈 효율적 프론티어 분석
          </h5>
          <div className="text-sm space-y-1">
            <p>
              • <strong>효율적 프론티어</strong>: 각 위험 수준에서 달성 가능한
              최대 수익률을 나타내는 곡선
            </p>
            <p>
              • <strong>자본배분선(CAL)</strong>: 무위험자산과 최적 위험자산을
              조합한 투자선
            </p>
            <p>
              • <strong>개별 자산</strong>: 각 종목의 위험-수익률 위치 (녹색 점)
            </p>
            <p>
              • 효율적 프론티어 위의 포트폴리오는 동일한 위험에서 더 높은
              수익률을 제공합니다
            </p>
            {efficientFrontier.max_sharpe_point && (
              <p>
                • 최적 포트폴리오 샤프 비율:{' '}
                <strong>
                  {efficientFrontier.max_sharpe_point.sharpe_ratio.toFixed(2)}
                </strong>
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

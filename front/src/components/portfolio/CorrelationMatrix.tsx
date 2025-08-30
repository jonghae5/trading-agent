import React from 'react'
import { motion } from 'framer-motion'
import { BarChart3, TrendingUp, TrendingDown } from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card'

interface CorrelationMatrixProps {
  correlationMatrix: Record<string, Record<string, number>>
  tickers: string[]
}

export const CorrelationMatrix: React.FC<CorrelationMatrixProps> = ({
  correlationMatrix,
  tickers
}) => {
  // 상관계수에 따른 색상 반환
  const getCorrelationColor = (correlation: number) => {
    if (correlation >= 0.7) return 'bg-red-500'
    if (correlation >= 0.3) return 'bg-orange-400'
    if (correlation >= 0.1) return 'bg-yellow-400'
    if (correlation >= -0.1) return 'bg-gray-300'
    if (correlation >= -0.3) return 'bg-blue-400'
    if (correlation >= -0.7) return 'bg-blue-500'
    return 'bg-blue-600'
  }

  // 상관계수에 따른 텍스트 색상 반환
  const getTextColor = (correlation: number) => {
    return Math.abs(correlation) > 0.5 ? 'text-white' : 'text-gray-800'
  }

  // 상관계수 해석 텍스트
  const getCorrelationInterpretation = (correlation: number) => {
    if (correlation >= 0.7) return '매우 강한 양의 상관관계'
    if (correlation >= 0.3) return '강한 양의 상관관계'
    if (correlation >= 0.1) return '약한 양의 상관관계'
    if (correlation >= -0.1) return '상관관계 없음'
    if (correlation >= -0.3) return '약한 음의 상관관계'
    if (correlation >= -0.7) return '강한 음의 상관관계'
    return '매우 강한 음의 상관관계'
  }

  // 상관관계 통계 계산
  const getCorrelationStats = () => {
    const correlations: number[] = []
    
    for (let i = 0; i < tickers.length; i++) {
      for (let j = i + 1; j < tickers.length; j++) {
        const correlation = correlationMatrix[tickers[i]]?.[tickers[j]]
        if (correlation !== undefined) {
          correlations.push(correlation)
        }
      }
    }

    const avgCorrelation = correlations.reduce((sum, corr) => sum + corr, 0) / correlations.length
    const maxCorrelation = Math.max(...correlations)
    const minCorrelation = Math.min(...correlations)

    return {
      average: avgCorrelation,
      maximum: maxCorrelation,
      minimum: minCorrelation,
      count: correlations.length
    }
  }

  const stats = getCorrelationStats()

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <BarChart3 className="size-5" />
          자산 간 상관관계 분석
        </CardTitle>
        <CardDescription>
          포트폴리오 내 자산들의 상관관계를 통해 분산투자 효과를 확인하세요
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* 상관관계 통계 */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 p-3 rounded-lg">
            <div className="text-sm text-blue-600">평균 상관계수</div>
            <div className="text-lg font-semibold text-blue-800">
              {stats.average.toFixed(3)}
            </div>
          </div>
          <div className="bg-green-50 p-3 rounded-lg">
            <div className="text-sm text-green-600">최고 상관계수</div>
            <div className="text-lg font-semibold text-green-800 flex items-center gap-1">
              <TrendingUp className="size-4" />
              {stats.maximum.toFixed(3)}
            </div>
          </div>
          <div className="bg-red-50 p-3 rounded-lg">
            <div className="text-sm text-red-600">최저 상관계수</div>
            <div className="text-lg font-semibold text-red-800 flex items-center gap-1">
              <TrendingDown className="size-4" />
              {stats.minimum.toFixed(3)}
            </div>
          </div>
          <div className="bg-gray-50 p-3 rounded-lg">
            <div className="text-sm text-gray-600">상관관계 쌍</div>
            <div className="text-lg font-semibold text-gray-800">
              {stats.count}개
            </div>
          </div>
        </div>

        {/* 상관관계 매트릭스 */}
        <div className="overflow-auto">
          <div className="inline-block min-w-full">
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="p-2 text-left font-medium text-gray-600 border-b">종목</th>
                  {tickers.map((ticker) => (
                    <th key={ticker} className="p-2 text-center font-medium text-gray-600 border-b min-w-16">
                      {ticker}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tickers.map((rowTicker, i) => (
                  <motion.tr
                    key={rowTicker}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.05 }}
                  >
                    <td className="p-2 font-medium text-gray-800 border-r">
                      {rowTicker}
                    </td>
                    {tickers.map((colTicker) => {
                      const correlation = correlationMatrix[rowTicker]?.[colTicker] ?? 0
                      const isDiagonal = rowTicker === colTicker
                      
                      return (
                        <td key={colTicker} className="p-1">
                          <div
                            className={`
                              h-10 w-full flex items-center justify-center rounded text-xs font-medium
                              ${isDiagonal ? 'bg-gray-800 text-white' : getCorrelationColor(correlation)}
                              ${isDiagonal ? '' : getTextColor(correlation)}
                            `}
                            title={`${rowTicker} vs ${colTicker}: ${correlation.toFixed(3)} (${getCorrelationInterpretation(correlation)})`}
                          >
                            {correlation.toFixed(2)}
                          </div>
                        </td>
                      )
                    })}
                  </motion.tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 상관관계 범례 */}
        <div className="space-y-3">
          <h5 className="font-medium">상관계수 해석 가이드</h5>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-red-500 rounded"></div>
              <span>0.7+ 매우 강한 양의 상관</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-orange-400 rounded"></div>
              <span>0.3~0.7 강한 양의 상관</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-yellow-400 rounded"></div>
              <span>0.1~0.3 약한 양의 상관</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gray-300 rounded"></div>
              <span>-0.1~0.1 상관없음</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-400 rounded"></div>
              <span>-0.3~-0.1 약한 음의 상관</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span>-0.7~-0.3 강한 음의 상관</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-blue-600 rounded"></div>
              <span>-0.7 미만 매우 강한 음의 상관</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-4 h-4 bg-gray-800 rounded"></div>
              <span>1.0 자기 자신</span>
            </div>
          </div>
        </div>

        {/* 분석 인사이트 */}
        <div className="bg-blue-50 p-4 rounded-lg">
          <h5 className="font-medium mb-2 text-blue-800">📊 분산투자 분석</h5>
          <div className="text-sm text-blue-700 space-y-1">
            <p>
              • 평균 상관계수: <strong>{stats.average.toFixed(3)}</strong> 
              {stats.average < 0.3 ? ' (우수한 분산효과)' : 
               stats.average < 0.6 ? ' (적절한 분산효과)' : 
               ' (분산효과 제한적)'}
            </p>
            <p>
              • 상관관계가 낮을수록 포트폴리오의 전체 위험이 감소합니다
            </p>
            <p>
              • 음의 상관관계를 갖는 자산들은 서로 반대 방향으로 움직여 위험을 상쇄합니다
            </p>
            {stats.maximum > 0.8 && (
              <p className="text-orange-600">
                ⚠️ 일부 자산 간 매우 높은 상관관계로 인해 분산효과가 제한될 수 있습니다
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
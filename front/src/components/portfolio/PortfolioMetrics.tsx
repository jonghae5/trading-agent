import React from 'react'
import { motion } from 'framer-motion'
import { TrendingUp, TrendingDown, Activity, Target } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'
import { OptimizationResult } from '../../api/portfolio'

interface PortfolioMetricsProps {
  optimization: OptimizationResult
}

export const PortfolioMetrics: React.FC<PortfolioMetricsProps> = ({
  optimization
}) => {
  const metrics = [
    {
      title: '기대 연간 수익률',
      value: (optimization.expected_annual_return * 100).toFixed(2) + '%',
      icon: TrendingUp,
      color:
        optimization.expected_annual_return > 0
          ? 'text-green-600'
          : 'text-red-600',
      bgColor:
        optimization.expected_annual_return > 0 ? 'bg-green-50' : 'bg-red-50',
      description: '포트폴리오의 예상 연간 수익률'
    },
    {
      title: '연간 변동성',
      value: (optimization.annual_volatility * 100).toFixed(2) + '%',
      icon: Activity,
      color: 'text-orange-600',
      bgColor: 'bg-orange-50',
      description: '포트폴리오의 위험도 (표준편차)'
    },
    {
      title: '샤프 비율',
      value: optimization.sharpe_ratio.toFixed(3),
      icon: Target,
      color:
        optimization.sharpe_ratio > 1
          ? 'text-green-600'
          : optimization.sharpe_ratio > 0.5
            ? 'text-yellow-600'
            : 'text-red-600',
      bgColor:
        optimization.sharpe_ratio > 1
          ? 'bg-green-50'
          : optimization.sharpe_ratio > 0.5
            ? 'bg-yellow-50'
            : 'bg-red-50',
      description: '위험 조정 수익률 (높을수록 좋음)'
    }
  ]

  const getPerformanceMessage = () => {
    const sharpe = optimization.sharpe_ratio
    const expectedReturn = optimization.expected_annual_return

    if (sharpe > 1.5 && expectedReturn > 0.1) {
      return {
        message: '우수',
        color: 'text-green-700',
        emoji: '🎯'
      }
    } else if (sharpe > 1.0 && expectedReturn > 0.05) {
      return {
        message: '양호',
        color: 'text-blue-700',
        emoji: '👍'
      }
    } else if (sharpe > 0.5) {
      return {
        message: '보통',
        color: 'text-yellow-700',
        emoji: '⚖️'
      }
    } else {
      return { message: '개선 필요', color: 'text-red-700', emoji: '⚠️' }
    }
  }

  const performance = getPerformanceMessage()

  return (
    <div>
      <div className="space-y-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-2">
            {/* 성과 평가 */}
            <Card>
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <p className="text-xs md:text-sm font-medium text-gray-600">
                      성과 평가
                    </p>
                    <p
                      className={`text-lg md:text-2xl font-bold mt-2 ${performance.color}`}
                    >
                      {performance.message}
                    </p>
                    <p className="text-[10px] md:text-xs text-gray-500 mt-1">
                      {optimization.sharpe_ratio > 1.0
                        ? '위험 대비 수익률이 우수합니다.'
                        : optimization.sharpe_ratio > 0.5
                          ? '적절한 수준의 위험 대비 수익률입니다.'
                          : '위험 대비 수익률이 낮습니다. 포트폴리오 구성을 재검토해보세요.'}
                    </p>
                  </div>
                  <div className="p-3 rounded-full bg-gray-100">
                    <span
                      className={`text-xl md:text-2xl ${performance.color}`}
                    >
                      {performance.emoji}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* 핵심 지표 */}
            {metrics.map((metric) => (
              <Card key={metric.title}>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-xs md:text-sm font-medium text-gray-600">
                        {metric.title}
                      </p>
                      <p
                        className={`text-lg md:text-2xl font-bold mt-2 ${metric.color}`}
                      >
                        {metric.value}
                      </p>
                      <p className="text-[10px] md:text-xs text-gray-500 mt-1">
                        {metric.description}
                      </p>
                    </div>
                    <div className={`p-3 rounded-full ${metric.bgColor}`}>
                      <metric.icon className={`h-4 w-4 ${metric.color}`} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </motion.div>
      </div>

      {/* 추가 설명 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
      >
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="p-4">
            <h4 className="font-semibold text-blue-800 mb-2">
              💡 지표 해석 가이드
            </h4>
            <div className="text-sm text-blue-800 space-y-1">
              <p>
                <strong>샤프 비율:</strong> 1.0 이상이면 우수, 0.5~1.0이면 양호,
                0.5 미만이면 개선 필요
              </p>
              <p>
                <strong>변동성:</strong> 낮을수록 안정적이나, 수익률도 함께
                고려해야 함
              </p>
              <p>
                <strong>기대 수익률:</strong> 과거 데이터 기반 예측이므로 실제
                수익률과 다를 수 있음
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

import React from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  Activity,
  Target,
  Shield,
  AlertTriangle,
  Zap
} from 'lucide-react'
import { Card, CardContent } from '../ui/card'
import { OptimizationResult } from '../../api/portfolio'

interface PortfolioMetricsProps {
  optimization: OptimizationResult
}

export const PortfolioMetrics: React.FC<PortfolioMetricsProps> = ({
  optimization
}) => {
  // 기본 지표
  const basicMetrics = [
    {
      title: '연복리 수익률',
      value: (optimization.expected_annual_return * 100).toFixed(2) + '%',
      icon: TrendingUp,
      color:
        optimization.expected_annual_return > 0
          ? 'text-green-600'
          : 'text-red-600',
      bgColor:
        optimization.expected_annual_return > 0 ? 'bg-green-50' : 'bg-red-50',
      description: '예상 연간 복리 수익률 (하루 단위 연환산)'
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

  // 고급 리스크 지표 (개인투자자 특화)
  const advancedMetrics = [
    ...(optimization.sortino_ratio
      ? [
          {
            title: 'Sortino 비율',
            value: optimization.sortino_ratio.toFixed(3),
            icon: Shield,
            color:
              optimization.sortino_ratio > 1.5
                ? 'text-green-600'
                : optimization.sortino_ratio > 1.0
                  ? 'text-blue-600'
                  : 'text-yellow-600',
            bgColor:
              optimization.sortino_ratio > 1.5
                ? 'bg-green-50'
                : optimization.sortino_ratio > 1.0
                  ? 'bg-blue-50'
                  : 'bg-yellow-50',
            description: '하락 위험만 반영, 1↑ 양호'
          }
        ]
      : []),

    ...(optimization.max_drawdown
      ? [
          {
            title: '최대 낙폭',
            value: (optimization.max_drawdown * 100).toFixed(2) + '%',
            icon: AlertTriangle,
            color:
              Math.abs(optimization.max_drawdown) > 0.2
                ? 'text-red-600'
                : Math.abs(optimization.max_drawdown) > 0.1
                  ? 'text-orange-600'
                  : 'text-green-600',
            bgColor:
              Math.abs(optimization.max_drawdown) > 0.2
                ? 'bg-red-50'
                : Math.abs(optimization.max_drawdown) > 0.1
                  ? 'bg-orange-50'
                  : 'bg-green-50',
            description: '최대 낙폭, ↓ 양호'
          }
        ]
      : []),

    ...(optimization.calmar_ratio
      ? [
          {
            title: 'Calmar 비율',
            value: optimization.calmar_ratio.toFixed(3),
            icon: Zap,
            color:
              optimization.calmar_ratio > 1.0
                ? 'text-green-600'
                : optimization.calmar_ratio > 0.5
                  ? 'text-blue-600'
                  : 'text-orange-600',
            bgColor:
              optimization.calmar_ratio > 1.0
                ? 'bg-green-50'
                : optimization.calmar_ratio > 0.5
                  ? 'bg-blue-50'
                  : 'bg-orange-50',
            description: '수익률 대비 낙폭 비율, 1↑ 양호'
          }
        ]
      : [])
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
          {/* 성과 평가 및 기본 지표 */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
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

            {/* 기본 지표 */}
            {basicMetrics.map((metric) => (
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
                      <metric.icon className={`size-4 ${metric.color}`} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* 고급 리스크 지표 (개인투자자 특화) */}
          {advancedMetrics.length > 0 && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                🎯 리스크 지표
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {advancedMetrics.map((metric) => (
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
                          <metric.icon className={`size-4 ${metric.color}`} />
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </div>
          )}

          {/* Walk-Forward Analysis 전용 지표 */}
          {optimization.walkForwardStats && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                🎯 Walk-Forward Analysis 지표
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-full bg-blue-50">
                        <Target className="size-4 text-blue-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600">
                          총 리밸런싱 기간
                        </p>
                        <p className="text-lg font-bold text-blue-600">
                          {optimization.walkForwardStats.totalPeriods}개월
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-full bg-green-50">
                        <TrendingUp className="size-4 text-green-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600">
                          승률
                        </p>
                        <p
                          className={`text-lg font-bold ${
                            optimization.walkForwardStats.winRate >= 0.55
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {(
                            optimization.walkForwardStats.winRate * 100
                          ).toFixed(1)}
                          %
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-full bg-purple-50">
                        <Activity className="size-4 text-purple-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600">
                          평균 샤프 비율
                        </p>
                        <p
                          className={`text-lg font-bold ${
                            optimization.walkForwardStats.avgSharpe >= 1.0
                              ? 'text-green-600'
                              : 'text-orange-600'
                          }`}
                        >
                          {optimization.walkForwardStats.avgSharpe.toFixed(2)}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="p-2 rounded-full bg-orange-50">
                        <Shield className="size-4 text-orange-600" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-600">
                          수익/손실 월수
                        </p>
                        <p className="text-lg font-bold text-gray-600">
                          {optimization.walkForwardStats.positiveReturns}/
                          {optimization.walkForwardStats.negativeReturns}
                        </p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          )}

          {/* 거래비용 & 집중도 정보 */}
          {(optimization.transaction_cost_impact ||
            optimization.concentration_limit) && (
            <div className="mb-4">
              <h3 className="text-lg font-semibold text-gray-800 mb-3">
                ⚙️ 최적화 설정
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-2 gap-4">
                {optimization.transaction_cost_impact && (
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 rounded-full bg-blue-50">
                          <Target className="size-4 text-blue-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-600">
                            거래비용 반영
                          </p>
                          <p className="text-lg font-bold text-blue-600">
                            {optimization.transaction_cost_impact}%
                          </p>
                          <p className="text-xs text-gray-500">리밸런싱 고려</p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                {optimization.concentration_limit && (
                  <Card>
                    <CardContent className="p-4">
                      <div className="flex items-center space-x-3">
                        <div className="p-2 rounded-full bg-purple-50">
                          <Shield className="size-4 text-purple-600" />
                        </div>
                        <div>
                          <p className="text-sm font-medium text-gray-600">
                            집중도 제한
                          </p>
                          <p className="text-lg font-bold text-purple-600">
                            최대 {optimization.concentration_limit}%
                          </p>
                          <p className="text-xs text-gray-500">
                            종목별 최대 한도
                          </p>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          )}
        </motion.div>
      </div>

      {/* Stress Test 결과 */}
      {optimization.stress_scenarios &&
        Object.keys(optimization.stress_scenarios).length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="mb-6"
          >
            <h3 className="text-lg font-semibold text-gray-800 mb-3">
              🔍 위기 시나리오 분석
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(optimization.stress_scenarios).map(
                ([key, scenario]) => (
                  <Card key={key} className="border-orange-200 bg-orange-50">
                    <CardContent className="p-4">
                      <div className="flex items-start space-x-3">
                        <div className="p-2 rounded-full bg-orange-100">
                          <AlertTriangle className="size-4 text-orange-600" />
                        </div>
                        <div className="flex-1">
                          <h4 className="font-medium text-orange-800 text-sm">
                            {scenario.name}
                          </h4>
                          <div className="mt-2 space-y-1">
                            {scenario.portfolio_return && (
                              <p className="text-xs text-orange-700">
                                포트폴리오 수익률:{' '}
                                <span className="font-bold">
                                  {(scenario.portfolio_return * 100).toFixed(2)}
                                  %
                                </span>
                              </p>
                            )}
                            {scenario.max_drawdown && (
                              <p className="text-xs text-orange-700">
                                최대 낙폭:{' '}
                                <span className="font-bold">
                                  {(scenario.max_drawdown * 100).toFixed(2)}%
                                </span>
                              </p>
                            )}
                            {scenario.volatility && (
                              <p className="text-xs text-orange-700">
                                변동성:{' '}
                                <span className="font-bold">
                                  {(scenario.volatility * 100).toFixed(2)}%
                                </span>
                              </p>
                            )}
                            {scenario.worst_day_return && (
                              <p className="text-xs text-orange-700">
                                최악 일일수익률:{' '}
                                <span className="font-bold">
                                  {(scenario.worst_day_return * 100).toFixed(2)}
                                  %
                                </span>
                              </p>
                            )}
                            {scenario.portfolio_impact && (
                              <p className="text-xs text-orange-700">
                                포트폴리오 영향:{' '}
                                <span className="font-bold">
                                  {(scenario.portfolio_impact * 100).toFixed(2)}
                                  %
                                </span>
                              </p>
                            )}
                            {scenario.probability && (
                              <p className="text-xs text-orange-700">
                                발생 확률:{' '}
                                <span className="font-bold">
                                  {scenario.probability}
                                </span>
                              </p>
                            )}
                            {scenario.affected_position && (
                              <p className="text-xs text-orange-700">
                                영향 종목:{' '}
                                <span className="font-bold">
                                  {scenario.affected_position}
                                </span>
                              </p>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )
              )}
            </div>
          </motion.div>
        )}
    </div>
  )
}

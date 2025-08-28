import React, { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  Lightbulb,
  Target,
  Shield
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../ui/card'
import { Button } from '../ui/button'
import { economicApi } from '../../api'
import type {
  EconomicAnalysisRequest,
  EconomicAnalysisResponse
} from '../../api/economic'

interface CategoryInsightsProps {
  category: string
  timeRange: string
  startDate: string
  endDate?: string
  isVisible: boolean
  hasData: boolean
  onRetry?: () => void
}

interface AnalysisState {
  isAnalyzing: boolean
  analysisResult: EconomicAnalysisResponse | null
  analysisError: string | null
  lastAnalyzedParams: string | null
}

export const CategoryInsights: React.FC<CategoryInsightsProps> = ({
  category,
  timeRange,
  startDate,
  endDate,
  isVisible,
  hasData,
  onRetry
}) => {
  const [analysisState, setAnalysisState] = useState<AnalysisState>({
    isAnalyzing: false,
    analysisResult: null,
    analysisError: null,
    lastAnalyzedParams: null
  })

  // 분석 파라미터가 변경되었는지 확인
  const currentParams = `${category}-${timeRange}-${startDate}-${endDate || ''}`

  useEffect(() => {
    const performAnalysis = async () => {
      if (!category || !timeRange || !startDate || !hasData) {
        return
      }

      // 이미 같은 파라미터로 분석 중이거나 완료된 경우 skip
      if (
        currentParams === analysisState.lastAnalyzedParams ||
        analysisState.isAnalyzing
      ) {
        return
      }

      setAnalysisState((prev) => ({
        ...prev,
        isAnalyzing: true,
        analysisResult: null,
        analysisError: null
      }))

      try {
        const request: EconomicAnalysisRequest = {
          category,
          time_range: timeRange,
          start_date: startDate,
          end_date: endDate
        }

        const result = await economicApi.analyzeCategory(request)

        setAnalysisState({
          isAnalyzing: false,
          analysisResult: result,
          analysisError: null,
          lastAnalyzedParams: currentParams
        })
      } catch (error) {
        console.error('Analysis failed:', error)
        setAnalysisState((prev) => ({
          ...prev,
          isAnalyzing: false,
          analysisError:
            error instanceof Error
              ? error.message
              : '분석 중 오류가 발생했습니다.'
        }))
      }
    }

    if (isVisible && hasData) {
      performAnalysis()
    }
  }, [
    category,
    timeRange,
    startDate,
    endDate,
    isVisible,
    hasData,
    currentParams,
    analysisState.lastAnalyzedParams,
    analysisState.isAnalyzing
  ])

  const handleRetry = () => {
    setAnalysisState((prev) => ({
      ...prev,
      lastAnalyzedParams: null,
      analysisError: null
    }))
    onRetry?.()
  }

  const getTrendIcon = (direction: string) => {
    switch (direction.toLowerCase()) {
      case '증가':
      case '상승':
        return <TrendingUp className="size-5 text-green-600" />
      case '감소':
      case '하락':
        return <TrendingDown className="size-5 text-red-600" />
      default:
        return <div className="size-5 bg-gray-400 rounded-full" />
    }
  }

  const getRiskColor = (level: string) => {
    switch (level.toLowerCase()) {
      case '낮음':
        return 'text-green-600 bg-green-50'
      case '보통':
        return 'text-yellow-600 bg-yellow-50'
      case '높음':
        return 'text-orange-600 bg-orange-50'
      case '매우높음':
        return 'text-red-600 bg-red-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-600'
    if (confidence >= 0.6) return 'text-yellow-600'
    return 'text-red-600'
  }

  if (!isVisible) {
    return null
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key="category-insights"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="space-y-6"
      >
        {/* 분석 상태 카드 */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Brain className="size-5 text-purple-600" />
              AI 경제 분석 인사이트
            </CardTitle>
            <CardDescription>
              LLM을 활용한 거시경제 데이터 심층 분석 결과
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!hasData && isVisible && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center py-12"
              >
                <div className="text-center">
                  <RefreshCw className="size-8 animate-spin text-blue-600 mx-auto mb-4" />
                  <p className="text-gray-600">
                    그래프 데이터를 불러오는 중...
                  </p>
                  <p className="text-sm text-gray-500 mt-1">
                    데이터 로딩 완료 후 AI 분석이 시작됩니다
                  </p>
                </div>
              </motion.div>
            )}

            {analysisState.isAnalyzing && hasData && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center justify-center py-12"
              >
                <div className="text-center">
                  <RefreshCw className="size-8 animate-spin text-purple-600 mx-auto mb-4" />
                  <p className="text-gray-600">경제 데이터를 분석하는 중...</p>
                  <p className="text-sm text-gray-500 mt-1">
                    LLM이 트렌드와 리스크를 종합 분석하고 있습니다
                  </p>
                </div>
              </motion.div>
            )}

            {analysisState.analysisError && (
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                className="bg-red-50 border border-red-200 rounded-lg p-4"
              >
                <div className="flex items-center gap-2 text-red-800 mb-2">
                  <AlertTriangle className="size-5" />
                  <span className="font-medium">분석 오류</span>
                </div>
                <p className="text-red-600 mb-3">
                  {analysisState.analysisError}
                </p>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleRetry}
                  className="text-red-600 border-red-200 hover:bg-red-50"
                >
                  <RefreshCw className="size-4 mr-2" />
                  다시 분석
                </Button>
              </motion.div>
            )}

            {analysisState.analysisResult && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="space-y-6"
              >
                {/* 요약 */}
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold text-blue-900 mb-2 flex items-center gap-2">
                    <CheckCircle className="size-5" />
                    종합 요약
                  </h3>
                  <p className="text-blue-800">
                    {analysisState.analysisResult.summary}
                  </p>
                  <div className="mt-2 text-sm text-blue-600">
                    데이터 품질:{' '}
                    {(analysisState.analysisResult.data_quality * 100).toFixed(
                      0
                    )}
                    %
                  </div>
                </div>

                {/* 트렌드 분석 */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        {getTrendIcon(
                          analysisState.analysisResult.trend_analysis.direction
                        )}
                        트렌드 분석
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">방향:</span>
                          <span className="font-medium">
                            {
                              analysisState.analysisResult.trend_analysis
                                .direction
                            }
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">강도:</span>
                          <span className="font-medium">
                            {
                              analysisState.analysisResult.trend_analysis
                                .strength
                            }
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">신뢰도:</span>
                          <span
                            className={`font-medium ${getConfidenceColor(
                              analysisState.analysisResult.trend_analysis
                                .confidence
                            )}`}
                          >
                            {(
                              analysisState.analysisResult.trend_analysis
                                .confidence * 100
                            ).toFixed(0)}
                            %
                          </span>
                        </div>
                      </div>

                      {analysisState.analysisResult.trend_analysis.key_points
                        .length > 0 && (
                        <div className="mt-4 pt-4 border-t">
                          <p className="text-sm font-medium text-gray-700 mb-2">
                            주요 포인트:
                          </p>
                          <ul className="text-sm text-gray-600 space-y-1">
                            {analysisState.analysisResult.trend_analysis.key_points.map(
                              (point, index) => (
                                <li
                                  key={index}
                                  className="flex items-start gap-2"
                                >
                                  <span className="text-blue-500 mt-1">•</span>
                                  <span>{point}</span>
                                </li>
                              )
                            )}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>

                  {/* 리스크 평가 */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Shield className="size-5 text-blue-600" />
                        리스크 평가
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex justify-between items-center">
                          <span className="text-sm text-gray-600">
                            위험 수준:
                          </span>
                          <span
                            className={`px-2 py-1 rounded text-sm font-medium ${getRiskColor(
                              analysisState.analysisResult.risk_assessment.level
                            )}`}
                          >
                            {analysisState.analysisResult.risk_assessment.level}
                          </span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-sm text-gray-600">전망:</span>
                          <span className="font-medium">
                            {
                              analysisState.analysisResult.risk_assessment
                                .outlook
                            }
                          </span>
                        </div>
                      </div>

                      {analysisState.analysisResult.risk_assessment.factors
                        .length > 0 && (
                        <div className="mt-4 pt-4 border-t">
                          <p className="text-sm font-medium text-gray-700 mb-2">
                            리스크 요인:
                          </p>
                          <ul className="text-sm text-gray-600 space-y-1">
                            {analysisState.analysisResult.risk_assessment.factors.map(
                              (factor, index) => (
                                <li
                                  key={index}
                                  className="flex items-start gap-2"
                                >
                                  <AlertTriangle className="size-3 text-orange-500 mt-1 flex-shrink-0" />
                                  <span>{factor}</span>
                                </li>
                              )
                            )}
                          </ul>
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>

                {/* 핵심 인사이트 */}
                {analysisState.analysisResult.key_insights.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Lightbulb className="size-5 text-yellow-600" />
                        핵심 인사이트
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-3">
                        {analysisState.analysisResult.key_insights.map(
                          (insight, index) => (
                            <motion.li
                              key={index}
                              initial={{ opacity: 0, x: -10 }}
                              animate={{ opacity: 1, x: 0 }}
                              transition={{ delay: 0.2 + index * 0.1 }}
                              className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg"
                            >
                              <span className="text-blue-600 font-bold text-lg mt-0.5">
                                {index + 1}
                              </span>
                              <span className="text-gray-700">{insight}</span>
                            </motion.li>
                          )
                        )}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                {/* 권고사항 */}
                {analysisState.analysisResult.recommendations.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-base flex items-center gap-2">
                        <Target className="size-5 text-green-600" />
                        권고사항
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ul className="space-y-2">
                        {analysisState.analysisResult.recommendations.map(
                          (recommendation, index) => (
                            <li key={index} className="flex items-start gap-2">
                              <CheckCircle className="size-4 text-green-500 mt-1 flex-shrink-0" />
                              <span className="text-gray-700">
                                {recommendation}
                              </span>
                            </li>
                          )
                        )}
                      </ul>
                    </CardContent>
                  </Card>
                )}

                {/* 분석 메타데이터 */}
                <div className="text-center text-sm text-gray-500">
                  분석 완료 시간:{' '}
                  {new Date(
                    analysisState.analysisResult.analysis_timestamp
                  ).toLocaleString('ko-KR')}
                </div>
              </motion.div>
            )}
          </CardContent>
        </Card>
      </motion.div>
    </AnimatePresence>
  )
}

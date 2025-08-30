import React, { useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  PieChart,
  Plus,
  Save,
  TrendingUp,
  Trash2,
  RefreshCw,
  Info,
  BarChart3,
  Settings,
  PlayCircle,
  BarChart,
  Target,
  FileText
} from 'lucide-react'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { ConfirmDialog } from '../components/ui/dialog'
import { StockAutocomplete } from '../components/ui/stock-autocomplete'
import {
  portfolioApi,
  PortfolioResponse,
  BacktestRequest,
  BacktestResponse
} from '../api/portfolio'
import {
  PortfolioWeights,
  PortfolioMetrics,
  DiscreteAllocation,
  CorrelationMatrix,
  EfficientFrontier
} from '../components/portfolio'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
  Legend
} from 'recharts'
import toast from 'react-hot-toast'

type OptimizationMethod =
  | 'max_sharpe'
  | 'min_volatility'
  | 'efficient_frontier'
  | 'risk_parity'

export const Portfolio: React.FC = () => {
  // 포트폴리오 구성 상태
  const [selectedTickers, setSelectedTickers] = useState<string[]>([])
  const [optimizationMethod, setOptimizationMethod] =
    useState<OptimizationMethod>('max_sharpe')
  const [searchValue, setSearchValue] = useState('')

  // 백테스트 결과
  const [backtestResult, setBacktestResult] = useState<BacktestResponse | null>(
    null
  )
  const [isBacktesting, setIsBacktesting] = useState(false)

  // 포트폴리오 저장
  const [portfolioName, setPortfolioName] = useState('')
  const [portfolioDescription, setPortfolioDescription] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  // 저장된 포트폴리오 목록
  const [savedPortfolios, setSavedPortfolios] = useState<PortfolioResponse[]>(
    []
  )
  const [isLoadingPortfolios, setIsLoadingPortfolios] = useState(false)

  // 포트폴리오 삭제 확인 모달
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<{
    id: number
    name: string
  } | null>(null)

  // 저장된 포트폴리오 목록 불러오기
  const loadSavedPortfolios = useCallback(async () => {
    setIsLoadingPortfolios(true)
    try {
      const portfolios = await portfolioApi.getUserPortfolios()
      setSavedPortfolios(portfolios)
    } catch (error) {
      console.error('포트폴리오 목록 불러오기 실패:', error)
      toast.error('포트폴리오 목록을 불러오는데 실패했습니다.')
    } finally {
      setIsLoadingPortfolios(false)
    }
  }, [])

  // 컴포넌트 마운트 시 저장된 포트폴리오 불러오기
  useEffect(() => {
    loadSavedPortfolios()
  }, [loadSavedPortfolios])

  // 종목 추가
  const handleAddTicker = useCallback(
    (ticker: string) => {
      const upperTicker = ticker.toUpperCase()
      if (
        !selectedTickers.includes(upperTicker) &&
        selectedTickers.length < 20
      ) {
        setSelectedTickers((prev) => [...prev, upperTicker])
        setSearchValue('') // 검색 입력 초기화
      } else if (selectedTickers.includes(upperTicker)) {
        toast.error('이미 추가된 종목입니다.')
      } else {
        toast.error('최대 20개 종목까지만 추가할 수 있습니다.')
      }
    },
    [selectedTickers]
  )

  // 종목 제거
  const handleRemoveTicker = useCallback((ticker: string) => {
    setSelectedTickers((prev) => prev.filter((t) => t !== ticker))
  }, [])

  // Walk-Forward 백테스팅 실행 (Only Walk-Forward Analysis)
  const handleBacktest = async () => {
    if (selectedTickers.length < 2) {
      toast.error('최소 2개 이상의 종목을 선택해주세요.')
      return
    }

    setIsBacktesting(true)
    try {
      const backtestRequest: BacktestRequest = {
        tickers: selectedTickers,
        optimization_method: optimizationMethod,
        investment_amount: 100000,
        transaction_cost: 0.001,
        max_position_size: 0.3
      }

      // Only Walk-Forward Analysis
      const result = await portfolioApi.backtestWalkForward(backtestRequest)

      setBacktestResult(result)
      toast.success('Walk-Forward Analysis 백테스팅이 완료되었습니다!')
    } catch (error: any) {
      console.error('백테스팅 실패:', error)
      toast.error(error?.response?.data?.detail || '백테스팅에 실패했습니다.')
    } finally {
      setIsBacktesting(false)
    }
  }

  // 포트폴리오 저장
  const handleSave = async () => {
    if (!portfolioName.trim()) {
      toast.error('포트폴리오 이름을 입력해주세요.')
      return
    }

    // Walk-Forward 백테스트 결과가 있어야 저장 가능
    if (!backtestResult || !backtestResult.results?.final_weights) {
      toast.error('Walk-Forward Analysis 백테스트를 먼저 실행해주세요.')
      return
    }

    setIsSaving(true)
    try {
      await portfolioApi.create({
        name: portfolioName.trim(),
        description: portfolioDescription.trim() || undefined,
        tickers: backtestResult.tickers, // 백테스트에서 검증된 종목 사용
        optimization_method: optimizationMethod
      })

      toast.success('포트폴리오가 저장되었습니다!')
      setPortfolioName('')
      setPortfolioDescription('')

      // 저장된 포트폴리오 목록 새로고침
      await loadSavedPortfolios()
    } catch (error: any) {
      console.error('저장 실패:', error)
      toast.error(
        error?.response?.data?.detail || '포트폴리오 저장에 실패했습니다.'
      )
    } finally {
      setIsSaving(false)
    }
  }

  // 포트폴리오 삭제 클릭 처리
  const handleDeleteClick = (portfolioId: number, portfolioName: string) => {
    setDeleteTarget({ id: portfolioId, name: portfolioName })
    setShowDeleteConfirm(true)
  }

  // 포트폴리오 삭제 확인
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return

    try {
      await portfolioApi.deletePortfolio(deleteTarget.id)
      toast.success('포트폴리오가 삭제되었습니다.')
      await loadSavedPortfolios()
    } catch (error: any) {
      console.error('삭제 실패:', error)
      toast.error(
        error?.response?.data?.detail || '포트폴리오 삭제에 실패했습니다.'
      )
    }
  }

  // 저장된 포트폴리오 불러오기
  const handleLoadPortfolio = (portfolio: PortfolioResponse) => {
    setSelectedTickers(portfolio.tickers)
    setOptimizationMethod(portfolio.optimization_method as OptimizationMethod)

    // 백테스트 결과 초기화 (새로운 백테스트 실행 필요)
    setBacktestResult(null)

    toast.success(`"${portfolio.name}" 포트폴리오를 불러왔습니다. 백테스트를 다시 실행해주세요.`)
  }

  const optimizationMethods = [
    {
      value: 'max_sharpe',
      label: '샤프비율 최대화',
      description: '위험 대비 수익률을 최적화하여 효율적인 포트폴리오 구성'
    },
    {
      value: 'min_volatility',
      label: '변동성 최소화',
      description: '리스크를 최소화한 안전한 포트폴리오 구성'
    },
    {
      value: 'efficient_frontier',
      label: '효율적 프론티어',
      description: '적정 수준의 위험과 수익률 균형을 맞춘 포트폴리오 구성'
    },
    {
      value: 'risk_parity',
      label: '리스크 패리티',
      description: '각 자산의 위험 기여도를 균등하게 분배한 포트폴리오 구성'
    }
  ]

  return (
    <div className="space-y-8">
      {/* Page Header */}
      <div className="text-center">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900 mb-2">
          📊 포트폴리오 최적화
        </h1>
        <p className="text-gray-600 text-sm md:text-base max-w-2xl mx-auto">
          월스트리트 표준 Walk-Forward Analysis 백테스팅 방법론으로 신뢰할 수
          있는 포트폴리오를 구성하세요.
          <br />
          단계별 가이드를 따라 최적화된 투자 포트폴리오를 생성할 수 있습니다.
        </p>
      </div>

      {/* Step Progress Indicator */}
      <div className="flex items-center justify-center space-x-4 mb-8">
        <div className="flex items-center">
          <div className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-800 rounded-full text-sm font-semibold">
            1
          </div>
          <span className="ml-2 text-sm font-medium text-gray-700">설정</span>
        </div>
        <div className="w-12 h-0.5 bg-gray-200"></div>
        <div className="flex items-center">
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${
              backtestResult
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            2
          </div>
          <span
            className={`ml-2 text-sm font-medium ${
              backtestResult ? 'text-gray-700' : 'text-gray-500'
            }`}
          >
            결과
          </span>
        </div>
        <div className="w-12 h-0.5 bg-gray-200"></div>
        <div className="flex items-center">
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${
              backtestResult
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            3
          </div>
          <span
            className={`ml-2 text-sm font-medium ${
              backtestResult ? 'text-gray-700' : 'text-gray-500'
            }`}
          >
            분석
          </span>
        </div>
        <div className="w-12 h-0.5 bg-gray-200"></div>
        <div className="flex items-center">
          <div
            className={`flex items-center justify-center w-8 h-8 rounded-full text-sm font-semibold ${
              backtestResult
                ? 'bg-green-100 text-green-800'
                : 'bg-gray-100 text-gray-500'
            }`}
          >
            4
          </div>
          <span
            className={`ml-2 text-sm font-medium ${
              backtestResult ? 'text-gray-700' : 'text-gray-500'
            }`}
          >
            실행
          </span>
        </div>
      </div>

      {/* SECTION 1: Portfolio Configuration */}
      <section className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-blue-100 text-blue-600 rounded-full mb-4">
            <Settings className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            1. 포트폴리오 구성
          </h2>
          <p className="text-gray-600 text-sm">
            종목 선택과 최적화 전략을 설정하세요
          </p>
        </div>

        <Card className="border-blue-200">
          <CardHeader className="bg-blue-50">
            <CardTitle className="flex items-center gap-2 text-blue-900">
              <Target className="size-5" />
              포트폴리오 설정
            </CardTitle>
            <CardDescription className="text-blue-700">
              2-20개 종목을 선택하여 최적화된 포트폴리오를 생성하세요
              <br />
              <span className="text-xs text-blue-600 font-medium">
                💡 모든 방법에서 CAPM(60%) + EWMA(40%) 하이브리드 기대수익률을
                사용합니다
              </span>
              <br />
              <span className="text-xs text-green-600 font-medium">
                🎯 Walk-Forward Analysis는 실제 월스트리트에서 사용하는 표준
                백테스팅 방법입니다
              </span>
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* 종목 선택 */}
            <div>
              <Label>종목 선택 ({selectedTickers.length}/20)</Label>
              <div className="mt-2 flex flex-wrap gap-2 mb-3">
                {selectedTickers.map((ticker) => (
                  <span
                    key={ticker}
                    className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm cursor-pointer hover:bg-blue-200 transition-colors"
                    onClick={() => handleRemoveTicker(ticker)}
                    title="클릭하여 제거"
                  >
                    {ticker} ×
                  </span>
                ))}
              </div>
              <StockAutocomplete
                value={searchValue}
                onChange={setSearchValue}
                onSelect={(stock) => handleAddTicker(stock.symbol)}
                placeholder="종목 코드나 회사명으로 검색..."
                disabled={selectedTickers.length >= 20}
              />
              {selectedTickers.length >= 20 && (
                <p className="text-xs text-red-500 mt-1">
                  최대 20개 종목까지만 선택할 수 있습니다.
                </p>
              )}
            </div>

            {/* 최적화 방법 */}
            <div>
              <Label>최적화 방법</Label>
              <div className="mt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
                {optimizationMethods.map((method) => (
                  <div
                    key={method.value}
                    className={`p-3 border rounded-lg cursor-pointer transition-colors ${
                      optimizationMethod === method.value
                        ? 'border-blue-500 bg-blue-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                    onClick={() => setOptimizationMethod(method.value as any)}
                  >
                    <div className="font-medium text-sm">{method.label}</div>
                    <div className="text-xs text-gray-600 mt-1">
                      {method.description}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="border-t pt-6">
              <div className="text-center mb-4">
                <div className="inline-flex items-center justify-center w-10 h-10 bg-green-100 text-green-600 rounded-full mb-2">
                  <PlayCircle className="w-5 h-5" />
                </div>
                <h3 className="font-semibold text-gray-900">
                  Walk-Forward Analysis 실행
                </h3>
                <p className="text-sm text-gray-600">
                  설정이 완료되면 월스트리트 표준 백테스트를 실행하세요
                </p>
              </div>

              <Button
                onClick={handleBacktest}
                disabled={selectedTickers.length < 2 || isBacktesting}
                className="w-full bg-green-600 hover:bg-green-700"
                size="lg"
              >
                {isBacktesting ? (
                  <>
                    <RefreshCw className="size-4 mr-2 animate-spin" />
                    Walk-Forward Analysis 진행 중...
                  </>
                ) : (
                  <>
                    <TrendingUp className="size-4 mr-2" />
                    Walk-Forward Analysis 실행
                  </>
                )}
              </Button>
            </div>

            {/* Walk-Forward Analysis 설명 */}
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
              <h4 className="font-medium text-amber-800 mb-2 flex items-center gap-2">
                <Info className="size-4" />
                Walk-Forward Analysis 설명
              </h4>
              <div className="text-sm text-amber-700">
                <p>
                  • 실제 투자환경을 완벽 모사하여 미래 데이터 누설 완전 방지
                </p>
                <p>
                  • 1년 데이터로 학습 → 1개월 실제 성과 측정 → 월별 리밸런싱
                  반복
                </p>
                <p>
                  • 가장 현실적이고 신뢰할 수 있는 월스트리트 표준 백테스트 방법
                </p>
                <p>• 거래비용, 슬리피지 등 실제 제약사항 모두 반영</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* SECTION 2: Results Overview */}
      {backtestResult && (
        <>
          <section className="space-y-6">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-green-100 text-green-600 rounded-full mb-4">
                <BarChart className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                2. 백테스트 결과
              </h2>
              <p className="text-gray-600 text-sm">
                Walk-Forward Analysis 백테스트 결과 요약
              </p>
            </div>

            {/* Consolidated Performance Metrics */}
            {backtestResult.results?.summary_stats && (
              <PortfolioMetrics
                optimization={{
                  weights: backtestResult.results.final_weights || {},
                  expected_annual_return:
                    backtestResult.results.summary_stats.annualized_return,
                  annual_volatility:
                    backtestResult.results.summary_stats.annualized_volatility,
                  sharpe_ratio:
                    backtestResult.results.summary_stats.sharpe_ratio,
                  max_drawdown:
                    backtestResult.results.summary_stats.max_drawdown,
                  transaction_cost_impact: 0.1,
                  concentration_limit: 30.0,
                  walkForwardStats: {
                    totalPeriods:
                      backtestResult.results.summary_stats.total_periods,
                    winRate: backtestResult.results.summary_stats.win_rate,
                    totalReturn:
                      backtestResult.results.summary_stats.total_return,
                    finalValue:
                      backtestResult.results.summary_stats.final_value,
                    totalRebalances:
                      backtestResult.results.walk_forward_results?.length || 0,
                    avgSharpe: backtestResult.results.walk_forward_results
                      ? backtestResult.results.walk_forward_results.reduce(
                          (sum: number, r: any) => sum + r.period_sharpe,
                          0
                        ) / backtestResult.results.walk_forward_results.length
                      : 0,
                    positiveReturns:
                      backtestResult.results.walk_forward_results?.filter(
                        (r: any) => r.period_return > 0
                      ).length || 0,
                    negativeReturns:
                      backtestResult.results.walk_forward_results?.filter(
                        (r: any) => r.period_return < 0
                      ).length || 0
                  }
                }}
              />
            )}
          </section>

          {/* SECTION 3: Detailed Analysis */}
          <section className="space-y-6">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-purple-100 text-purple-600 rounded-full mb-4">
                <BarChart3 className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                3. 상세 분석
              </h2>
              <p className="text-gray-600 text-sm">
                포트폴리오 구성, 상관관계, 효율적 프론티어 분석
              </p>
            </div>

            {/* Portfolio Weights */}
            {backtestResult.results?.final_weights && (
              <PortfolioWeights
                weights={backtestResult.results.final_weights}
                tickers={backtestResult.tickers}
              />
            )}

            {/* Weight Changes Over Time Chart */}
            {backtestResult.results?.walk_forward_results && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="size-5" />
                    포트폴리오 가중치 변화 (전체 리밸런싱)
                  </CardTitle>
                  <CardDescription>
                    시간에 따른 각 종목별 비중 변화를 확인하세요 - 전체{' '}
                    {backtestResult.results.walk_forward_results.length}회
                    리밸런싱
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {(() => {
                    const allTickers: string[] = Array.from(
                      new Set(
                        backtestResult.results.walk_forward_results.flatMap(
                          (r: any) => Object.keys(r.weights)
                        )
                      )
                    )

                    const chartData =
                      backtestResult.results.walk_forward_results.map(
                        (result: any) => {
                          const dataPoint: any = {
                            date: new Date(
                              result.period_start
                            ).toLocaleDateString('ko-KR', {
                              year: '2-digit',
                              month: 'short'
                            }),
                            fullDate: result.period_start,
                            period_return: result.period_return
                          }

                          allTickers.forEach((ticker: string) => {
                            dataPoint[ticker] =
                              (result.weights[ticker] || 0) * 100
                          })

                          return dataPoint
                        }
                      )

                    const colors = [
                      '#3b82f6',
                      '#ef4444',
                      '#10b981',
                      '#f59e0b',
                      '#8b5cf6',
                      '#06b6d4',
                      '#84cc16',
                      '#f97316',
                      '#ec4899',
                      '#6366f1',
                      '#14b8a6',
                      '#eab308',
                      '#a855f7',
                      '#059669',
                      '#dc2626'
                    ]

                    const CustomTooltip = ({ active, payload, label }: any) => {
                      if (active && payload && payload.length) {
                        return (
                          <div className="bg-white p-3 border rounded-lg shadow-lg">
                            <div className="font-semibold text-gray-900 mb-2">
                              {label}
                            </div>
                            <div className="space-y-1 text-sm">
                              {payload.map((entry: any, index: number) => (
                                <div
                                  key={index}
                                  className="flex items-center justify-between gap-4"
                                >
                                  <div className="flex items-center gap-2">
                                    <div
                                      className="w-3 h-3 rounded"
                                      style={{ backgroundColor: entry.color }}
                                    />
                                    <span className="font-medium">
                                      {entry.dataKey}
                                    </span>
                                  </div>
                                  <span className="font-semibold">
                                    {entry.value.toFixed(1)}%
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )
                      }
                      return null
                    }

                    return (
                      <div className="h-96">
                        <ResponsiveContainer width="100%" height="100%">
                          <AreaChart
                            data={chartData}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="date"
                              fontSize={12}
                              tick={{ fontSize: 11 }}
                            />
                            <YAxis
                              domain={[0, 100]}
                              tickFormatter={(value) => `${value}%`}
                              fontSize={12}
                              tick={{ fontSize: 11 }}
                            />
                            <Tooltip content={<CustomTooltip />} />
                            <Legend
                              wrapperStyle={{
                                paddingTop: '20px',
                                fontSize: '12px'
                              }}
                            />

                            {allTickers.map((ticker: string, index: number) => (
                              <Area
                                key={ticker}
                                type="monotone"
                                dataKey={ticker}
                                stackId="1"
                                stroke={colors[index % colors.length]}
                                fill={colors[index % colors.length]}
                                fillOpacity={0.8}
                              />
                            ))}
                          </AreaChart>
                        </ResponsiveContainer>
                      </div>
                    )
                  })()}
                </CardContent>
              </Card>
            )}

            {/* Monthly Returns Timeline */}
            {backtestResult.results?.walk_forward_results && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="size-5" />
                    월별 수익률 타임라인
                  </CardTitle>
                  <CardDescription>
                    각 리밸런싱 기간별 수익률 추이를 확인하세요
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {(() => {
                    const performanceData =
                      backtestResult.results.walk_forward_results.map(
                        (result: any) => ({
                          date: new Date(
                            result.period_start
                          ).toLocaleDateString('ko-KR', {
                            year: '2-digit',
                            month: 'short'
                          }),
                          fullDate: result.period_start,
                          return: (result.period_return * 100).toFixed(2),
                          returnValue: result.period_return * 100,
                          sharpe: result.period_sharpe,
                          portfolioValue: result.portfolio_value
                        })
                      )

                    const CustomPerformanceTooltip = ({
                      active,
                      payload,
                      label
                    }: any) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload
                        return (
                          <div className="bg-white p-3 border rounded-lg shadow-lg">
                            <div className="font-semibold text-gray-900 mb-2">
                              {label}
                            </div>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between gap-4">
                                <span className="text-gray-600">
                                  월간 수익률:
                                </span>
                                <span
                                  className={`font-semibold ${
                                    data.returnValue >= 0
                                      ? 'text-green-600'
                                      : 'text-red-600'
                                  }`}
                                >
                                  {data.returnValue >= 0 ? '+' : ''}
                                  {data.return}%
                                </span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-gray-600">
                                  샤프 비율:
                                </span>
                                <span className="font-semibold">
                                  {data.sharpe.toFixed(2)}
                                </span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-gray-600">
                                  포트폴리오 가치:
                                </span>
                                <span className="font-semibold">
                                  ${data.portfolioValue.toLocaleString()}
                                </span>
                              </div>
                            </div>
                          </div>
                        )
                      }
                      return null
                    }

                    return (
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart
                            data={performanceData}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="date"
                              fontSize={12}
                              tick={{ fontSize: 11 }}
                            />
                            <YAxis
                              tickFormatter={(value) => `${value}%`}
                              fontSize={12}
                              tick={{ fontSize: 11 }}
                            />
                            <Tooltip content={<CustomPerformanceTooltip />} />
                            <Legend />

                            <Line
                              type="monotone"
                              dataKey={() => 0}
                              stroke="#6b7280"
                              strokeWidth={1}
                              strokeDasharray="5 5"
                              dot={false}
                              name="기준선 (0%)"
                            />

                            <Line
                              type="monotone"
                              dataKey="returnValue"
                              stroke="#3b82f6"
                              strokeWidth={3}
                              dot={{ r: 4, fill: '#3b82f6' }}
                              activeDot={{
                                r: 6,
                                stroke: '#3b82f6',
                                strokeWidth: 2
                              }}
                              name="월간 수익률 (%)"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )
                  })()}
                </CardContent>
              </Card>
            )}

            {/* Cumulative Returns Timeline */}
            {backtestResult.results?.walk_forward_results && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="size-5" />
                    누적 수익률 타임라인
                  </CardTitle>
                  <CardDescription>
                    시간에 따른 포트폴리오 누적 수익률 추이를 확인하세요
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {(() => {
                    // 누적 수익률 데이터 계산
                    let cumulativeReturn = 1 // 1에서 시작 (100%)
                    const cumulativeData =
                      backtestResult.results.walk_forward_results.map(
                        (result: any, index: number) => {
                          if (index === 0) {
                            cumulativeReturn = 1 + result.period_return // 첫 번째 기간
                          } else {
                            cumulativeReturn =
                              cumulativeReturn * (1 + result.period_return) // 복리 계산
                          }

                          return {
                            date: new Date(
                              result.period_start
                            ).toLocaleDateString('ko-KR', {
                              year: '2-digit',
                              month: 'short'
                            }),
                            fullDate: result.period_start,
                            cumulativeReturn: (cumulativeReturn - 1) * 100, // 백분율로 변환
                            portfolioValue: result.portfolio_value,
                            monthlyReturn: result.period_return * 100,
                            sharpe: result.period_sharpe
                          }
                        }
                      )

                    const CustomCumulativeTooltip = ({
                      active,
                      payload,
                      label
                    }: any) => {
                      if (active && payload && payload.length) {
                        const data = payload[0].payload
                        return (
                          <div className="bg-white p-3 border rounded-lg shadow-lg">
                            <div className="font-semibold text-gray-900 mb-2">
                              {label}
                            </div>
                            <div className="space-y-1 text-sm">
                              <div className="flex justify-between gap-4">
                                <span className="text-gray-600">
                                  누적 수익률:
                                </span>
                                <span
                                  className={`font-semibold ${
                                    data.cumulativeReturn >= 0
                                      ? 'text-green-600'
                                      : 'text-red-600'
                                  }`}
                                >
                                  {data.cumulativeReturn >= 0 ? '+' : ''}
                                  {data.cumulativeReturn.toFixed(2)}%
                                </span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-gray-600">
                                  월간 수익률:
                                </span>
                                <span
                                  className={`font-medium ${
                                    data.monthlyReturn >= 0
                                      ? 'text-green-600'
                                      : 'text-red-600'
                                  }`}
                                >
                                  {data.monthlyReturn >= 0 ? '+' : ''}
                                  {data.monthlyReturn.toFixed(2)}%
                                </span>
                              </div>
                              <div className="flex justify-between gap-4">
                                <span className="text-gray-600">
                                  포트폴리오 가치:
                                </span>
                                <span className="font-semibold">
                                  ${data.portfolioValue.toLocaleString()}
                                </span>
                              </div>
                            </div>
                          </div>
                        )
                      }
                      return null
                    }

                    return (
                      <div className="h-80">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart
                            data={cumulativeData}
                            margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
                          >
                            <CartesianGrid
                              strokeDasharray="3 3"
                              opacity={0.3}
                            />
                            <XAxis
                              dataKey="date"
                              fontSize={12}
                              tick={{ fontSize: 11 }}
                            />
                            <YAxis
                              tickFormatter={(value) => `${value}%`}
                              fontSize={12}
                              tick={{ fontSize: 11 }}
                            />
                            <Tooltip content={<CustomCumulativeTooltip />} />
                            <Legend />

                            {/* 0% 기준선 */}
                            <Line
                              type="monotone"
                              dataKey={() => 0}
                              stroke="#6b7280"
                              strokeWidth={1}
                              strokeDasharray="5 5"
                              dot={false}
                              name="기준선 (0%)"
                            />

                            {/* 누적 수익률 라인 */}
                            <Line
                              type="monotone"
                              dataKey="cumulativeReturn"
                              stroke="#10b981"
                              strokeWidth={3}
                              dot={{ r: 4, fill: '#10b981' }}
                              activeDot={{
                                r: 6,
                                stroke: '#10b981',
                                strokeWidth: 2
                              }}
                              name="누적 수익률 (%)"
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )
                  })()}
                </CardContent>
              </Card>
            )}

            {/* Correlation Matrix */}
            {backtestResult.results?.correlation_matrix && (
              <CorrelationMatrix
                correlationMatrix={backtestResult.results.correlation_matrix}
                tickers={backtestResult.tickers}
              />
            )}

            {/* Efficient Frontier */}
            {backtestResult.results?.efficient_frontier &&
              backtestResult.results?.summary_stats && (
                <EfficientFrontier
                  efficientFrontier={backtestResult.results.efficient_frontier}
                  currentPortfolio={{
                    expected_return:
                      backtestResult.results.summary_stats.annualized_return,
                    volatility:
                      backtestResult.results.summary_stats.annualized_volatility
                  }}
                />
              )}
          </section>

          {/* SECTION 4: Implementation */}
          <section className="space-y-6">
            <div className="text-center">
              <div className="inline-flex items-center justify-center w-12 h-12 bg-indigo-100 text-indigo-600 rounded-full mb-4">
                <Target className="w-6 h-6" />
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                4. 포트폴리오 실행
              </h2>
              <p className="text-gray-600 text-sm">
                실제 투자를 위한 구체적인 주식 수량과 포트폴리오 저장
              </p>
            </div>

            {/* Discrete Allocation - Actual Shares to Buy */}
            {backtestResult.results?.discrete_allocation &&
              backtestResult.results?.final_weights && (
                <DiscreteAllocation
                  allocation={backtestResult.results.discrete_allocation}
                  leftoverCash={backtestResult.results.leftover_cash || 0}
                  weights={backtestResult.results.final_weights}
                />
              )}

            {/* Portfolio Save Functionality */}
            {backtestResult.results?.final_weights && (
              <Card className="bg-gradient-to-r from-green-50 to-emerald-50 border-green-200">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-green-800">
                    <Save className="size-5" />
                    포트폴리오 저장
                  </CardTitle>
                  <CardDescription className="text-green-700">
                    Walk-Forward 분석으로 검증된 포트폴리오를 저장하여 나중에
                    사용하세요
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label htmlFor="backtestPortfolioName">
                      포트폴리오 이름
                    </Label>
                    <Input
                      id="backtestPortfolioName"
                      value={portfolioName}
                      onChange={(e) => setPortfolioName(e.target.value)}
                      placeholder="예: Walk-Forward 최적화 포트폴리오"
                      className="mt-1"
                    />
                  </div>

                  <div>
                    <Label htmlFor="backtestPortfolioDescription">
                      설명 (선택사항)
                    </Label>
                    <Input
                      id="backtestPortfolioDescription"
                      value={portfolioDescription}
                      onChange={(e) => setPortfolioDescription(e.target.value)}
                      placeholder="포트폴리오에 대한 간단한 설명..."
                      className="mt-1"
                    />
                  </div>

                  <Button
                    onClick={handleSave}
                    disabled={!portfolioName.trim() || isSaving}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    {isSaving ? (
                      <>
                        <RefreshCw className="size-4 mr-2 animate-spin" />
                        저장 중...
                      </>
                    ) : (
                      <>
                        <Save className="size-4 mr-2" />
                        포트폴리오 저장
                      </>
                    )}
                  </Button>
                </CardContent>
              </Card>
            )}
          </section>
        </>
      )}

      {/* SECTION 5: Portfolio Management */}
      <section className="space-y-6">
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-gray-100 text-gray-600 rounded-full mb-4">
            <FileText className="w-6 h-6" />
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">
            5. 포트폴리오 관리
          </h2>
          <p className="text-gray-600 text-sm">
            저장된 포트폴리오를 불러오거나 관리하세요
          </p>
        </div>

        <Card className="border-gray-200">
          <CardHeader className="bg-gray-50">
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-gray-900">
                <PieChart className="size-5" />
                저장된 포트폴리오
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={loadSavedPortfolios}
                disabled={isLoadingPortfolios}
              >
                {isLoadingPortfolios ? (
                  <RefreshCw className="size-4 animate-spin" />
                ) : (
                  <RefreshCw className="size-4" />
                )}
              </Button>
            </CardTitle>
            <CardDescription className="text-gray-700">
              이전에 생성한 포트폴리오를 불러오거나 관리할 수 있습니다
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isLoadingPortfolios ? (
              <div className="flex items-center justify-center py-8">
                <RefreshCw className="size-6 animate-spin text-gray-400" />
                <span className="ml-2 text-gray-500">
                  포트폴리오 목록을 불러오는 중...
                </span>
              </div>
            ) : !savedPortfolios || savedPortfolios.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <PieChart className="size-12 mx-auto mb-4 text-gray-300" />
                <p>저장된 포트폴리오가 없습니다.</p>
                <p className="text-sm">
                  위에서 포트폴리오를 생성하고 저장해보세요.
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {savedPortfolios.map((portfolio) => (
                  <motion.div
                    key={portfolio.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="border rounded-lg p-4 hover:shadow-md transition-shadow"
                  >
                    <div className="flex justify-between items-start mb-3">
                      <h4 className="font-semibold text-gray-900 truncate">
                        {portfolio.name}
                      </h4>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() =>
                          handleDeleteClick(portfolio.id, portfolio.name)
                        }
                        className="text-red-500 hover:text-red-700 hover:bg-red-50 p-1"
                      >
                        <Trash2 className="size-4" />
                      </Button>
                    </div>

                    {portfolio.description && (
                      <p className="text-sm text-gray-600 mb-3 line-clamp-2">
                        {portfolio.description}
                      </p>
                    )}

                    <div className="space-y-2 mb-4">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">종목 수:</span>
                        <span className="font-medium">
                          {portfolio.tickers.length}개
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">기대 수익률:</span>
                        <span
                          className={`font-medium ${
                            (portfolio.expected_return || 0) >= 0
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {((portfolio.expected_return || 0) * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">샤프 비율:</span>
                        <span className="font-medium">
                          {(portfolio.sharpe_ratio || 0).toFixed(2)}
                        </span>
                      </div>
                    </div>

                    <div className="flex flex-wrap gap-1 mb-4">
                      {portfolio.tickers.slice(0, 5).map((ticker) => (
                        <span
                          key={ticker}
                          className="px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs"
                        >
                          {ticker}
                        </span>
                      ))}
                      {portfolio.tickers.length > 5 && (
                        <span className="px-2 py-1 bg-gray-100 text-gray-500 rounded text-xs">
                          +{portfolio.tickers.length - 5}
                        </span>
                      )}
                    </div>

                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleLoadPortfolio(portfolio)}
                      className="w-full"
                    >
                      <Plus className="size-4 mr-2" />
                      불러오기
                    </Button>

                    <div className="text-xs text-gray-400 mt-2">
                      {new Date(portfolio.created_at).toLocaleDateString(
                        'ko-KR'
                      )}
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </section>

      {/* 주의사항 */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
      >
        <Card className="bg-amber-50 border-amber-200">
          <CardContent className="p-4">
            <h4 className="font-semibold text-amber-800 mb-2 flex items-center gap-2">
              <Info className="size-4" />
              투자 주의사항
            </h4>
            <div className="text-sm text-amber-800 space-y-1">
              <p>
                • 이 도구는 과거 데이터를 기반으로 한 시뮬레이션이며, 미래
                수익을 보장하지 않습니다.
              </p>
              <p>
                • 실제 투자 시에는 거래 비용, 세금, 유동성 등을 추가로 고려해야
                합니다.
              </p>
              <p>
                • 포트폴리오는 정기적으로 리밸런싱하고 시장 상황에 따라 조정이
                필요합니다.
              </p>
              <p>
                • 투자 결정은 신중히 하시고, 필요시 전문가와 상담하시기
                바랍니다.
              </p>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        onClose={() => {
          setShowDeleteConfirm(false)
          setDeleteTarget(null)
        }}
        onConfirm={handleDeleteConfirm}
        title="포트폴리오 삭제"
        message={`정말로 "${deleteTarget?.name}" 포트폴리오를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.`}
        confirmText="삭제"
        cancelText="취소"
        variant="danger"
      />
    </div>
  )
}

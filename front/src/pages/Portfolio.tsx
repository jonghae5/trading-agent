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
  | 'risk_parity'

export const Portfolio: React.FC = () => {
  // 포트폴리오 구성 상태
  const [selectedTickers, setSelectedTickers] = useState<string[]>([])
  const [tickerWeights, setTickerWeights] = useState<Record<string, number>>({})
  const [useCustomWeights, setUseCustomWeights] = useState(false)
  const [optimizationMethod, setOptimizationMethod] =
    useState<OptimizationMethod>('max_sharpe')
  const [rebalanceFrequency, setRebalanceFrequency] = useState<
    'monthly' | 'quarterly'
  >('monthly')
  const [searchValue, setSearchValue] = useState('')

  // 백테스트 결과
  const [backtestResult, setBacktestResult] = useState<BacktestResponse | null>(
    null
  )
  const [isBacktesting, setIsBacktesting] = useState(false)

  console.log('backtestResult', backtestResult)
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
    // 비중 정보도 함께 제거
    setTickerWeights((prev) => {
      const newWeights = { ...prev }
      delete newWeights[ticker]
      return newWeights
    })
  }, [])

  // 비중 업데이트
  const handleWeightChange = useCallback((ticker: string, weight: number) => {
    setTickerWeights((prev) => ({
      ...prev,
      [ticker]: weight
    }))
  }, [])

  // 균등 배분
  const handleEqualDistribution = useCallback(() => {
    if (selectedTickers.length === 0) return
    const equalWeight = 100 / selectedTickers.length
    const newWeights: Record<string, number> = {}
    selectedTickers.forEach((ticker) => {
      newWeights[ticker] = Math.round(equalWeight * 100) / 100
    })
    setTickerWeights(newWeights)
  }, [selectedTickers])

  // 비중 정규화 (합계가 100%가 되도록)
  const normalizeWeights = useCallback(() => {
    const totalWeight = selectedTickers.reduce(
      (sum, ticker) => sum + (tickerWeights[ticker] || 0),
      0
    )
    if (totalWeight === 0) return

    const normalizedWeights: Record<string, number> = {}
    selectedTickers.forEach((ticker) => {
      const currentWeight = tickerWeights[ticker] || 0
      normalizedWeights[ticker] =
        Math.round((currentWeight / totalWeight) * 100 * 100) / 100
    })
    setTickerWeights(normalizedWeights)
  }, [selectedTickers, tickerWeights])

  // 비중 유효성 검증
  const getWeightValidation = useCallback(() => {
    if (!useCustomWeights) return { isValid: true, message: '' }

    const totalWeight = selectedTickers.reduce(
      (sum, ticker) => sum + (tickerWeights[ticker] || 0),
      0
    )
    const hasEmptyWeights = selectedTickers.some(
      (ticker) => !tickerWeights[ticker] || tickerWeights[ticker] <= 0
    )

    if (hasEmptyWeights) {
      return { isValid: false, message: '모든 종목의 비중을 입력해주세요.' }
    }

    if (Math.abs(totalWeight - 100) > 0.1) {
      return {
        isValid: false,
        message: `비중 합계가 ${totalWeight.toFixed(
          1
        )}%입니다. 100%가 되어야 합니다.`
      }
    }

    return { isValid: true, message: '' }
  }, [useCustomWeights, selectedTickers, tickerWeights])

  // Walk-Forward 백테스팅 실행 (Only Walk-Forward Analysis)
  const handleBacktest = async () => {
    if (selectedTickers.length < 2) {
      toast.error('최소 2개 이상의 종목을 선택해주세요.')
      return
    }

    // 커스텀 비중 사용 시 유효성 검증
    const weightValidation = getWeightValidation()
    if (!weightValidation.isValid) {
      toast.error(weightValidation.message)
      return
    }

    setIsBacktesting(true)
    try {
      // 월가 공격적 집중투자 전략 적용
      const calculateMaxPositionSize = (tickerCount: number): number => {
        if (tickerCount === 2) return 0.5 // 2개 종목: 각 50%
        if (tickerCount === 3) return 0.35 // 3개 종목: 최대 35%
        if (tickerCount === 4) return 0.3 // 4개 종목: 최대 30%
        if (tickerCount === 5) return 0.25 // 5개 종목: 최대 25%
        if (tickerCount === 6) return 0.2 // 6개 종목: 최대 20%
        return 0.15 // 7개 이상: 최대 15%
      }

      // 커스텀 비중을 백분율에서 소수로 변환
      let requestWeights: Record<string, number> | undefined = undefined
      if (useCustomWeights && Object.keys(tickerWeights).length > 0) {
        requestWeights = {}
        selectedTickers.forEach((ticker) => {
          requestWeights![ticker] = (tickerWeights[ticker] || 0) / 100
        })
      }

      const backtestRequest: BacktestRequest = {
        tickers: selectedTickers,
        ticker_weights: requestWeights,
        optimization_method: optimizationMethod,
        rebalance_frequency: rebalanceFrequency,
        investment_amount: 100000,
        transaction_cost: 0.001,
        max_position_size: calculateMaxPositionSize(selectedTickers.length)
      }

      // Only Walk-Forward Analysis
      const result = await portfolioApi.backtestWalkForward(backtestRequest)

      setBacktestResult(result)
      toast.success('백테스팅이 완료되었습니다!')
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
      // 사용자 정의 비중이 있는 경우 포함해서 저장
      let weightsToSave: Record<string, number> | undefined = undefined
      if (useCustomWeights && Object.keys(tickerWeights).length > 0) {
        weightsToSave = {}
        selectedTickers.forEach((ticker) => {
          weightsToSave![ticker] = (tickerWeights[ticker] || 0) / 100 // 백분율을 소수로 변환
        })
      }

      await portfolioApi.create({
        name: portfolioName.trim(),
        description: portfolioDescription.trim() || undefined,
        tickers: backtestResult.tickers, // 백테스트에서 검증된 종목 사용
        ticker_weights: weightsToSave,
        optimization_method: optimizationMethod,
        rebalance_frequency: rebalanceFrequency
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

    // 리밸런싱 빈도 설정
    setRebalanceFrequency(
      (portfolio.rebalance_frequency as 'monthly' | 'quarterly') || 'monthly'
    )

    // 비중 정보가 있는 경우 불러오기
    if (
      portfolio.ticker_weights &&
      Object.keys(portfolio.ticker_weights).length > 0
    ) {
      setUseCustomWeights(true)
      // 소수를 백분율로 변환
      const percentWeights: Record<string, number> = {}
      Object.entries(portfolio.ticker_weights).forEach(([ticker, weight]) => {
        percentWeights[ticker] = weight * 100
      })
      setTickerWeights(percentWeights)
    } else {
      setUseCustomWeights(false)
      setTickerWeights({})
    }

    // 백테스트 결과 초기화 (새로운 백테스트 실행 필요)
    setBacktestResult(null)

    const hasWeights =
      portfolio.ticker_weights &&
      Object.keys(portfolio.ticker_weights).length > 0
    toast.success(
      `"${portfolio.name}" 포트폴리오를 불러왔습니다${
        hasWeights ? ' (고정 비중 포함)' : ''
      }. 백테스트를 실행해주세요.`
    )
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
                💡 모든 방법에서 EWMA(지수이동평균) 기대수익률을 사용합니다
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

            {/* 비중 설정 */}
            {selectedTickers.length > 0 && (
              <div className="border-t pt-4">
                <div className="flex items-center justify-between mb-3">
                  <Label>포트폴리오 비중 설정</Label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="checkbox"
                      id="useCustomWeights"
                      checked={useCustomWeights}
                      onChange={(e) => {
                        setUseCustomWeights(e.target.checked)
                        if (!e.target.checked) {
                          setTickerWeights({})
                        }
                      }}
                      className="rounded"
                    />
                    <label
                      htmlFor="useCustomWeights"
                      className="text-sm font-medium"
                    >
                      고정 비중 사용
                    </label>
                  </div>
                </div>

                {useCustomWeights ? (
                  <div className="space-y-4">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <h4 className="font-medium text-blue-800 mb-2">
                        🎯 고정 비중 모드
                      </h4>
                      <p className="text-sm text-blue-700 mb-3">
                        각 종목의 비중을 직접 설정하면, 해당 비중으로 고정하여
                        리밸런싱했을 때의 성과와 최적화 결과를 함께 비교할 수
                        있습니다.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={handleEqualDistribution}
                          className="text-xs"
                        >
                          균등 배분
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={normalizeWeights}
                          className="text-xs"
                        >
                          비중 정규화
                        </Button>
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {selectedTickers.map((ticker) => (
                        <div
                          key={ticker}
                          className="flex items-center space-x-2"
                        >
                          <label className="text-sm font-medium min-w-[60px]">
                            {ticker}:
                          </label>
                          <div className="flex-1">
                            <Input
                              type="number"
                              min="0"
                              max="100"
                              step="0.1"
                              value={tickerWeights[ticker] || ''}
                              onChange={(e) => {
                                const value = parseFloat(e.target.value) || 0
                                if (value >= 0 && value <= 100) {
                                  handleWeightChange(ticker, value)
                                }
                              }}
                              placeholder="0.0"
                              className="text-sm"
                            />
                          </div>
                          <span className="text-sm text-gray-500 min-w-[20px]">
                            %
                          </span>
                        </div>
                      ))}
                    </div>

                    {/* 비중 합계 및 유효성 표시 */}
                    <div className="bg-gray-50 rounded-lg p-3">
                      {(() => {
                        const totalWeight = selectedTickers.reduce(
                          (sum, ticker) => sum + (tickerWeights[ticker] || 0),
                          0
                        )
                        const validation = getWeightValidation()

                        return (
                          <div className="flex items-center justify-between">
                            <span className="text-sm font-medium">
                              총 비중: {totalWeight.toFixed(1)}%
                            </span>
                            <div className="flex items-center">
                              {validation.isValid ? (
                                <span className="text-xs text-green-600 font-medium">
                                  ✓ 유효
                                </span>
                              ) : (
                                <span className="text-xs text-red-600 font-medium">
                                  {validation.message}
                                </span>
                              )}
                            </div>
                          </div>
                        )
                      })()}
                    </div>
                  </div>
                ) : (
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3">
                    <h4 className="font-medium text-gray-800 mb-2">
                      🤖 자동 최적화 모드
                    </h4>
                    <p className="text-sm text-gray-700">
                      선택한 최적화 방법에 따라 알고리즘이 자동으로 최적의
                      비중을 계산합니다.
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* 최적화 방법 */}
            <div>
              <Label>최적화 방법</Label>
              <div className="mt-2 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
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

            {/* 리밸런싱 빈도 */}
            <div>
              <Label>리밸런싱 빈도</Label>
              <div className="mt-2 grid grid-cols-1 md:grid-cols-2 gap-3">
                <div
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    rebalanceFrequency === 'monthly'
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setRebalanceFrequency('monthly')}
                >
                  <div className="font-medium text-sm mb-1">
                    📅 월별 리밸런싱
                  </div>
                  <div className="text-xs text-gray-600">
                    매달 포트폴리오 재조정 (더 빈번한 최적화)
                  </div>
                  <div className="text-xs text-green-600 font-medium mt-1">
                    ✓ 시장 변동에 민감한 대응
                  </div>
                </div>
                <div
                  className={`p-4 border rounded-lg cursor-pointer transition-colors ${
                    rebalanceFrequency === 'quarterly'
                      ? 'border-green-500 bg-green-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setRebalanceFrequency('quarterly')}
                >
                  <div className="font-medium text-sm mb-1">
                    📊 분기별 리밸런싱
                  </div>
                  <div className="text-xs text-gray-600">
                    3개월마다 포트폴리오 재조정 (안정적인 전략)
                  </div>
                  <div className="text-xs text-green-600 font-medium mt-1">
                    ✓ 거래 비용 절약 및 장기 관점
                  </div>
                </div>
              </div>
              <div className="mt-2 text-xs text-gray-500">
                💡 월별: 더 자주 최적화하여 시장 변화에 빠르게 대응 | 분기별:
                거래 비용을 줄이고 안정적인 장기 전략
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
                  • 1년 데이터로 학습 →{' '}
                  {rebalanceFrequency === 'monthly' ? '1개월' : '1분기'} 실제
                  성과 측정 →
                  <b>
                    {rebalanceFrequency === 'monthly' ? '월별' : '분기별'}{' '}
                    리밸런싱
                  </b>{' '}
                  반복
                </p>
                <p>
                  • 가장 현실적이고 신뢰할 수 있는 월스트리트 표준 백테스트 방법
                </p>
                <p>• 거래비용, 슬리피지 등 실제 제약사항 모두 반영</p>
                <p className="mt-2 font-medium">
                  🔄 선택된 리밸런싱:{' '}
                  <span className="text-amber-900">
                    {rebalanceFrequency === 'monthly'
                      ? '월별 (12회/년)'
                      : '분기별 (4회/년)'}
                  </span>
                </p>
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
              <div className="mt-2 inline-flex items-center px-3 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                🔄{' '}
                {rebalanceFrequency === 'monthly'
                  ? '월별 리밸런싱 (12회/년)'
                  : '분기별 리밸런싱 (4회/년)'}
              </div>
            </div>

            {/* Performance Comparison */}
            {backtestResult.results?.summary_stats && (
              <>
                <PortfolioMetrics
                  optimization={{
                    weights: backtestResult.results.final_weights || {},
                    expected_annual_return:
                      backtestResult.results.summary_stats.annualized_return,
                    annual_volatility:
                      backtestResult.results.summary_stats
                        .annualized_volatility,
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
                        backtestResult.results.walk_forward_results?.length ||
                        0,
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

                {/* Fixed Weights Performance Comparison */}
                {backtestResult.results?.fixed_weights_performance && (
                  <Card className="bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200">
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-purple-800">
                        <Target className="size-5" />
                        고정 비중 vs 최적화 성과 비교
                      </CardTitle>
                      <CardDescription className="text-purple-700">
                        설정한 고정 비중으로 리밸런싱한 결과와 알고리즘 최적화
                        결과를 비교합니다
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                        {/* 최적화 결과 */}
                        <div className="bg-white rounded-lg p-4 border">
                          <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                            🤖 알고리즘 최적화 ({optimizationMethod})
                          </h4>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                총 수익률:
                              </span>
                              <span
                                className={`text-sm font-medium ${
                                  backtestResult.results.summary_stats
                                    .total_return >= 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                }`}
                              >
                                {(
                                  backtestResult.results.summary_stats
                                    .total_return * 100
                                ).toFixed(2)}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                연간 수익률:
                              </span>
                              <span
                                className={`text-sm font-medium ${
                                  backtestResult.results.summary_stats
                                    .annualized_return >= 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                }`}
                              >
                                {(
                                  backtestResult.results.summary_stats
                                    .annualized_return * 100
                                ).toFixed(2)}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                샤프 비율:
                              </span>
                              <span className="text-sm font-medium">
                                {backtestResult.results.summary_stats.sharpe_ratio.toFixed(
                                  2
                                )}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                최대 낙폭:
                              </span>
                              <span className="text-sm font-medium text-red-600">
                                {(
                                  backtestResult.results.summary_stats
                                    .max_drawdown * 100
                                ).toFixed(2)}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                최종 가치:
                              </span>
                              <span className="text-sm font-medium">
                                $
                                {backtestResult.results.summary_stats.final_value.toLocaleString()}
                              </span>
                            </div>
                          </div>
                        </div>

                        {/* 고정 비중 결과 */}
                        <div className="bg-white rounded-lg p-4 border">
                          <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                            🎯 고정 비중 전략
                          </h4>
                          <div className="space-y-2">
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                총 수익률:
                              </span>
                              <span
                                className={`text-sm font-medium ${
                                  backtestResult.results
                                    .fixed_weights_performance.summary_stats
                                    .total_return >= 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                }`}
                              >
                                {(
                                  backtestResult.results
                                    .fixed_weights_performance.summary_stats
                                    .total_return * 100
                                ).toFixed(2)}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                연간 수익률:
                              </span>
                              <span
                                className={`text-sm font-medium ${
                                  backtestResult.results
                                    .fixed_weights_performance.summary_stats
                                    .annualized_return >= 0
                                    ? 'text-green-600'
                                    : 'text-red-600'
                                }`}
                              >
                                {(
                                  backtestResult.results
                                    .fixed_weights_performance.summary_stats
                                    .annualized_return * 100
                                ).toFixed(2)}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                샤프 비율:
                              </span>
                              <span className="text-sm font-medium">
                                {backtestResult.results.fixed_weights_performance.summary_stats.sharpe_ratio.toFixed(
                                  2
                                )}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                최대 낙폭:
                              </span>
                              <span className="text-sm font-medium text-red-600">
                                {(
                                  backtestResult.results
                                    .fixed_weights_performance.summary_stats
                                    .max_drawdown * 100
                                ).toFixed(2)}
                                %
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                최종 가치:
                              </span>
                              <span className="text-sm font-medium">
                                $
                                {backtestResult.results.fixed_weights_performance.summary_stats.final_value.toLocaleString()}
                              </span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-sm text-gray-600">
                                승률:
                              </span>
                              <span className="text-sm font-medium">
                                {(backtestResult.results.fixed_weights_performance.summary_stats.win_rate * 100).toFixed(1)}%
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Performance Difference */}
                      <div className="mt-4 bg-gray-50 rounded-lg p-3">
                        <h5 className="font-medium text-gray-900 mb-2">
                          성과 차이 분석
                        </h5>
                        {(() => {
                          const optimizedReturn =
                            backtestResult.results.summary_stats.total_return
                          const fixedReturn =
                            backtestResult.results.fixed_weights_performance
                              .summary_stats.total_return
                          const returnDiff = optimizedReturn - fixedReturn
                          const optimizedSharpe =
                            backtestResult.results.summary_stats.sharpe_ratio
                          const fixedSharpe =
                            backtestResult.results.fixed_weights_performance
                              .summary_stats.sharpe_ratio
                          const sharpeDiff = optimizedSharpe - fixedSharpe

                          return (
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                              <div className="flex justify-between">
                                <span className="text-gray-600">
                                  수익률 차이:
                                </span>
                                <span
                                  className={`font-medium ${
                                    returnDiff >= 0
                                      ? 'text-green-600'
                                      : 'text-red-600'
                                  }`}
                                >
                                  {returnDiff >= 0 ? '+' : ''}
                                  {(returnDiff * 100).toFixed(2)}%p (
                                  {returnDiff >= 0
                                    ? '최적화 우세'
                                    : '고정비중 우세'}
                                  )
                                </span>
                              </div>
                              <div className="flex justify-between">
                                <span className="text-gray-600">
                                  샤프 비율 차이:
                                </span>
                                <span
                                  className={`font-medium ${
                                    sharpeDiff >= 0
                                      ? 'text-green-600'
                                      : 'text-red-600'
                                  }`}
                                >
                                  {sharpeDiff >= 0 ? '+' : ''}
                                  {sharpeDiff.toFixed(3)}(
                                  {sharpeDiff >= 0
                                    ? '최적화 우세'
                                    : '고정비중 우세'}
                                  )
                                </span>
                              </div>
                            </div>
                          )
                        })()}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
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
                    {backtestResult.results?.fixed_weights_performance && (
                      <span className="text-sm font-normal text-purple-600 ml-2">
                        (알고리즘 vs 고정비중)
                      </span>
                    )}
                  </CardTitle>
                  <CardDescription>
                    시간에 따른 각 종목별 비중 변화를 확인하세요 - 전체{' '}
                    {backtestResult.results.walk_forward_results.length}회
                    리밸런싱
                    {backtestResult.results?.fixed_weights_performance && (
                      <span className="text-purple-600"> vs 고정 비중 유지</span>
                    )}
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

                    const algorithicChartData =
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

                    // 고정 비중 차트 데이터 생성
                    let fixedChartData: any[] = []
                    if (backtestResult.results?.fixed_weights_performance?.fixed_weights) {
                      const fixedWeights = backtestResult.results.fixed_weights_performance.fixed_weights
                      fixedChartData = algorithicChartData.map((item: any) => {
                        const dataPoint: any = {
                          date: item.date,
                          fullDate: item.fullDate
                        }
                        
                        allTickers.forEach((ticker: string) => {
                          dataPoint[ticker] = (fixedWeights[ticker] || 0) * 100
                        })
                        
                        return dataPoint
                      })
                    }

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
                                      className="size-3 rounded"
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
                      <div className={`grid ${backtestResult.results?.fixed_weights_performance ? 'grid-cols-1 lg:grid-cols-2' : 'grid-cols-1'} gap-6`}>
                        {/* 알고리즘 가중치 변화 */}
                        <div>
                          <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                            🤖 알고리즘 최적화 가중치 변화
                          </h4>
                          <div className="h-80">
                            <ResponsiveContainer width="100%" height="100%">
                              <AreaChart
                                data={algorithicChartData}
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
                                <Legend />

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
                        </div>

                        {/* 고정 비중 차트 (있는 경우에만) */}
                        {backtestResult.results?.fixed_weights_performance && (
                          <div>
                            <h4 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                              🎯 고정 비중 유지 (일정한 가중치)
                            </h4>
                            <div className="h-80">
                              <ResponsiveContainer width="100%" height="100%">
                                <AreaChart
                                  data={fixedChartData}
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
                                  <Legend />

                                  {allTickers.map((ticker: string, index: number) => (
                                    <Area
                                      key={ticker}
                                      type="monotone"
                                      dataKey={ticker}
                                      stackId="1"
                                      stroke={colors[index % colors.length]}
                                      fill={colors[index % colors.length]}
                                      fillOpacity={0.6}
                                    />
                                  ))}
                                </AreaChart>
                              </ResponsiveContainer>
                            </div>
                          </div>
                        )}
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
                    {rebalanceFrequency === 'monthly' ? '월별' : '분기별'}{' '}
                    수익률 타임라인
                    {backtestResult.results?.fixed_weights_performance && (
                      <span className="text-sm font-normal text-purple-600 ml-2">
                        (최적화 vs 고정비중 비교)
                      </span>
                    )}
                  </CardTitle>
                  <CardDescription>
                    각 리밸런싱 기간별 수익률 추이를 확인하세요 (
                    {rebalanceFrequency === 'monthly' ? '월간' : '분기별'} 분석)
                    {backtestResult.results?.fixed_weights_performance && (
                      <span className="text-purple-600">
                        {' '}
                        - 고정 비중 성과와 함께 비교
                      </span>
                    )}
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

                    // 고정 비중 리밸런싱 데이터 추가 (portfolio_timeline 사용)
                    if (
                      backtestResult.results?.fixed_weights_performance
                        ?.portfolio_timeline
                    ) {
                      const fixedResults =
                        backtestResult.results.fixed_weights_performance
                          .portfolio_timeline

                      // 고정 비중 기간별 수익률 매핑
                      const fixedPeriodReturns = new Map()
                      
                      fixedResults.forEach((result: any) => {
                        fixedPeriodReturns.set(
                          result.period_start,
                          result.period_return * 100
                        )
                      })

                      // 기존 데이터에 고정 비중 정보 추가
                      performanceData.forEach((item: any) => {
                        const fixedReturn = fixedPeriodReturns.get(
                          item.fullDate
                        )
                        if (fixedReturn !== undefined) {
                          item.fixedReturnValue = fixedReturn
                        }
                      })
                    }

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
                                  최적화{' '}
                                  {rebalanceFrequency === 'monthly'
                                    ? '월간'
                                    : '분기간'}{' '}
                                  수익률:
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
                              {data.fixedReturnValue !== undefined && (
                                <div className="flex justify-between gap-4">
                                  <span className="text-gray-600">
                                    고정비중{' '}
                                    {rebalanceFrequency === 'monthly'
                                      ? '월간'
                                      : '분기간'}{' '}
                                    수익률:
                                  </span>
                                  <span
                                    className={`font-semibold ${
                                      data.fixedReturnValue >= 0
                                        ? 'text-green-600'
                                        : 'text-red-600'
                                    }`}
                                  >
                                    {data.fixedReturnValue >= 0 ? '+' : ''}
                                    {data.fixedReturnValue.toFixed(2)}%
                                  </span>
                                </div>
                              )}
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
                              name={`최적화 ${
                                rebalanceFrequency === 'monthly'
                                  ? '월간'
                                  : '분기간'
                              } 수익률 (%)`}
                            />

                            {/* 고정 비중 수익률 라인 (있는 경우에만) */}
                            {backtestResult.results
                              ?.fixed_weights_performance && (
                              <Line
                                type="monotone"
                                dataKey="fixedReturnValue"
                                stroke="#8b5cf6"
                                strokeWidth={3}
                                strokeDasharray="8 4"
                                dot={{ r: 4, fill: '#8b5cf6' }}
                                activeDot={{
                                  r: 6,
                                  stroke: '#8b5cf6',
                                  strokeWidth: 2
                                }}
                                name={`고정비중 ${
                                  rebalanceFrequency === 'monthly'
                                    ? '월간'
                                    : '분기간'
                                } 수익률 (%)`}
                              />
                            )}
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
                    {backtestResult.results?.fixed_weights_performance && (
                      <span className="text-sm font-normal text-purple-600 ml-2">
                        (최적화 vs 고정비중 비교)
                      </span>
                    )}
                  </CardTitle>
                  <CardDescription>
                    시간에 따른 포트폴리오 누적 수익률 추이를 확인하세요
                    {backtestResult.results?.fixed_weights_performance && (
                      <span className="text-purple-600">
                        {' '}
                        - 고정 비중 성과와 함께 비교
                      </span>
                    )}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {(() => {
                    // 누적 수익률 데이터 계산 (최적화)
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

                    // 고정 비중 누적 수익률 계산 (있는 경우)
                    if (
                      backtestResult.results?.fixed_weights_performance
                        ?.portfolio_timeline
                    ) {
                      const fixedTimeline =
                        backtestResult.results.fixed_weights_performance
                          .portfolio_timeline

                      // 고정 비중 누적 수익률을 직접 계산
                      let fixedCumulativeReturn = 1 // 1에서 시작 (100%)
                      
                      // 날짜별로 고정 비중 데이터 매핑 (기간별 수익률로부터 누적 계산)
                      const fixedDataMap = new Map()
                      fixedTimeline.forEach((item: any, index: number) => {
                        if (index === 0) {
                          fixedCumulativeReturn = 1 + item.period_return // 첫 번째 기간
                        } else {
                          fixedCumulativeReturn = fixedCumulativeReturn * (1 + item.period_return) // 복리 계산
                        }
                        
                        fixedDataMap.set(
                          item.period_start, // period_start를 키로 사용
                          (fixedCumulativeReturn - 1) * 100 // 백분율로 변환
                        )
                      })

                      // 기존 데이터에 고정 비중 정보 추가
                      cumulativeData.forEach((item: any) => {
                        const fixedReturn = fixedDataMap.get(item.fullDate)
                        if (fixedReturn !== undefined) {
                          item.fixedCumulativeReturn = fixedReturn
                        }
                      })
                    }

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
                                  최적화 누적 수익률:
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
                              {data.fixedCumulativeReturn !== undefined && (
                                <div className="flex justify-between gap-4">
                                  <span className="text-gray-600">
                                    고정비중 누적 수익률:
                                  </span>
                                  <span
                                    className={`font-semibold ${
                                      data.fixedCumulativeReturn >= 0
                                        ? 'text-green-600'
                                        : 'text-red-600'
                                    }`}
                                  >
                                    {data.fixedCumulativeReturn >= 0 ? '+' : ''}
                                    {data.fixedCumulativeReturn.toFixed(2)}%
                                  </span>
                                </div>
                              )}
                              <div className="flex justify-between gap-4">
                                <span className="text-gray-600">
                                  {rebalanceFrequency === 'monthly'
                                    ? '월간'
                                    : '분기간'}{' '}
                                  수익률:
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

                            {/* 최적화 누적 수익률 라인 */}
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
                              name="알고리즘 최적화 누적 수익률 (%)"
                            />

                            {/* 고정 비중 누적 수익률 라인 (있는 경우에만) */}
                            {backtestResult.results
                              ?.fixed_weights_performance && (
                              <Line
                                type="monotone"
                                dataKey="fixedCumulativeReturn"
                                stroke="#8b5cf6"
                                strokeWidth={3}
                                strokeDasharray="8 4"
                                dot={{ r: 4, fill: '#8b5cf6' }}
                                activeDot={{
                                  r: 6,
                                  stroke: '#8b5cf6',
                                  strokeWidth: 2
                                }}
                                name="고정 비중 누적 수익률 (%)"
                              />
                            )}
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
                        <span className="text-gray-600">월별/분기별:</span>
                        <span
                          className={`font-medium ${
                            portfolio.rebalance_frequency == 'monthly'
                              ? 'text-green-600'
                              : 'text-red-600'
                          }`}
                        >
                          {portfolio.rebalance_frequency == 'monthly'
                            ? '월 단위'
                            : '분기 단위'}
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

import React, { useState, useCallback, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  PieChart,
  Plus,
  Save,
  TrendingUp,
  Trash2,
  RefreshCw,
  Info
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
  PortfolioOptimizeResponse,
  PortfolioResponse
} from '../api/portfolio'
import {
  PortfolioChart,
  PortfolioWeights,
  PortfolioMetrics,
  DiscreteAllocation,
  CorrelationMatrix,
  EfficientFrontier
} from '../components/portfolio'
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

  // 최적화 결과
  const [optimizationResult, setOptimizationResult] =
    useState<PortfolioOptimizeResponse | null>(null)
  const [isOptimizing, setIsOptimizing] = useState(false)

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

  // 포트폴리오 최적화
  const handleOptimize = async () => {
    if (selectedTickers.length < 2) {
      toast.error('최소 2개 이상의 종목을 선택해주세요.')
      return
    }

    setIsOptimizing(true)
    try {
      const result = await portfolioApi.optimize({
        tickers: selectedTickers,
        optimization_method: optimizationMethod,
        investment_amount: 100000
      })
      setOptimizationResult(result)
      toast.success('포트폴리오 최적화가 완료되었습니다!')
    } catch (error: any) {
      console.error('최적화 실패:', error)
      toast.error(
        error?.response?.data?.detail || '포트폴리오 최적화에 실패했습니다.'
      )
    } finally {
      setIsOptimizing(false)
    }
  }

  // 포트폴리오 저장
  const handleSave = async () => {
    if (!optimizationResult || !portfolioName.trim()) {
      toast.error('포트폴리오 이름을 입력해주세요.')
      return
    }

    setIsSaving(true)
    try {
      await portfolioApi.create({
        name: portfolioName.trim(),
        description: portfolioDescription.trim() || undefined,
        tickers: selectedTickers,
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

    // 기존 최적화 결과 재생성
    const weights = portfolio.tickers.reduce(
      (acc, ticker, index) => {
        acc[ticker] = portfolio.weights[index]
        return acc
      },
      {} as Record<string, number>
    )

    setOptimizationResult({
      optimization: {
        weights,
        expected_annual_return: portfolio.expected_return || 0,
        annual_volatility: portfolio.volatility || 0,
        sharpe_ratio: portfolio.sharpe_ratio || 0
      },
      simulation: [], // 시뮬레이션은 다시 실행해야 함
      tickers: portfolio.tickers
    })

    toast.success(`"${portfolio.name}" 포트폴리오를 불러왔습니다.`)
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
    <div className="space-y-6">
      {/* 헤더 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl md:text-2xl font-semibold text-gray-900">
            📊 포트폴리오 최적화
          </h1>
          <p className="text-gray-600 mt-1 text-sm md:text-base">
            Modern Portfolio Theory를 기반으로 한 과학적 포트폴리오 구성
          </p>
        </div>
      </div>

      {/* 포트폴리오 설정 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="size-5" />
            포트폴리오 구성
          </CardTitle>
          <CardDescription>
            2-20개 종목을 선택하여 최적화된 포트폴리오를 생성하세요
            <br />
            <span className="text-xs text-blue-600 font-medium">
              💡 모든 방법에서 CAPM(60%) + EWMA(40%) 하이브리드 기대수익률을
              사용합니다
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

          {/* 최적화 버튼 */}
          <Button
            onClick={handleOptimize}
            disabled={selectedTickers.length < 2 || isOptimizing}
            className="w-full"
            size="lg"
          >
            {isOptimizing ? (
              <>
                <RefreshCw className="size-4 mr-2 animate-spin" />
                최적화 중...
              </>
            ) : (
              <>
                <TrendingUp className="size-4 mr-2" />
                포트폴리오 최적화
              </>
            )}
          </Button>
        </CardContent>
      </Card>

      {/* 최적화 결과 */}
      {optimizationResult && (
        <>
          {/* 포트폴리오 지표 */}
          <PortfolioMetrics optimization={optimizationResult.optimization} />

          {/* 포트폴리오 구성 */}
          <PortfolioWeights
            weights={optimizationResult.optimization.weights}
            tickers={optimizationResult.tickers}
          />

          {/* 수익률 타임라인 차트 */}
          {optimizationResult.simulation.length > 0 && (
            <PortfolioChart simulation={optimizationResult.simulation} />
          )}

          {/* 효율적 프론티어 */}
          {optimizationResult.optimization.efficient_frontier && (
            <EfficientFrontier
              efficientFrontier={
                optimizationResult.optimization.efficient_frontier
              }
              currentPortfolio={{
                expected_return:
                  optimizationResult.optimization.expected_annual_return,
                volatility: optimizationResult.optimization.annual_volatility
              }}
            />
          )}

          {/* 자산 간 상관관계 분석 */}
          {optimizationResult.optimization.correlation_matrix && (
            <CorrelationMatrix
              correlationMatrix={
                optimizationResult.optimization.correlation_matrix
              }
              tickers={optimizationResult.tickers}
            />
          )}

          {/* 실제 매수 주식 수량 계산 */}
          {optimizationResult.optimization.discrete_allocation && (
            <DiscreteAllocation
              allocation={optimizationResult.optimization.discrete_allocation}
              leftoverCash={optimizationResult.optimization.leftover_cash || 0}
              weights={optimizationResult.optimization.weights}
            />
          )}

          {/* 저장 섹션 */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Save className="size-5" />
                포트폴리오 저장
              </CardTitle>
              <CardDescription>
                최적화된 포트폴리오를 저장하여 나중에 확인할 수 있습니다
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label>포트폴리오 이름 *</Label>
                <Input
                  value={portfolioName}
                  onChange={(e) => setPortfolioName(e.target.value)}
                  placeholder="예: 안정형 배당주 포트폴리오"
                  maxLength={100}
                />
              </div>
              <div>
                <Label>설명 (선택사항)</Label>
                <Input
                  value={portfolioDescription}
                  onChange={(e) => setPortfolioDescription(e.target.value)}
                  placeholder="포트폴리오에 대한 간단한 설명을 입력하세요"
                  maxLength={500}
                />
              </div>
              <Button
                onClick={handleSave}
                disabled={!portfolioName.trim() || isSaving}
                className="w-full"
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
        </>
      )}

      {/* 저장된 포트폴리오 목록 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="flex items-center gap-2">
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
          <CardDescription>
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
              {(savedPortfolios || []).map((portfolio) => (
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
                    {new Date(portfolio.created_at).toLocaleDateString('ko-KR')}
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

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

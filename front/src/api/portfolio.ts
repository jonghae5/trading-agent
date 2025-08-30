import { apiClient } from './client'
import { EconomicEvent } from './economic'

export interface PortfolioOptimizeRequest {
  tickers: string[]
  optimization_method:
    | 'max_sharpe'
    | 'min_volatility'
    | 'efficient_frontier'
    | 'risk_parity'
  investment_amount?: number
  transaction_cost?: number
  max_position_size?: number
}

export interface EfficientFrontierPoint {
  expected_return: number
  volatility: number
  sharpe_ratio: number
}

export interface IndividualAsset {
  ticker: string
  expected_return: number
  volatility: number
}

export interface EfficientFrontierData {
  frontier_points: EfficientFrontierPoint[]
  max_sharpe_point: EfficientFrontierPoint | null
  individual_assets: IndividualAsset[]
  risk_free_rate: number
}

export interface StressScenario {
  name: string
  portfolio_return?: number
  max_drawdown?: number
  volatility?: number
  worst_day_return?: number
  probability?: string
  portfolio_impact?: number
  affected_position?: string
}

export interface WalkForwardStats {
  totalPeriods: number
  winRate: number
  totalReturn: number
  finalValue: number
  totalRebalances: number
  avgSharpe: number
  positiveReturns: number
  negativeReturns: number
}

export interface OptimizationResult {
  weights: Record<string, number>
  expected_annual_return: number
  annual_volatility: number
  sharpe_ratio: number
  sortino_ratio?: number
  max_drawdown?: number
  calmar_ratio?: number
  value_at_risk_95?: number
  discrete_allocation?: Record<string, number>
  leftover_cash?: number
  correlation_matrix?: Record<string, Record<string, number>>
  efficient_frontier?: EfficientFrontierData
  stress_scenarios?: Record<string, StressScenario>
  transaction_cost_impact?: number
  concentration_limit?: number
  // Walk-Forward Analysis specific metrics
  walkForwardStats?: WalkForwardStats
}

export interface SimulationDataPoint {
  date: string
  portfolio_value: number
  daily_return: number
  cumulative_return: number
}

export interface PortfolioOptimizeResponse {
  optimization: OptimizationResult
  simulation: SimulationDataPoint[]
  tickers: string[]
  economic_events?: EconomicEvent[]
}

export interface PortfolioResponse {
  id: number
  user_id: number
  name: string
  description?: string
  tickers: string[]
  weights: number[]
  optimization_method: string
  expected_return?: number
  volatility?: number
  sharpe_ratio?: number
  sortino_ratio?: number
  max_drawdown?: number
  calmar_ratio?: number
  value_at_risk_95?: number
  transaction_cost?: number
  max_position_size?: number
  stress_scenarios?: Record<string, StressScenario>
  correlation_matrix?: Record<string, Record<string, number>>
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PortfolioCreateRequest {
  name: string
  description?: string
  tickers: string[]
  optimization_method: string
}

export interface PortfolioSimulationResponse {
  simulation: SimulationDataPoint[]
  metrics: {
    max_drawdown?: number
    win_rate?: number
    total_return?: number
    annualized_return?: number
  }
  portfolio: PortfolioResponse
}

export interface DiscreteAllocationRequest {
  tickers: string[]
  weights: Record<string, number>
  investment_amount: number
}

export interface DiscreteAllocationResponse {
  allocation: Record<string, number>
  leftover_cash: number
  invested_amount: number
  total_portfolio_value: number
  latest_prices: Record<string, number>
}

export interface BacktestRequest {
  tickers: string[]
  optimization_method:
    | 'max_sharpe'
    | 'min_volatility'
    | 'efficient_frontier'
    | 'risk_parity'

  // Walk-Forward Analysis 파라미터
  train_window?: number // 기본값: 252 (1년)
  test_window?: number // 기본값: 21 (1개월)
  rebalance_frequency?: 'weekly' | 'monthly' | 'quarterly'

  // 공통 파라미터
  investment_amount?: number
  transaction_cost?: number
  max_position_size?: number
}

export interface BacktestResponse {
  backtest_type: 'walk_forward'
  results: any // Walk-Forward Analysis 결과 구조
  tickers: string[]
}

// Generic API response wrapper
type ApiResponse<T> = {
  success: boolean
  data: T
  message?: string
}

export const portfolioApi = {
  /**
   * 포트폴리오 최적화 수행
   */
  async optimize(
    request: PortfolioOptimizeRequest
  ): Promise<PortfolioOptimizeResponse> {
    const response: ApiResponse<PortfolioOptimizeResponse> =
      await apiClient.post('/api/v1/portfolio/optimize', request)
    if (!response.success)
      throw new Error(response.message || '포트폴리오 최적화 실패')
    return response.data
  },

  /**
   * 포트폴리오 생성 및 저장
   */
  async create(portfolio: PortfolioCreateRequest): Promise<PortfolioResponse> {
    const response: ApiResponse<PortfolioResponse> = await apiClient.post(
      '/api/v1/portfolio',
      portfolio
    )
    if (!response.success)
      throw new Error(response.message || '포트폴리오 생성 실패')
    return response.data
  },

  /**
   * 사용자 포트폴리오 목록 조회
   */
  async getUserPortfolios(): Promise<PortfolioResponse[]> {
    const response: ApiResponse<PortfolioResponse[]> =
      await apiClient.get('/api/v1/portfolio')
    if (!response.success)
      throw new Error(response.message || '포트폴리오 목록 조회 실패')
    return response.data
  },

  /**
   * 특정 포트폴리오 조회
   */
  async getPortfolio(portfolioId: number): Promise<PortfolioResponse> {
    const response: ApiResponse<PortfolioResponse> = await apiClient.get(
      `/api/v1/portfolio/${portfolioId}`
    )
    if (!response.success)
      throw new Error(response.message || '포트폴리오 조회 실패')
    return response.data
  },

  /**
   * 포트폴리오 삭제
   */
  async deletePortfolio(portfolioId: number): Promise<{ message: string }> {
    const response: ApiResponse<{ message: string }> = await apiClient.delete(
      `/api/v1/portfolio/${portfolioId}`
    )
    if (!response.success)
      throw new Error(response.message || '포트폴리오 삭제 실패')
    return response.data
  },

  /**
   * Walk-Forward Analysis 백테스팅
   */
  async backtestWalkForward(
    request: BacktestRequest
  ): Promise<BacktestResponse> {
    const response: ApiResponse<BacktestResponse> = await apiClient.post(
      '/api/v1/portfolio/backtest/walk-forward',
      request
    )
    if (!response.success)
      throw new Error(response.message || 'Walk-Forward 백테스트 실패')
    return response.data
  }
}

/**
 * Insights API client for advanced stock analysis
 */

import { apiClient } from './client'

export interface TechnicalIndicator {
  name: string
  value: number
  signal: 'bullish' | 'bearish' | 'neutral'
  strength: number
  description: string
}

export interface TechnicalAnalysisResult {
  ticker: string
  timestamp: string
  indicators: TechnicalIndicator[]
  overall_signal: string
  confidence: number
  support_levels: number[]
  resistance_levels: number[]
  trend_direction: string
  volatility: number
}

export interface ValuationMetric {
  name: string
  value: number
  fair_value_estimate?: number
  rating: 'excellent' | 'good' | 'average' | 'poor' | 'very_poor'
  description: string
}

export interface FinancialRatio {
  name: string
  value: number
  industry_avg?: number
  rating: 'excellent' | 'good' | 'average' | 'poor' | 'very_poor'
  description: string
}

export interface GrowthMetric {
  name: string
  current_value: number
  historical_avg: number
  trend: 'accelerating' | 'stable' | 'declining'
  description: string
}

export interface FundamentalAnalysisResult {
  ticker: string
  company_name: string
  timestamp: string
  current_price: number
  market_cap: number
  valuation_metrics: ValuationMetric[]
  financial_ratios: FinancialRatio[]
  growth_metrics: GrowthMetric[]
  overall_rating: 'strong_buy' | 'buy' | 'hold' | 'sell' | 'strong_sell'
  confidence: number
  fair_value: number
  upside_potential: number
  risk_factors: string[]
  strengths: string[]
}

export interface ComprehensiveInsights {
  ticker: string
  timestamp: string
  combined_signal: 'bullish' | 'bearish' | 'neutral'
  combined_confidence: number
  technical_analysis: {
    overall_signal?: string
    confidence?: number
    trend_direction?: string
    volatility?: number
    key_indicators: Array<{
      name: string
      signal: string
      strength: number
    }>
  }
  fundamental_analysis: {
    overall_rating?: string
    confidence?: number
    fair_value?: number
    upside_potential?: number
    key_strengths: string[]
    key_risks: string[]
  }
  market_context: {
    economic_indicators: any
    market_sentiment: string
  }
}

export interface EconomicData {
  gdp: any
  employment: any
  inflation: any
  rates: any
  housing?: any
}

export interface MarketContext {
  timestamp: string
  economic_indicators: any
  gdp: any
  employment: any
  inflation: any
  interest_rates: any
}

export interface PortfolioAnalysis {
  tickers: string[]
  analysis_count: number
  portfolio_metrics: {
    average_signal: number
    average_volatility: number
    diversification_score: number
    risk_level: 'low' | 'medium' | 'high'
  }
  individual_analyses: Array<{
    ticker: string
    technical_signal?: string
    fundamental_rating?: string
    volatility?: number
    upside_potential?: number
  }>
  timestamp: string
}

export interface ValueScreenerResult {
  criteria: {
    min_market_cap?: number
    max_pe_ratio?: number
    min_dividend_yield?: number
  }
  results: Array<{
    ticker: string
    company_name: string
    pe_ratio: number
    dividend_yield: number
    market_cap: number
    score: number
  }>
  total_matches: number
  timestamp: string
}

export interface StockSearchResult {
  symbol: string
  name: string
  exchange: string
  type: 'stock' | 'etf' | 'index'
  sector?: string
  industry?: string
  market_cap?: number
  currency?: string
}

export interface StockSearchResponse {
  query: string
  results: StockSearchResult[]
  count: number
}

export interface StockValidationResponse {
  ticker: string
  valid: boolean
  info?: StockSearchResult
}

export const insightsApi = {
  async getTechnicalAnalysis(
    ticker: string,
    period: string = '6mo'
  ): Promise<TechnicalAnalysisResult> {
    const response = await apiClient.get<{
      success: boolean
      data: TechnicalAnalysisResult
    }>(`/api/v1/insights/technical/${ticker}`, { period })
    return response.data
  },

  async getFundamentalAnalysis(
    ticker: string
  ): Promise<FundamentalAnalysisResult> {
    const response = await apiClient.get<{
      success: boolean
      data: FundamentalAnalysisResult
    }>(`/api/v1/insights/fundamental/${ticker}`)
    return response.data
  },

  async getComprehensiveInsights(
    ticker: string,
    period: string = '6mo'
  ): Promise<ComprehensiveInsights> {
    const response = await apiClient.get<{
      success: boolean
      data: ComprehensiveInsights
    }>(`/api/v1/insights/comprehensive/${ticker}`, { period })
    return response.data
  },

  async getEconomicSummary(): Promise<any> {
    const response = await apiClient.get<{
      success: boolean
      data: any
    }>('/api/v1/insights/economic/summary')
    return response.data
  },

  async getDetailedEconomicData(): Promise<EconomicData> {
    const response = await apiClient.get<{
      success: boolean
      data: EconomicData
    }>('/api/v1/insights/economic/detailed')
    return response.data
  },

  async getMarketContext(): Promise<MarketContext> {
    const response = await apiClient.get<{
      success: boolean
      data: MarketContext
    }>('/api/v1/insights/market/context')
    return response.data
  },

  async screenValueStocks(params?: {
    min_market_cap?: number
    max_pe_ratio?: number
    min_dividend_yield?: number
  }): Promise<ValueScreenerResult> {
    const response = await apiClient.get<{
      success: boolean
      data: ValueScreenerResult
    }>('/api/v1/insights/screener/value', params)
    return response.data
  },

  async analyzePortfolio(tickers: string[]): Promise<PortfolioAnalysis> {
    const tickerString = tickers.join(',')
    const response = await apiClient.get<{
      success: boolean
      data: PortfolioAnalysis
    }>('/api/v1/insights/portfolio/analysis', { tickers: tickerString })
    return response.data
  },

  async searchStocks(
    query: string,
    limit: number = 10
  ): Promise<StockSearchResponse> {
    const response = await apiClient.get<{
      success: boolean
      data: StockSearchResponse
    }>('/api/v1/insights/search/stocks', { q: query, limit })
    return response.data
  },

  async validateTicker(ticker: string): Promise<StockValidationResponse> {
    const response = await apiClient.get<{
      success: boolean
      data: StockValidationResponse
    }>(`/api/v1/insights/search/validate/${ticker}`)
    return response.data
  },

  async getPopularStocks(
    limit: number = 20
  ): Promise<{ results: StockSearchResult[]; count: number }> {
    const response = await apiClient.get<{
      success: boolean
      data: { results: StockSearchResult[]; count: number }
    }>('/api/v1/insights/search/popular', { limit })
    return response.data
  }
}

// Helper functions for analysis results
export const getSignalColor = (signal: string): string => {
  switch (signal.toLowerCase()) {
    case 'bullish':
    case 'strong_buy':
    case 'buy':
      return '#10b981' // green
    case 'bearish':
    case 'strong_sell':
    case 'sell':
      return '#ef4444' // red
    case 'neutral':
    case 'hold':
    default:
      return '#f59e0b' // amber
  }
}

export const getRatingColor = (rating: string): string => {
  switch (rating) {
    case 'excellent':
      return '#059669' // emerald
    case 'good':
      return '#10b981' // green
    case 'average':
      return '#f59e0b' // amber
    case 'poor':
      return '#ea580c' // orange
    case 'very_poor':
      return '#dc2626' // red
    default:
      return '#6b7280' // gray
  }
}

export const formatCurrency = (value: number, decimals: number = 2): string => {
  if (value >= 1e9) {
    return `$${(value / 1e9).toFixed(decimals)}B`
  } else if (value >= 1e6) {
    return `$${(value / 1e6).toFixed(decimals)}M`
  } else if (value >= 1e3) {
    return `$${(value / 1e3).toFixed(decimals)}K`
  } else {
    return `$${value.toFixed(decimals)}`
  }
}

export const formatPercentage = (
  value: number,
  decimals: number = 1
): string => {
  return `${value >= 0 ? '+' : ''}${value.toFixed(decimals)}%`
}

export const formatNumber = (value: number, decimals: number = 2): string => {
  return value.toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

/**
 * Insights API client for advanced stock analysis
 */

import { apiClient } from './client'

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

export interface RecommendationTrend {
  buy: number
  hold: number
  period: string
  sell: number
  strongBuy: number
  strongSell: number
  symbol: string
}

export interface EarningSurprise {
  actual: number
  estimate: number
  period: string
  quarter: number
  surprise: number
  surprisePercent: number
  symbol: string
  year: number
}

export const stocksApi = {
  async searchStocks(
    query: string,
    limit: number = 10
  ): Promise<StockSearchResponse> {
    const response = await apiClient.get<{
      success: boolean
      data: StockSearchResponse
    }>('/api/v1/stocks/search/stocks', { q: query, limit })
    return response.data
  },

  async getRecommendationTrends(
    symbol: string
  ): Promise<RecommendationTrend[]> {
    const response = await apiClient.get<{
      success: boolean
      data: { symbol: string; trends: RecommendationTrend[] }
    }>(`/api/v1/stocks/recommendation-trends/${symbol}`)
    return response.data.trends
  },

  async getEarningSurprises(
    symbol: string,
    limit?: number
  ): Promise<EarningSurprise[]> {
    const params = limit ? { limit } : {}
    const response = await apiClient.get<{
      success: boolean
      data: { symbol: string; surprises: EarningSurprise[] }
    }>(`/api/v1/stocks/earnings-surprises/${symbol}`, params)
    return response.data.surprises
  }
}

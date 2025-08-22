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
  }
}

/**
 * API client configuration and utilities
 */

import { API_BASE_URL } from '../lib/constants'
import type { ErrorData, StockSearchResult } from '../types'

export interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data?: T
  error?: string
  status_code?: number
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public data?: ErrorData
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

class ApiClient {
  private baseURL: string
  private isRefreshing: boolean = false
  private refreshPromise: Promise<boolean> | null = null

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL.replace(/\/$/, '') // Remove trailing slash
  }

  // 쿠키 방식에서는 토큰을 직접 관리하지 않음
  setToken(token: string) {
    // No-op for cookie-based auth
  }

  clearToken() {
    // No-op for cookie-based auth
  }

  // 토큰 갱신 함수
  private async refreshToken(): Promise<boolean> {
    if (this.isRefreshing) {
      return this.refreshPromise || Promise.resolve(false)
    }

    this.isRefreshing = true
    this.refreshPromise = this.performTokenRefresh()

    try {
      const result = await this.refreshPromise
      return result
    } finally {
      this.isRefreshing = false
      this.refreshPromise = null
    }
  }

  private async performTokenRefresh(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseURL}/api/v1/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json'
        }
      })

      if (response.ok) {
        return true
      } else {
        // 리프레시 토큰도 만료된 경우 로그인 페이지로 리다이렉트
        window.location.href = '/login'
        return false
      }
    } catch (error) {
      console.error('Token refresh failed:', error)
      window.location.href = '/login'
      return false
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {},
    isRetry: boolean = false
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`

    const config: RequestInit = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers
      },
      credentials: 'include', // 쿠키를 포함하여 요청
      mode: 'cors',
      ...options
    }

    try {
      const response = await fetch(url, config)

      // 401 에러이고 재시도가 아닌 경우 토큰 갱신 시도
      if (response.status === 401 && !isRetry && !endpoint.includes('/auth/')) {
        const refreshSuccess = await this.refreshToken()
        if (refreshSuccess) {
          // 토큰 갱신 성공 시 원래 요청 재시도
          return this.request<T>(endpoint, options, true)
        }
      }

      if (!response.ok) {
        let errorData: ErrorData
        try {
          errorData = await response.json()
        } catch {
          errorData = { message: response.statusText }
        }

        throw new ApiError(
          response.status,
          errorData.message || errorData.detail || 'Request failed',
          errorData
        )
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      } else {
        return {} as T
      }
    } catch (error) {
      if (error instanceof ApiError) {
        throw error
      }

      // Network or other errors
      throw new ApiError(
        0,
        error instanceof Error ? error.message : 'Network error',
        { originalError: error }
      )
    }
  }

  // HTTP methods
  async get<T>(endpoint: string, params?: Record<string, unknown>): Promise<T> {
    let url = endpoint
    if (params) {
      const searchParams = new URLSearchParams()
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          searchParams.append(key, String(value))
        }
      })
      const queryString = searchParams.toString()
      if (queryString) {
        url += `?${queryString}`
      }
    }

    return this.request<T>(url, { method: 'GET' })
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async patch<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined
    })
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: 'DELETE' })
  }
}

// Global API client instance
export const apiClient = new ApiClient()

// Helper function to handle API responses
export function handleApiResponse<T>(response: ApiResponse<T>): T {
  if (!response.success) {
    throw new Error(response.message || 'API request failed')
  }
  return response.data as T
}

// Fear & Greed Index API functions
export interface FearGreedIndexData {
  value: number
  classification: string
  timestamp: string
  previous_close?: number
  one_week_ago?: number
  one_month_ago?: number
  one_year_ago?: number
}

export interface FearGreedHistoricalPoint {
  date: string
  value: number
  classification: string
}

export interface FearGreedHistoricalData {
  data: FearGreedHistoricalPoint[]
  period_days: number
  start_date: string
  end_date: string
  total_points: number
}

export interface FearGreedSummarySummary {
  current: FearGreedIndexData
  trend: 'improving' | 'declining' | 'neutral'
  volatility: 'low' | 'medium' | 'high'
  historical_comparison: {
    previous_close?: number
    one_week_ago?: number
    one_month_ago?: number
    one_year_ago?: number
  }
  recent_history: FearGreedHistoricalPoint[]
}

export interface AdvancedSentimentAnalysis {
  fear_greed_index: FearGreedIndexData
  social_sentiment?: {
    twitter_sentiment: number
    reddit_sentiment: number
    social_volume: string
    trending_topics: string[]
  }
  news_sentiment?: {
    overall_sentiment: number
    positive_articles: number
    negative_articles: number
    neutral_articles: number
    key_themes: string[]
  }
  options_sentiment?: {
    put_call_ratio: number
    vix_level: number
    options_flow: string
    gamma_exposure: string
  }
  combined_sentiment_score: number
  confidence_level: number
  timestamp: string
}

// Stock Quote API functions
export interface StockQuoteData {
  ticker: string
  company_name: string
  price: number
  change: number
  change_percent: number
  volume: number
  day_low: number | null
  day_high: number | null
  week_52_low: number | null
  week_52_high: number | null
  previous_close: number
  market_cap: number | null
  pe_ratio: number | null
  timestamp: string
  source?: string
}

export interface ChartDataPoint {
  timestamp: string
  price: number
  volume: number
}

// Fear & Greed Index API methods
export const fearGreedApi = {
  // Get historical Fear & Greed Index data
  async getHistory(
    days: number = 30,
    aggregation: string = 'daily'
  ): Promise<FearGreedHistoricalData> {
    const response = await apiClient.get<ApiResponse<FearGreedHistoricalData>>(
      '/api/v1/fear-greed/history',
      { days, aggregation }
    )
    return handleApiResponse(response)
  },

  // Get comprehensive market sentiment summary
  async getSummary(): Promise<FearGreedSummarySummary> {
    const response = await apiClient.get<ApiResponse<FearGreedSummarySummary>>(
      '/api/v1/fear-greed/summary'
    )

    console.log('response', response)
    return handleApiResponse(response)
  }
}

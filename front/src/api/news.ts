/**
 * News API service for Fred API integration
 */

import { apiClient, handleApiResponse, type ApiResponse } from './client'
import type {
  NewsArticle,
  NewsSearchFilters,
  NewsSearchResult,
  FredNewsResponse
} from '../types'

export interface NewsApiService {
  // Get categorized news from Fred API
  getCategorizedNews(): Promise<{
    latest: NewsArticle[]
  }>

  // Search news with filters
  searchNews(filters: NewsSearchFilters): Promise<NewsSearchResult>

  // Get news by sentiment
  getNewsBySentiment(
    sentiment: 'positive' | 'negative' | 'latest'
  ): Promise<NewsArticle[]>
}

class NewsApi implements NewsApiService {
  /**
   * Fetch categorized news from Fred API
   */
  async getCategorizedNews() {
    try {
      const response = await apiClient.get<FredNewsResponse>(
        '/api/v1/news/categorized'
      )

      if (!response.success || !response.data) {
        throw new Error(response.message || 'Failed to fetch news')
      }

      return {
        latest: response.data.latest_news || []
      }
    } catch (error) {
      console.error('Error fetching categorized news:', error)
      throw error // Re-throw to be handled by caller
    }
  }

  /**
   * Search news with filters
   */
  async searchNews(filters: NewsSearchFilters): Promise<NewsSearchResult> {
    try {
      const searchParams: Record<string, unknown> = {}

      if (filters.query) searchParams.query = filters.query
      if (filters.sentiment && filters.sentiment !== 'all') {
        searchParams.sentiment = filters.sentiment
      }
      if (filters.source) searchParams.source = filters.source
      if (filters.dateFrom) searchParams.date_from = filters.dateFrom
      if (filters.dateTo) searchParams.date_to = filters.dateTo
      if (filters.limit) searchParams.limit = filters.limit

      const response = await apiClient.get<ApiResponse<NewsSearchResult>>(
        '/api/v1/news/search',
        searchParams
      )

      return handleApiResponse(response)
    } catch (error) {
      console.error('Error searching news:', error)
      return {
        articles: [],
        total: 0,
        hasMore: false,
        searchQuery: filters.query
      }
    }
  }

  /**
   * Get news by specific sentiment category
   */
  async getNewsBySentiment(
    sentiment: 'positive' | 'negative' | 'latest'
  ): Promise<NewsArticle[]> {
    try {
      const response = await apiClient.get<ApiResponse<NewsArticle[]>>(
        `/api/v1/news/${sentiment}`
      )

      return handleApiResponse(response)
    } catch (error) {
      console.error(`Error fetching ${sentiment} news:`, error)
      return []
    }
  }
}

// Export singleton instance
export const newsApi = new NewsApi()

// Export convenience functions
export const fetchNewsByCategory = async (
  category: 'latest' | 'positive' | 'negative'
): Promise<NewsArticle[]> => {
  try {
    const categorizedNews = await newsApi.getCategorizedNews()
    console.log('오종해', categorizedNews)
    return categorizedNews[category]
  } catch (error) {
    console.error(`Failed to fetch ${category} news:`, error)
    // Return mock data as fallback
    return mockNewsData[category]
  }
}

export const searchNews = async (
  filters: NewsSearchFilters
): Promise<NewsSearchResult> => {
  try {
    return await newsApi.searchNews(filters)
  } catch (error) {
    console.error('Failed to search news:', error)
    // Return filtered mock data as fallback
    const allMockArticles = [
      ...mockNewsData.latest,
      ...mockNewsData.positive,
      ...mockNewsData.negative
    ]

    let filtered = allMockArticles

    if (filters.query) {
      const query = filters.query.toLowerCase()
      filtered = filtered.filter(
        (article) =>
          article.title.toLowerCase().includes(query) ||
          (article.summary && article.summary.toLowerCase().includes(query))
      )
    }

    if (filters.sentiment && filters.sentiment !== 'all') {
      filtered = filtered.filter(
        (article) => article.sentiment === filters.sentiment
      )
    }

    return {
      articles: filtered,
      total: filtered.length,
      hasMore: false,
      searchQuery: filters.query
    }
  }
}

// Mock data for development (fallback when Fred API is unavailable)
export const mockNewsData = {
  positive: [
    {
      id: 'pos-1',
      title: 'Market Rally Continues as Tech Stocks Surge',
      summary:
        "Major technology stocks showed strong performance in today's trading session, driving broader market gains.",
      sentiment: 'positive' as const,
      source: 'Financial Times',
      publishedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      relevanceScore: 0.85,
      tags: ['technology', 'market', 'stocks']
    },
    {
      id: 'pos-2',
      title: 'Federal Reserve Signals Optimistic Economic Outlook',
      summary:
        'Fed officials express confidence in economic recovery and stable inflation expectations.',
      sentiment: 'positive' as const,
      source: 'Reuters',
      publishedAt: new Date(Date.now() - 4 * 60 * 60 * 1000).toISOString(), // 4 hours ago
      relevanceScore: 0.92,
      tags: ['federal reserve', 'economy', 'inflation']
    }
  ],
  negative: [
    {
      id: 'neg-1',
      title: 'Energy Sector Faces Headwinds as Oil Prices Decline',
      summary:
        'Crude oil prices dropped significantly amid concerns over global demand and supply chain issues.',
      sentiment: 'negative' as const,
      source: 'Bloomberg',
      publishedAt: new Date(Date.now() - 3 * 60 * 60 * 1000).toISOString(), // 3 hours ago
      relevanceScore: 0.78,
      tags: ['energy', 'oil', 'commodities']
    },
    {
      id: 'neg-2',
      title: 'Manufacturing Data Shows Unexpected Weakness',
      summary:
        'Latest manufacturing indices indicate slower growth than anticipated, raising economic concerns.',
      sentiment: 'negative' as const,
      source: 'Wall Street Journal',
      publishedAt: new Date(Date.now() - 5 * 60 * 60 * 1000).toISOString(), // 5 hours ago
      relevanceScore: 0.83,
      tags: ['manufacturing', 'economy', 'data']
    }
  ],
  latest: [
    {
      id: 'latest-1',
      title: 'Breaking: Central Bank Announces Interest Rate Decision',
      summary:
        'The central bank maintains current interest rates while monitoring inflation trends closely.',
      sentiment: 'neutral' as const,
      source: 'CNBC',
      publishedAt: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 minutes ago
      relevanceScore: 0.95,
      tags: ['central bank', 'interest rates', 'monetary policy']
    },
    {
      id: 'latest-2',
      title: 'Quarterly Earnings Season Kicks Off with Mixed Results',
      summary:
        'Companies report varied quarterly performance as investors assess market conditions.',
      sentiment: 'neutral' as const,
      source: 'MarketWatch',
      publishedAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), // 1 hour ago
      relevanceScore: 0.87,
      tags: ['earnings', 'quarterly results', 'companies']
    }
  ]
}

/**
 * Economic indicators API client for FRED data
 */

import { apiClient } from './client'
import { getKSTDate, newKSTDate } from '../lib/utils'

export interface EconomicObservation {
  date: string
  value: number
}

export interface EconomicEvent {
  date: string // Chart positioning date (1st of month)
  detail_date: string // Exact date for tooltips and precise positioning
  title: string
  description: string
  type:
    | 'crisis'
    | 'recession'
    | 'policy_change'
    | 'market_event'
    | 'geopolitical'
    | 'pandemic'
  severity: 'low' | 'medium' | 'high' | 'critical'
  color: string
  icon: string
  impact_duration_months?: number
  related_indicators: string[]
  priority: number
}

export interface HistoricalDataResponse {
  date_range: {
    start: string
    end: string
    duration_days: number
  }
  indicators: Record<string, EconomicObservation[]>
  events: EconomicEvent[]
  metadata: {
    indicators_count: number
    events_count: number
    data_points_total: number
  }
}

export interface EconomicEventsResponse {
  events: EconomicEvent[]
  metadata: {
    total_events: number
    date_range: {
      start?: string
      end?: string
    }
    filters: {
      indicator?: string
      event_types?: string[]
      min_severity?: string
    }
  }
  available_filters: {
    event_types: string[]
    severity_levels: string[]
  }
}

export interface SeriesInfo {
  id: string
  title: string
  frequency: string
  units: string
  seasonal_adjustment: string
  last_updated: string
  notes?: string
}

export interface SeriesDataResponse {
  series_info: SeriesInfo
  observations: EconomicObservation[]
  count: number
}

export interface EconomicSummary {
  [indicator: string]: {
    value: number
    date: string
    series_id: string
  } | null
}

// API endpoints
export const economicApi = {
  /**
   * Get historical data for multiple indicators with optional date range
   */
  async getHistoricalData(params: {
    indicators: string[]
    startDate: string
    endDate?: string
    includeEvents?: boolean
    eventTypes?: string[]
    minSeverity?: 'low' | 'medium' | 'high' | 'critical'
  }): Promise<HistoricalDataResponse> {
    const queryParams = new URLSearchParams({
      indicators: params.indicators.join(','),
      start_date: params.startDate,
      include_events: (params.includeEvents ?? true).toString()
    })

    if (params.endDate) {
      queryParams.append('end_date', params.endDate)
    }

    if (params.eventTypes && params.eventTypes.length > 0) {
      queryParams.append('event_types', params.eventTypes.join(','))
    }

    if (params.minSeverity) {
      queryParams.append('min_severity', params.minSeverity)
    }

    const response = await apiClient.get<{ data: HistoricalDataResponse }>(
      `/api/v1/economic/historical?${queryParams.toString()}`
    )
    return response.data
  },

  /**
   * Get economic events and crisis markers
   */
  async getEconomicEvents(params?: {
    startDate?: string
    endDate?: string
    eventTypes?: string[]
    minSeverity?: string
    indicator?: string
  }): Promise<EconomicEventsResponse> {
    const queryParams = new URLSearchParams()

    if (params?.startDate) {
      queryParams.append('start_date', params.startDate)
    }

    if (params?.endDate) {
      queryParams.append('end_date', params.endDate)
    }

    if (params?.eventTypes && params.eventTypes.length > 0) {
      queryParams.append('event_types', params.eventTypes.join(','))
    }

    if (params?.minSeverity) {
      queryParams.append('min_severity', params.minSeverity)
    }

    if (params?.indicator) {
      queryParams.append('indicator', params.indicator)
    }

    const url = queryParams.toString()
      ? `/api/v1/economic/events?${queryParams.toString()}`
      : '/api/v1/economic/events'

    const response = await apiClient.get<{ data: EconomicEventsResponse }>(url)
    return response.data
  }
}

// Utility functions for date handling
export const economicUtils = {
  /**
   * Get date string for N years ago
   */
  getDateYearsAgo(years: number): string {
    const date = getKSTDate()
    date.setFullYear(date.getFullYear() - years)
    return date.toISOString().split('T')[0]
  },

  /**
   * Get date string for N months ago
   */
  getDateMonthsAgo(months: number): string {
    const date = getKSTDate()
    date.setMonth(date.getMonth() - months)
    return date.toISOString().split('T')[0]
  },

  /**
   * Format date for display
   */
  formatDate(dateString: string): string {
    return newKSTDate(dateString).toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  },

  /**
   * Get preset date ranges
   */
  getPresetRanges() {
    const today = getKSTDate().toISOString().split('T')[0]

    return {
      '1Y': {
        label: '1년',
        startDate: this.getDateYearsAgo(1),
        endDate: today
      },
      '5Y': {
        label: '5년',
        startDate: this.getDateYearsAgo(5),
        endDate: today
      },
      '10Y': {
        label: '10년',
        startDate: this.getDateYearsAgo(10),
        endDate: today
      },
      '20Y': {
        label: '20년',
        startDate: this.getDateYearsAgo(20),
        endDate: today
      }
    }
  },

  /**
   * Aggregate data to monthly intervals for long-term periods
   */
  aggregateToMonthly(
    observations: EconomicObservation[]
  ): EconomicObservation[] {
    if (observations.length === 0) return []

    const monthlyData: Record<string, EconomicObservation[]> = {}

    // Group observations by year-month
    observations.forEach((obs) => {
      const date = newKSTDate(obs.date)
      const monthKey = `${date.getFullYear()}-${String(
        date.getMonth() + 1
      ).padStart(2, '0')}`

      if (!monthlyData[monthKey]) {
        monthlyData[monthKey] = []
      }
      monthlyData[monthKey].push(obs)
    })

    // Calculate monthly averages/end-of-month values
    return Object.keys(monthlyData)
      .sort()
      .map((monthKey) => {
        const monthObs = monthlyData[monthKey]
        // Use the last observation of the month (most common for economic data)
        const lastObs = monthObs[monthObs.length - 1]

        return {
          date: `${monthKey}-01`, // Normalize to first of month for display
          value: lastObs.value
        }
      })
  },

  /**
   * Determine if data should be aggregated based on time range
   */
  shouldAggregateData(startDate: string, endDate: string): boolean {
    const start = newKSTDate(startDate)
    const end = newKSTDate(endDate)
    const yearsDiff =
      (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24 * 365.25)

    // Aggregate for periods longer than 5 years
    return yearsDiff > 5
  }
}

// Common indicator groups - aligned with frontend categories (merged)
export const IndicatorGroups = {
  GROWTH_EMPLOYMENT: ['GDP', 'INDPRO', 'TCU', 'UNRATE', 'PAYEMS', 'ICSA'],
  INFLATION_MONETARY: [
    'CPIAUCSL',
    'PCEPILFE',
    'T5YIE',
    'FEDFUNDS',
    'DGS10',
    'DGS2',
    'T10Y2Y'
  ],
  FINANCIAL_RISK: ['NFCI', 'BAMLH0A0HYM2', 'BAA', 'VIXCLS', 'UMCSENT'],
  REALESTATE_DEBT: [
    'MORTGAGE30US',
    'NYUCSFRCONDOSMSAMID',
    'GFDEBTN',
    'GFDEGDQ188S',
    'NCBDBIQ027S'
  ],
  FISCAL_GLOBAL: ['FYFSGDA188S', 'DTWEXBGS', 'DGS30']
} as const

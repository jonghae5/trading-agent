import React, { useState, useCallback, useRef } from 'react'
import { Search } from 'lucide-react'
import { cn } from '../../lib/utils'
import { StockAutocomplete, StockSearchResult } from '../ui/stock-autocomplete'

interface NewsSearchProps {
  onSearch: (filters: { query?: string; limit?: number }) => void
  isLoading?: boolean
  className?: string
}

function useDebouncedCallback<T extends (...args: any[]) => void>(
  callback: T,
  delay: number
) {
  const timeoutRef = useRef<NodeJS.Timeout | null>(null)
  return useCallback(
    (...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
      timeoutRef.current = setTimeout(() => {
        callback(...args)
      }, delay)
    },
    [callback, delay]
  )
}

export const NewsSearch: React.FC<NewsSearchProps> = ({
  onSearch,
  isLoading = false,
  className
}) => {
  const [query, setQuery] = useState('')

  // Load default news on mount
  React.useEffect(() => {
    onSearch({ limit: 20 })
  }, [onSearch])

  const handleStockSelect = useCallback((stock: StockSearchResult) => {
    setQuery(stock.symbol)
  }, [])

  // 디바운스된 검색 함수 (버튼 클릭용)
  const debouncedHandleSearch = useDebouncedCallback(() => {
    onSearch({ query: query.trim() || undefined, limit: 20 })
  }, 400)

  // 즉시 검색 (엔터키 등)
  const handleSearch = useCallback(() => {
    onSearch({ query: query.trim() || undefined, limit: 20 })
  }, [query, onSearch])

  const handleKeyPress = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') {
        handleSearch()
      }
    },
    [handleSearch]
  )

  return (
    <div className={cn('space-y-3', className)}>
      <div className="flex gap-2">
        <div className="flex-1">
          <StockAutocomplete
            value={query}
            onChange={setQuery}
            onSelect={handleStockSelect}
            onKeyDown={handleKeyPress}
            placeholder="뉴스 검색 (종목명 또는 티커)..."
            disabled={isLoading}
            showPopularStocks={true}
            className="w-full"
          />
        </div>

        <button
          onClick={debouncedHandleSearch}
          disabled={isLoading}
          className="px-4 py-2 bg-blue-600 text-white rounded-md text-sm font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors duration-200 flex items-center gap-2"
        >
          {isLoading ? (
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          ) : (
            <Search className="h-4 w-4" />
          )}
          검색
        </button>
      </div>
    </div>
  )
}

export default NewsSearch

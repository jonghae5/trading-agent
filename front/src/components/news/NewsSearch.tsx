import React, { useState, useCallback } from 'react'
import { Search, X } from 'lucide-react'

import { Input } from '../ui/input'
import { cn } from '../../lib/utils'
import { useDebounce } from '../../hooks/useDebounce'
import { motion } from 'framer-motion'

interface NewsSearchProps {
  onSearch: (filters: { query?: string; limit?: number }) => void
  isLoading?: boolean
  className?: string
}

export const NewsSearch: React.FC<NewsSearchProps> = ({
  onSearch,
  isLoading = false,
  className
}) => {
  const [query, setQuery] = useState('')

  // Debounce search query to avoid excessive API calls
  const debouncedQuery = useDebounce(query, 1500)

  // Trigger search when query changes
  React.useEffect(() => {
    onSearch({ query: debouncedQuery || undefined, limit: 20 })
  }, [debouncedQuery, onSearch])

  const handleQueryChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      setQuery(e.target.value)
    },
    []
  )

  const handleClearSearch = useCallback(() => {
    setQuery('')
  }, [])

  return (
    <div className={cn('space-y-3', className)}>
      {/* Search Input */}
      <div className="relative">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <Input
            type="text"
            placeholder="뉴스 검색..."
            value={query}
            onChange={handleQueryChange}
            className="pl-10 pr-16 sm:pr-20 text-sm sm:text-base"
            disabled={isLoading}
          />

          {/* Action buttons */}
          <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-0.5 sm:gap-1">
            {query && (
              <motion.button
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                exit={{ scale: 0 }}
                onClick={handleClearSearch}
                className="rounded-full p-1.5 sm:p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                title="Clear search"
              >
                <X className="h-3 w-3" />
              </motion.button>
            )}
          </div>
        </div>

        {/* Loading indicator */}
        {isLoading && (
          <div className="absolute right-10 sm:right-12 top-1/2 -translate-y-1/2">
            <div className="h-4 w-4 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          </div>
        )}
      </div>

      {/* Quick Search Suggestions */}
      {!query && (
        <div className="flex flex-wrap gap-1 sm:gap-2">
          {['AAPL', 'SPY', 'TSLA', 'SOXL'].map((suggestion) => (
            <button
              key={suggestion}
              onClick={() => setQuery(suggestion)}
              className="rounded-full bg-gray-100 px-2 sm:px-3 py-1 text-xs text-gray-600 transition-colors hover:bg-gray-200 hover:text-gray-800"
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default NewsSearch

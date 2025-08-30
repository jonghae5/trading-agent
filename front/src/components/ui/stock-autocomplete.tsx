/**
 * Stock Autocomplete Component
 * Provides real-time search and autocomplete functionality for stock tickers
 */

import React, { useState, useEffect, useRef, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, TrendingUp, Building2, Zap, X } from 'lucide-react'
import { stocksApi } from '../../api/stocks'
import { debounce } from '../../utils/debounce'

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

interface StockAutocompleteProps {
  value: string
  onChange: (value: string) => void
  onSelect?: (stock: StockSearchResult) => void
  onKeyDown?: (e: React.KeyboardEvent) => void
  placeholder?: string
  className?: string
  disabled?: boolean
  error?: boolean
  // showPopularStocks?: boolean   // 삭제 또는 무시
}

export const StockAutocomplete: React.FC<StockAutocompleteProps> = ({
  value,
  onChange,
  onSelect,
  onKeyDown,
  placeholder = 'Search stocks...',
  className = '',
  disabled = false,
  error = false
  // showPopularStocks = true   // 삭제 또는 무시
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const [results, setResults] = useState<StockSearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedIndex, setSelectedIndex] = useState(-1)
  // const [popularStocks, setPopularStocks] = useState<StockSearchResult[]>([]) // 삭제

  const inputRef = useRef<HTMLInputElement>(null)
  const dropdownRef = useRef<HTMLDivElement>(null)
  const resultsRef = useRef<HTMLDivElement>(null)

  // Debounced search function
  const debouncedSearch = useCallback(
    debounce(async (query: string) => {
      if (!query.trim()) {
        setResults([])
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        const response = await stocksApi.searchStocks(query.trim(), 10)
        setResults(response.results || [])
      } catch (error) {
        console.error('Stock search failed:', error)
        setResults([])
      } finally {
        setLoading(false)
      }
    }, 300),
    []
  )

  // popularStocks 관련 코드 제거
  // useEffect(() => {
  //   if (showPopularStocks) {
  //     const loadPopularStocks = async () => {
  //       try {
  //         const response = await stocksApi.getPopularStocks(20)
  //         setPopularStocks(response.results || [])
  //       } catch (error) {
  //         console.error('Failed to load popular stocks:', error)
  //       }
  //     }
  //     loadPopularStocks()
  //   }
  // }, [showPopularStocks])

  // Handle search when value changes
  useEffect(() => {
    if (isOpen) {
      debouncedSearch(value)
    }
  }, [value, isOpen, debouncedSearch])

  // Handle input change
  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const newValue = e.target.value
      onChange(newValue)
      setSelectedIndex(-1)

      if (!isOpen && newValue.trim()) {
        setIsOpen(true)
      }
    },
    [onChange, isOpen]
  )

  // Handle input focus
  const handleInputFocus = useCallback(() => {
    setIsOpen(true)
    // popularStocks 관련 코드 제거
    // if (!value.trim() && showPopularStocks && popularStocks.length > 0) {
    //   setResults(popularStocks.slice(0, 8))
    // }
    if (!value || !value.trim()) {
      setResults([])
    }
  }, [value])

  // Handle stock selection
  const handleStockSelect = useCallback(
    (stock: StockSearchResult) => {
      onChange(stock.symbol)
      setIsOpen(false)
      setSelectedIndex(-1)
      onSelect?.(stock)
      inputRef.current?.blur()
    },
    [onChange, onSelect]
  )

  // Handle keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!isOpen || results.length === 0) {
        // If dropdown is not open or no results, pass the event to parent
        onKeyDown?.(e)
        return
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault()
          setSelectedIndex((prev) => (prev < results.length - 1 ? prev + 1 : 0))
          break
        case 'ArrowUp':
          e.preventDefault()
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : results.length - 1))
          break
        case 'Enter':
          e.preventDefault()
          if (selectedIndex >= 0 && selectedIndex < results.length) {
            handleStockSelect(results[selectedIndex])
          } else {
            // If no item selected, pass Enter to parent
            onKeyDown?.(e)
          }
          break
        case 'Escape':
          setIsOpen(false)
          setSelectedIndex(-1)
          inputRef.current?.blur()
          break
        default:
          // Pass other keys to parent
          onKeyDown?.(e)
          break
      }
    },
    [isOpen, results.length, selectedIndex, handleStockSelect, onKeyDown]
  )

  // Handle click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        inputRef.current &&
        !inputRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false)
        setSelectedIndex(-1)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // Scroll selected item into view
  useEffect(() => {
    if (selectedIndex >= 0 && resultsRef.current) {
      const selectedElement = resultsRef.current.children[
        selectedIndex
      ] as HTMLElement
      if (selectedElement) {
        selectedElement.scrollIntoView({
          behavior: 'smooth',
          block: 'nearest'
        })
      }
    }
  }, [selectedIndex])

  // Get icon for stock type
  const getStockIcon = (type: string, sector?: string) => {
    if (type === 'etf') return <Zap className="size-4 text-purple-500" />
    if (sector === 'Technology')
      return <TrendingUp className="size-4 text-blue-500" />
    return <Building2 className="size-4 text-gray-500" />
  }

  // Format market cap
  const formatMarketCap = (marketCap?: number) => {
    if (!marketCap) return null
    if (marketCap >= 1e12) return `$${(marketCap / 1e12).toFixed(1)}T`
    if (marketCap >= 1e9) return `$${(marketCap / 1e9).toFixed(1)}B`
    if (marketCap >= 1e6) return `$${(marketCap / 1e6).toFixed(1)}M`
    return `$${marketCap.toLocaleString()}`
  }

  const clearInput = () => {
    onChange('')
    setIsOpen(false)
    setSelectedIndex(-1)
    inputRef.current?.focus()
  }

  return (
    <div className={`relative w-full ${className}`}>
      {/* Input Field */}
      <div className="relative">
        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <Search className="size-4 text-gray-400" />
        </div>

        <input
          ref={inputRef}
          type="text"
          value={value}
          onChange={handleInputChange}
          onFocus={handleInputFocus}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          autoComplete="off"
          spellCheck="false"
          className={`
            w-full pl-10 pr-10 py-2 border rounded-md text-sm
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            ${
              error
                ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                : 'border-gray-300'
            }
            ${disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'}
            transition-colors duration-200
          `}
        />

        {/* Clear Button */}
        {value && !disabled && (
          <button
            onClick={clearInput}
            className="absolute inset-y-0 right-0 pr-3 flex items-center hover:text-gray-600"
            type="button"
          >
            <X className="size-4 text-gray-400" />
          </button>
        )}
      </div>

      {/* Dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            ref={dropdownRef}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-96 overflow-hidden"
          >
            {loading ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <div className="animate-spin rounded-full h-6 w-6 border-2 border-blue-500 border-t-transparent mx-auto"></div>
                <p className="mt-2 text-sm">Searching...</p>
              </div>
            ) : results.length > 0 ? (
              <>
                {/* Results Header */}
                {/* popularStocks 관련 헤더 제거 */}
                {/* Results List */}
                <div ref={resultsRef} className="max-h-80 overflow-y-auto">
                  {results.map((stock, index) => (
                    <motion.div
                      key={`${stock.symbol}-${index}`}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: index * 0.05 }}
                      className={`
                        px-4 py-3 cursor-pointer border-b border-gray-100 last:border-b-0
                        transition-colors duration-150
                        ${
                          selectedIndex === index
                            ? 'bg-blue-50 border-blue-200'
                            : 'hover:bg-gray-50'
                        }
                      `}
                      onClick={() => handleStockSelect(stock)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 flex-1 min-w-0">
                          {getStockIcon(stock.type, stock.sector)}

                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2">
                              <span className="font-semibold text-gray-900 text-sm">
                                {stock.symbol}
                              </span>
                              <span className="text-xs px-1.5 py-0.5 bg-gray-200 text-gray-600 rounded">
                                {stock.exchange}
                              </span>
                              {stock.type === 'etf' && (
                                <span className="text-xs px-1.5 py-0.5 bg-purple-100 text-purple-700 rounded">
                                  ETF
                                </span>
                              )}
                            </div>

                            <p className="text-sm text-gray-600 truncate">
                              {stock.name}
                            </p>

                            {stock.sector && (
                              <p className="text-xs text-gray-500">
                                {stock.sector}
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Market Cap */}
                        {stock.market_cap && (
                          <div className="text-xs text-gray-500 ml-2">
                            {formatMarketCap(stock.market_cap)}
                          </div>
                        )}
                      </div>
                    </motion.div>
                  ))}
                </div>
              </>
            ) : value && value.trim() && !loading ? (
              <div className="px-4 py-8 text-center text-gray-500">
                <Search className="size-8 text-gray-300 mx-auto mb-2" />
                <p className="text-sm">No stocks found for "{value}"</p>
                <p className="text-xs text-gray-400 mt-1">
                  Try searching by ticker symbol or company name
                </p>
              </div>
            ) : null}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

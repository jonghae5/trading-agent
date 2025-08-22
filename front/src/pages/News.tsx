import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, RefreshCw, Clock } from 'lucide-react'
import { NewsItem } from '../components/news/NewsItem'
import { NewsSearch } from '../components/news/NewsSearch'
import { fetchNews, searchNews } from '../api/news'
import { NewsArticle } from '../types'
import { getKSTDate } from '../lib/utils'

export const News: React.FC = () => {
  const [articles, setArticles] = useState<NewsArticle[]>([])
  const [filteredArticles, setFilteredArticles] = useState<NewsArticle[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [searching, setSearching] = useState(false)

  const [lastUpdated, setLastUpdated] = useState<Date>(getKSTDate())


  const loadArticles = async (refresh = false) => {
    if (refresh) setRefreshing(true)
    else setLoading(true)

    try {
      const data = await fetchNews('latest')
      setArticles(data.slice(0, 20))
      setLastUpdated(getKSTDate())
    } catch (error) {
      console.error('Failed to load articles:', error)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  const handleSearch = async (query: string) => {
    if (!query.trim()) {
      setFilteredArticles([])
      // 검색어가 없을 때 기본 뉴스 로드
      await loadArticles()
      return
    }

    setSearching(true)
    try {
      const results = await searchNews({ query, limit: 20 })
      setFilteredArticles(results.articles.slice(0, 20))
    } catch (error) {
      console.error('Search failed:', error)
      setFilteredArticles([])
    } finally {
      setSearching(false)
    }
  }

  const handleRefresh = () => {
    loadArticles(true)
  }

  useEffect(() => {
    loadArticles()
  }, [])

  const onSearch = (searchQuery: string) => {
    handleSearch(searchQuery)
  }
  const displayArticles =
    filteredArticles.length > 0 ? filteredArticles : articles

  return (
    <div className="min-h-screen bg-gray-50 p-3 sm:p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 sm:mb-8">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
            <div>
              <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                뉴스 모니터링
              </h1>
              <p className="text-gray-600 mt-2 text-sm sm:text-base">
                실시간 금융 뉴스와 시장 동향을 확인하세요
              </p>
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
              <button
                onClick={handleRefresh}
                disabled={refreshing}
                className="flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 bg-white border border-gray-200 rounded-lg text-gray-700 hover:bg-gray-50 transition-all disabled:opacity-50 text-sm sm:text-base"
              >
                <RefreshCw
                  className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`}
                />
                <span className="hidden sm:inline">새로고침</span>
              </button>
            </div>
          </div>

          {/* Search */}
          <AnimatePresence>
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-6"
            >
              <NewsSearch
                onSearch={(filters) => onSearch(filters.query || '')}
                isLoading={loading || searching}
              />
            </motion.div>
          </AnimatePresence>

          {/* Latest News Header */}
          <div className="flex items-center gap-2 bg-white p-3 rounded-lg border border-gray-200">
            <Clock className="h-5 w-5 text-blue-600" />
            <span className="font-medium text-gray-900">최신 뉴스</span>
            <span className="ml-auto px-2 py-1 text-sm bg-blue-50 text-blue-700 rounded-full">
              {displayArticles.length}개
            </span>
          </div>

          {/* Last Updated */}
          <div className="mt-4 text-xs sm:text-sm text-gray-500">
            마지막 업데이트: {lastUpdated.toLocaleString('ko-KR')}
          </div>
        </div>

        {/* Content */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-2 xl:grid-cols-3 gap-4 sm:gap-6">
          <AnimatePresence mode="wait">
            {loading ? (
              <motion.div
                key="loading"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="col-span-full flex items-center justify-center py-12"
              >
                <div className="text-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
                  <p className="mt-4 text-gray-600">
                    뉴스를 불러오고 있습니다...
                  </p>
                </div>
              </motion.div>
            ) : searching ? (
              // News search skeleton
              Array.from({ length: 6 }).map((_, index) => (
                <motion.div
                  key={`skeleton-${index}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="bg-white rounded-lg border border-gray-200 p-4 animate-pulse"
                >
                  <div className="space-y-3">
                    <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                    <div className="h-3 bg-gray-200 rounded w-full"></div>
                    <div className="h-3 bg-gray-200 rounded w-2/3"></div>
                    <div className="flex justify-between items-center pt-2">
                      <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                      <div className="h-3 bg-gray-200 rounded w-1/4"></div>
                    </div>
                  </div>
                </motion.div>
              ))
            ) : displayArticles.length === 0 ? (
              <motion.div
                key="empty"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="col-span-full text-center py-12"
              >
                <div className="text-gray-400">
                  <Search className="h-16 w-16 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    뉴스가 없습니다
                  </h3>
                  <p>다른 카테고리를 선택하거나 검색 조건을 변경해보세요.</p>
                </div>
              </motion.div>
            ) : (
              displayArticles.map((article, index) => (
                <motion.div
                  key={article.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.1 }}
                >
                  <NewsItem article={article} />
                </motion.div>
              ))
            )}
          </AnimatePresence>
        </div>

        {/* Show Results Info */}
        {filteredArticles.length > 0 && (
          <div className="mt-6 sm:mt-8 p-3 sm:p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2 text-blue-700">
              <Search className="h-4 w-4 flex-shrink-0" />
              <span className="font-medium text-sm sm:text-base">
                검색 결과: {filteredArticles.length}개의 뉴스를 찾았습니다
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

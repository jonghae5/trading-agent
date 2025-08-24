import React from 'react'
import { motion } from 'framer-motion'
import {
  Clock,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'

import { cn, newKSTDate } from '../../lib/utils'
import type { NewsArticle } from '../../types'

interface NewsItemProps {
  article: NewsArticle
  onClick?: (article: NewsArticle) => void
  compact?: boolean
  className?: string
}

export const NewsItem: React.FC<NewsItemProps> = ({
  article,
  onClick,
  compact = false,
  className
}) => {
  const getSentimentIcon = (compoundScore: number) => {
    if (compoundScore >= 0.05) {
      return <TrendingUp className="h-4 w-4 text-emerald-600" />
    } else if (compoundScore <= -0.05) {
      return <TrendingDown className="h-4 w-4 text-red-600" />
    } else {
      return <Minus className="h-4 w-4 text-gray-500" />
    }
  }

  const getSentimentColor = (compoundScore: number) => {
    if (compoundScore >= 0.05) {
      return 'border-l-emerald-500 bg-emerald-50/30'
    } else if (compoundScore <= -0.05) {
      return 'border-l-red-500 bg-red-50/30'
    } else {
      return 'border-l-gray-400 bg-gray-50/30'
    }
  }

  const getCompoundScorePercentage = (compoundScore: number): number => {
    // compound_score는 -1부터 1까지, 이를 0%부터 100%로 변환
    return Math.round(((compoundScore + 1) / 2) * 100)
  }

  const getCompoundScoreColor = (compoundScore: number): string => {
    if (compoundScore >= 0.5) {
      return 'bg-emerald-500'
    } else if (compoundScore >= 0.05) {
      return 'bg-green-500'
    } else if (compoundScore >= -0.05) {
      return 'bg-gray-500'
    } else if (compoundScore >= -0.5) {
      return 'bg-orange-500'
    } else {
      return 'bg-red-500'
    }
  }

  const handleClick = () => {
    if (onClick) {
      onClick(article)
    } else if (article.url) {
      window.open(article.url, '_blank', 'noopener,noreferrer')
    }
  }

  const timeAgo = formatDistanceToNow(newKSTDate(article.published_at), {
    addSuffix: true
  })

  return (
    <motion.article
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      whileHover={{ scale: 1.02 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'group relative cursor-pointer rounded-lg border-l-4 bg-white p-3 shadow-sm transition-all duration-200 hover:shadow-md',
        getSentimentColor(article.compound_score),
        compact ? 'p-2' : 'p-3',
        className
      )}
      onClick={handleClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          {getSentimentIcon(article.compound_score)}
          <span className="font-medium">{article.source}</span>
          <div className="flex items-center gap-1">
            <Clock className="h-3 w-3" />
            <span>{timeAgo}</span>
          </div>
        </div>

        {article.url && (
          <ExternalLink className="h-3 w-3 text-gray-400 opacity-0 transition-opacity group-hover:opacity-100" />
        )}
      </div>

      {/* Title */}
      <h3
        className={cn(
          'font-semibold text-gray-900 line-clamp-2 group-hover:text-blue-700 transition-colors',
          compact ? 'text-sm mt-1' : 'text-sm mt-2'
        )}
      >
        {article.title}
      </h3>

      {/* Summary */}
      {article.summary && !compact && (
        <p className="mt-2 text-xs text-gray-600 line-clamp-3">
          {article.summary}
        </p>
      )}

      {/* Footer */}
      <div className="mt-3 flex items-center justify-between">
        {/* Tags */}
        {article.tags && article.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {article.tags.slice(0, compact ? 2 : 3).map((tag, index) => (
              <span
                key={index}
                className="inline-block rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
              >
                {tag}
              </span>
            ))}
            {article.tags.length > (compact ? 2 : 3) && (
              <span className="text-xs text-gray-400">
                +{article.tags.length - (compact ? 2 : 3)} more
              </span>
            )}
          </div>
        )}

        {/* Sentiment Score */}
        {typeof article.compound_score === 'number' && (
          <div className="flex items-center gap-1">
            <div className="h-2 w-10 rounded-full bg-gray-200">
              <div
                className={`h-2 rounded-full transition-all duration-300 ${getCompoundScoreColor(article.compound_score)}`}
                style={{ width: `${getCompoundScorePercentage(article.compound_score)}%` }}
              />
            </div>
            <span className="text-xs font-medium text-gray-600">
              {getCompoundScorePercentage(article.compound_score)}%
            </span>
          </div>
        )}
      </div>

      {/* Hover Effect Overlay */}
      <div className="absolute inset-0 rounded-lg bg-blue-50 opacity-0 transition-opacity group-hover:opacity-10" />
    </motion.article>
  )
}

export default NewsItem

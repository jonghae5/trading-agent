import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import {
  History as HistoryIcon,
  Calendar,
  TrendingUp,
  Activity,
  Eye,
  Download,
  Trash2,
  Filter,
  Search,
  Clock,
  BarChart3,
  FileText,
  CheckCircle,
  XCircle,
  AlertCircle,
  Play,
  RefreshCw
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import {
  historyApi,
  AnalysisSession,
  AnalysisStatsResponse
} from '../api/history'
import { ReportDetailView } from '../components/reports/ReportDetailView'

// Status badge component
const StatusBadge: React.FC<{ status: string }> = ({ status }) => {
  const getStatusConfig = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return { color: 'bg-green-100 text-green-700', icon: CheckCircle }
      case 'running':
        return { color: 'bg-blue-100 text-blue-700', icon: Play }
      case 'failed':
        return { color: 'bg-red-100 text-red-700', icon: XCircle }
      case 'cancelled':
        return { color: 'bg-gray-100 text-gray-700', icon: XCircle }
      case 'pending':
        return { color: 'bg-yellow-100 text-yellow-700', icon: Clock }
      default:
        return { color: 'bg-gray-100 text-gray-700', icon: AlertCircle }
    }
  }

  const { color, icon: Icon } = getStatusConfig(status)

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium ${color}`}
    >
      <Icon className="size-3" />
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

// Decision badge component
const DecisionBadge: React.FC<{ decision?: string }> = ({ decision }) => {
  if (!decision) return <span className="text-gray-400">-</span>

  const getDecisionColor = (decision: string) => {
    const lowerDecision = decision.toLowerCase()
    if (lowerDecision.includes('buy') || lowerDecision.includes('bullish')) {
      return 'text-green-600 bg-green-50 border-green-200'
    } else if (
      lowerDecision.includes('sell') ||
      lowerDecision.includes('bearish')
    ) {
      return 'text-red-600 bg-red-50 border-red-200'
    } else {
      return 'text-yellow-600 bg-yellow-50 border-yellow-200'
    }
  }

  return (
    <span
      className={`inline-block px-2 py-1 rounded border text-xs font-medium ${getDecisionColor(
        decision
      )}`}
    >
      {decision}
    </span>
  )
}

// Main History component
export const History: React.FC = () => {
  const navigate = useNavigate()
  const [sessions, setSessions] = useState<AnalysisSession[]>([])
  const [stats, setStats] = useState<AnalysisStatsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [searchTicker, setSearchTicker] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(0)
  const [totalSessions, setTotalSessions] = useState(0)

  // Detail view state
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(
    null
  )

  // Load data
  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)

      const [historyResponse, statsResponse] = await Promise.all([
        historyApi.getHistory({
          ticker: searchTicker || '',
          page: currentPage,
          per_page: 20
        }),
        historyApi.getAnalysisStats({
          days: 30
        })
      ])
      setSessions(historyResponse.sessions)
      setTotalPages(historyResponse.pages)
      setTotalSessions(historyResponse.total)
      setStats(statsResponse)
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to load analysis history'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line
  }, [currentPage, searchTicker])

  const handleSearch = (value: string) => {
    setSearchTicker(value)
    setCurrentPage(1)
  }

  const formatDate = (dateString: string) => {
    if (!dateString) return '-'
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-'
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = Math.floor(seconds % 60)
    return `${minutes}m ${remainingSeconds}s`
  }

  const handleExport = async (sessionId: string, ticker: string) => {
    try {
      const response = await historyApi.exportAnalysisReport(sessionId, 'json')
      const blob = new Blob([JSON.stringify(response, null, 2)], {
        type: 'application/json'
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `analysis_${ticker}_${sessionId.slice(0, 8)}.json`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      alert('Failed to export analysis report')
    }
  }

  const handleDelete = async (sessionId: string, ticker: string) => {
    if (window.confirm(`정말로 ${ticker} 분석을 삭제하시겠습니까?`)) {
      try {
        await historyApi.deleteAnalysisReport(sessionId)
        await loadData()
      } catch (err) {
        alert('Failed to delete analysis report')
      }
    }
  }

  if (selectedSessionId) {
    return (
      <ReportDetailView
        sessionId={selectedSessionId}
        onBack={() => setSelectedSessionId(null)}
      />
    )
  }

  if (loading && sessions.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">
              분석 히스토리
            </h1>
            <p className="text-gray-600 mt-1">
              과거 분석 내역을 불러오는 중입니다...
            </p>
          </div>
        </div>
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="size-8 animate-spin text-blue-500" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            분석 히스토리
          </h1>
          <p className="text-gray-600 mt-1">
            과거 트레이딩 분석 리포트와 인사이트를 확인하세요.
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" onClick={() => loadData()}>
            <RefreshCw className="size-4 mr-2" />
            새로고침
          </Button>
        </div>
      </div>

      {/* Error Message */}
      {error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 text-red-700">
              <XCircle className="size-5" />
              <span>{error}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stats Overview */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
          >
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-50 rounded-lg">
                    <BarChart3 className="size-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">총 분석 수</p>
                    <p className="text-xl font-bold text-gray-900">
                      {stats.total_analyses}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-green-50 rounded-lg">
                    <TrendingUp className="size-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">평균 신뢰도</p>
                    <p className="text-xl font-bold text-gray-900">
                      {stats.average_confidence != null
                        ? `${Math.round(stats.average_confidence)}%`
                        : '-'}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-purple-50 rounded-lg">
                    <Activity className="size-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">결정 분포</p>
                    <div className="flex gap-1 mt-1 flex-wrap">
                      {Object.keys(stats.decision_distribution).length === 0 ? (
                        <span className="text-xs text-gray-400">-</span>
                      ) : (
                        Object.entries(stats.decision_distribution).map(
                          ([decision, count]) => (
                            <span
                              key={decision}
                              className="text-xs bg-gray-100 px-1 py-0.5 rounded"
                            >
                              {decision}: {count}
                            </span>
                          )
                        )
                      )}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card>
              <CardContent className="p-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-50 rounded-lg">
                    <Calendar className="size-5 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">기간</p>
                    <p className="text-xl font-bold text-gray-900">30일</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )}

      {/* Search and Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Filter className="size-5" />
                필터
              </CardTitle>
              <CardDescription>
                분석 내역을 검색 및 필터링하세요.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 size-4" />
                <Input
                  placeholder="티커로 검색 (예: AAPL, TSLA)"
                  value={searchTicker}
                  onChange={(e) => handleSearch(e.target.value)}
                  className="pl-10"
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Analysis History Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <HistoryIcon className="size-5" />
            분석 히스토리
          </CardTitle>
          <CardDescription>
            {totalSessions > 0
              ? `총 ${totalSessions}건 중 ${sessions.length}건 표시`
              : '분석 내역이 없습니다.'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="size-12 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                분석 내역 없음
              </h3>
              <p className="text-gray-500 mb-4">
                아직 분석을 실행한 기록이 없습니다.
              </p>
              <Button onClick={() => navigate('/analysis')}>
                첫 분석 시작하기
              </Button>
            </div>
          ) : (
            <div className="space-y-4">
              {sessions.map((session, index) => {
                // config_snapshot에서 analysts, research_depth, llm_provider 추출
                const config = session.config_snapshot || {}
                const analysts = Array.isArray(config.analysts)
                  ? config.analysts
                  : []
                const researchDepth = config.research_depth
                const llmProvider = config.llm_provider

                return (
                  <motion.div
                    key={session.session_id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className="p-4 border border-gray-200 rounded-lg hover:border-gray-300 transition-colors"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-3 mb-2">
                          <h3 className="text-lg font-semibold text-gray-900">
                            {session.ticker}
                          </h3>
                          <StatusBadge status={session.status} />
                          <DecisionBadge decision={session.final_decision} />
                        </div>

                        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <span className="text-gray-500">분석일:</span>
                            <div className="font-medium">
                              {session.analysis_date
                                ? session.analysis_date.split('T')[0]
                                : '-'}
                            </div>
                          </div>
                          <div>
                            <span className="text-gray-500">생성일:</span>
                            <div className="font-medium">
                              {formatDate(session.created_at)}
                            </div>
                          </div>
                          <div>
                            <span className="text-gray-500">소요시간:</span>
                            <div className="font-medium">
                              {formatDuration(session.execution_time_seconds)}
                            </div>
                          </div>
                          <div>
                            <span className="text-gray-500">신뢰도:</span>
                            <div className="font-medium">
                              {session.confidence_score != null
                                ? `${Math.round(session.confidence_score)}%`
                                : '-'}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-4 mt-3 text-sm text-gray-500 flex-wrap">
                          <span>애널리스트: {analysts.length}</span>
                          <span>깊이: {researchDepth ?? '-'}</span>
                          <span>모델: {llmProvider ?? '-'}</span>
                          {session.llm_call_count != null && (
                            <span>LLM 호출: {session.llm_call_count}</span>
                          )}
                        </div>

                        {session.status === 'failed' &&
                          session.error_message && (
                            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                              <div className="flex items-start gap-2">
                                <XCircle className="size-4 text-red-500 mt-0.5 flex-shrink-0" />
                                <div className="text-sm text-red-700">
                                  <p className="font-medium mb-1">분석 실패:</p>
                                  <p className="text-xs font-mono break-all">
                                    {session.error_message.length > 100
                                      ? `${session.error_message.substring(
                                          0,
                                          100
                                        )}...`
                                      : session.error_message}
                                  </p>
                                </div>
                              </div>
                            </div>
                          )}
                      </div>

                      <div className="flex items-center gap-2 ml-4">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            setSelectedSessionId(session.session_id)
                          }
                        >
                          <Eye className="size-4" />
                        </Button>

                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            handleDelete(session.session_id, session.ticker)
                          }
                          className="text-red-600 hover:text-red-700 hover:border-red-300"
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </div>
                    </div>
                  </motion.div>
                )
              })}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between mt-6 pt-4 border-t">
              <div className="text-sm text-gray-500">
                페이지 {currentPage} / {totalPages}
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setCurrentPage((prev) => Math.max(1, prev - 1))
                  }
                  disabled={currentPage === 1}
                >
                  이전
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    setCurrentPage((prev) => Math.min(totalPages, prev + 1))
                  }
                  disabled={currentPage === totalPages}
                >
                  다음
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

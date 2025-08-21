import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import {
  ArrowLeft,
  Brain,
  TrendingUp,
  Trash2,
  Zap,
  BarChart3,
  FileText,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Activity,
  Target,
  Eye,
  MessageSquare,
  Clock,
  DollarSign,
  Users,
  PieChart,
  TrendingDown,
  Minus
} from 'lucide-react'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../ui/card'
import { Button } from '../ui/button'
import { MarkdownRenderer } from '../common/MarkdownRenderer'
import { historyApi, AnalysisSession, HistoryReportSection } from '../../api/history'

interface ReportDetailViewProps {
  sessionId: string
  onBack: () => void
}

// Report section component
const ReportSectionCard: React.FC<{ section: HistoryReportSection }> = ({
  section
}) => {
  const [expanded, setExpanded] = useState(false)

  const getSectionIcon = (sectionType: string) => {
    switch (sectionType.toLowerCase()) {
      case 'market_report':
        return BarChart3
      case 'sentiment_report':
        return Activity
      case 'news_report':
        return FileText
      case 'fundamentals_report':
        return TrendingUp
      case 'bull_analysis':
        return TrendingUp
      case 'bear_analysis':
        return TrendingDown
      case 'judge_decision':
        return Users
      case 'final_decision':
        return CheckCircle
      case 'investment_plan':
        return Target
      case 'trader_investment_plan':
        return Zap
      default:
        return FileText
    }
  }

  const getSectionTitle = (sectionType: string) => {
    return sectionType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const Icon = getSectionIcon(section.section_type)

  return (
    <Card className="mb-4">
      <CardHeader
        className="cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-50 rounded-lg">
              <Icon className="size-5 text-blue-600" />
            </div>
            <div>
              <CardTitle className="text-lg">
                {getSectionTitle(section.section_type)}
              </CardTitle>
              <CardDescription>{section.agent_name}</CardDescription>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-500">
              {new Date(section.created_at).toLocaleString('ko-KR')}
            </span>
            <Eye
              className={`size-4 transition-transform ${
                expanded ? 'rotate-180' : ''
              }`}
            />
          </div>
        </div>
      </CardHeader>

      {expanded && (
        <CardContent>
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="prose prose-sm prose-gray max-w-none">
              <MarkdownRenderer content={section.content} variant="report" />
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

export const ReportDetailView: React.FC<ReportDetailViewProps> = ({
  sessionId,
  onBack
}) => {
  const [session, setSession] = useState<AnalysisSession | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadReportDetail()
    // eslint-disable-next-line
  }, [sessionId])

  const loadReportDetail = async () => {
    try {
      setLoading(true)
      setError(null)
      const sessionData = await historyApi.getAnalysisReport(sessionId)
      setSession(sessionData)
    } catch (err) {
      console.error('Failed to load report detail:', err)
      setError(
        err instanceof Error ? err.message : 'Failed to load report details'
      )
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '-'
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const remainingSeconds = Math.floor(seconds % 60)

    if (hours > 0) {
      return `${hours}h ${minutes}m ${remainingSeconds}s`
    }
    return `${minutes}m ${remainingSeconds}s`
  }

  const handleDelete = async () => {
    if (!session) return

    if (
      window.confirm(
        `Are you sure you want to delete the analysis for ${session.ticker}?`
      )
    ) {
      try {
        await historyApi.deleteAnalysisReport(sessionId)
        onBack()
      } catch (err) {
        console.error('Delete failed:', err)
        alert('Failed to delete analysis report')
      }
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return 'text-green-600 bg-green-50'
      case 'running':
        return 'text-blue-600 bg-blue-50'
      case 'failed':
        return 'text-red-600 bg-red-50'
      case 'cancelled':
        return 'text-gray-600 bg-gray-50'
      case 'pending':
        return 'text-yellow-600 bg-yellow-50'
      default:
        return 'text-gray-600 bg-gray-50'
    }
  }

  const getDecisionColor = (decision?: string) => {
    if (!decision) return 'text-gray-600 bg-gray-50'

    const lowerDecision = decision.toLowerCase()
    if (
      lowerDecision.includes('buy') ||
      lowerDecision.includes('bullish') ||
      lowerDecision.includes('매수')
    ) {
      return 'text-green-600 bg-green-50'
    } else if (
      lowerDecision.includes('sell') ||
      lowerDecision.includes('bearish') ||
      lowerDecision.includes('매도')
    ) {
      return 'text-red-600 bg-red-50'
    } else if (
      lowerDecision.includes('hold') ||
      lowerDecision.includes('보유')
    ) {
      return 'text-blue-600 bg-blue-50'
    } else {
      return 'text-yellow-600 bg-yellow-50'
    }
  }

  const getDecisionIcon = (decision?: string) => {
    if (!decision) return Minus

    const lowerDecision = decision.toLowerCase()
    if (
      lowerDecision.includes('buy') ||
      lowerDecision.includes('bullish') ||
      lowerDecision.includes('매수')
    ) {
      return TrendingUp
    } else if (
      lowerDecision.includes('sell') ||
      lowerDecision.includes('bearish') ||
      lowerDecision.includes('매도')
    ) {
      return TrendingDown
    } else if (
      lowerDecision.includes('hold') ||
      lowerDecision.includes('보유')
    ) {
      return Minus
    } else {
      return Target
    }
  }

  // Helper: count completed agents from agent_executions
  const getCompletedAgentCount = () => {
    if (!session?.agent_executions) return 0
    return session.agent_executions.filter(
      (exec) => exec.status === 'completed'
    ).length
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={onBack}>
            <ArrowLeft className="size-4 mr-2" />
            뒤로가기
          </Button>
          <h1 className="text-2xl font-semibold">리포트 로딩 중...</h1>
        </div>

        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
        </div>
      </div>
    )
  }

  if (error || !session) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button variant="outline" onClick={onBack}>
            <ArrowLeft className="size-4 mr-2" />
            Back
          </Button>
          <h1 className="text-2xl font-semibold text-red-600">
            Error Loading Report
          </h1>
        </div>

        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-6">
            <div className="flex items-center gap-2 text-red-700">
              <XCircle className="size-5" />
              <span>{error || 'Report not found'}</span>
            </div>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 sm:gap-4">
          <Button variant="outline" onClick={onBack} size="sm">
            <ArrowLeft className="size-4 mr-1 sm:mr-2" />
            <span className="text-xs sm:text-sm">뒤로</span>
          </Button>
          <div className="min-w-0 flex-1">
            <h1 className="text-lg sm:text-xl md:text-2xl font-semibold text-gray-900 truncate">
              분석 리포트: {session.ticker}
            </h1>
            <p className="text-gray-600 mt-1 text-xs sm:text-sm md:text-base truncate">
              세션 {sessionId.slice(0, 8)}
            </p>
          </div>
        </div>

        <div className="flex gap-2 justify-end">
          <Button
            variant="outline"
            onClick={handleDelete}
            size="sm"
            className="text-red-600 hover:text-red-700 hover:border-red-300 flex-shrink-0"
          >
            <Trash2 className="size-4 mr-1" />
            <span className="text-xs sm:text-sm">삭제</span>
          </Button>
        </div>
      </div>

      {/* Session Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
            <BarChart3 className="size-5" />
            분석 개요
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 md:gap-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900 text-sm md:text-base">
                기본 정보
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    종목:
                  </span>
                  <span className="font-medium text-base md:text-lg">
                    {session.ticker}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    분석 날짜:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {session.analysis_date}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    상태:
                  </span>
                  <span
                    className={`px-2 py-1 rounded-full text-sm font-medium ${getStatusColor(
                      session.status
                    )}`}
                  >
                    {session.status.charAt(0).toUpperCase() +
                      session.status.slice(1)}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    사용자:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {session.username}
                  </span>
                </div>
              </div>
            </div>

            {/* Timing Info */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900 text-sm md:text-base">
                시간 정보
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <span className="text-gray-600 text-sm md:text-base">
                    생성:
                  </span>
                  <span className="font-medium text-xs md:text-sm text-right">
                    {formatDate(session.created_at)}
                  </span>
                </div>
                {session.started_at && (
                  <div className="flex justify-between items-start">
                    <span className="text-gray-600 text-sm md:text-base">
                      시작:
                    </span>
                    <span className="font-medium text-xs md:text-sm text-right">
                      {formatDate(session.started_at)}
                    </span>
                  </div>
                )}
                {session.completed_at && (
                  <div className="flex justify-between items-start">
                    <span className="text-gray-600 text-sm md:text-base">
                      완료:
                    </span>
                    <span className="font-medium text-xs md:text-sm text-right">
                      {formatDate(session.completed_at)}
                    </span>
                  </div>
                )}
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    소요시간:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {formatDuration(session.execution_time_seconds)}
                  </span>
                </div>
              </div>
            </div>

            {/* Results */}
            <div className="space-y-4">
              <h3 className="font-semibold text-gray-900 text-sm md:text-base">
                결과
              </h3>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    투자결정:
                  </span>
                  {session.final_decision ? (
                    <div className="flex items-center gap-2">
                      {React.createElement(
                        getDecisionIcon(session.final_decision),
                        {
                          className: `size-4 ${
                            getDecisionColor(session.final_decision).split(
                              ' '
                            )[0]
                          }`
                        }
                      )}
                      <span
                        className={`px-2 py-1 rounded text-sm font-medium ${getDecisionColor(
                          session.final_decision
                        )}`}
                      >
                        {session.final_decision}
                      </span>
                    </div>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    신뢰도:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {session.confidence_score
                      ? `${Math.round(session.confidence_score)}%`
                      : '-'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    LLM 호출:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {session.llm_call_count || '-'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    도구 호출:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {session.tool_call_count || '-'}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
            <Brain className="size-5" />
            설정 정보
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6">
            <div>
              <h3 className="font-semibold text-gray-900 mb-3 text-sm md:text-base">
                선택된 분석가
              </h3>
              <div className="space-y-2">
                {session.config_snapshot?.analysts?.map(
                  (analyst: any, index: number) => (
                    <div key={index} className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <span className="text-sm">{analyst}</span>
                    </div>
                  )
                ) || (
                  <span className="text-sm text-gray-400">
                    설정된 분석가 없음
                  </span>
                )}
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-gray-900 mb-3 text-sm md:text-base">
                연구 설정
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    연구 깊이:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {session.config_snapshot?.research_depth || '-'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    LLM 제공자:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {session.config_snapshot?.llm_provider || '-'}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    고급 모델:
                  </span>
                  <span className="font-medium text-xs md:text-sm">
                    {session.config_snapshot?.deep_thinker || '-'}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="font-semibold text-gray-900 mb-3 text-sm md:text-base">
                실행 통계
              </h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    완료된 에이전트:
                  </span>
                  <span className="font-medium text-sm md:text-base">
                    {getCompletedAgentCount()} /{' '}
                    {session.agent_executions?.length || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    실패한 에이전트:
                  </span>
                  <span className="font-medium text-red-600 text-sm md:text-base">
                    {session.agent_executions
                      ? session.agent_executions.filter(
                          (exec: any) => exec.status === 'failed'
                        ).length
                      : 0}
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-600 text-sm md:text-base">
                    총 토큰 수:
                  </span>
                  <span className="font-medium text-xs md:text-sm">-</span>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Report Sections */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg md:text-xl">
            <FileText className="size-5" />
            리포트 섹션
          </CardTitle>
          <CardDescription className="text-sm md:text-base">
            {session.report_sections && session.report_sections.length > 0
              ? '각 AI 에이전트의 상세 분석 리포트'
              : session.status === 'failed'
                ? '분석 실패 - 생성된 리포트 없음'
                : session.status === 'running'
                  ? '분석 진행 중 - 리포트가 여기에 표시됩니다'
                  : '아직 사용 가능한 리포트가 없습니다'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {session.report_sections && session.report_sections.length > 0 ? (
            <motion.div
              className="space-y-4"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ staggerChildren: 0.1 }}
            >
              {session.report_sections
                .sort(
                  (a, b) =>
                    new Date(a.created_at).getTime() -
                    new Date(b.created_at).getTime()
                )
                .map((section, index) => (
                  <motion.div
                    key={section.id}
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.1 }}
                  >
                    <ReportSectionCard section={section} />
                  </motion.div>
                ))}
            </motion.div>
          ) : (
            <div className="text-center py-12">
              {session.status === 'failed' ? (
                <>
                  <XCircle className="size-12 text-red-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    분석 실패
                  </h3>
                  <p className="text-gray-500 mb-4">
                    분석을 성공적으로 완료할 수 없었습니다.
                  </p>
                  {session.error_message && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-left">
                      <p className="text-sm text-red-700 font-mono">
                        {session.error_message}
                      </p>
                    </div>
                  )}
                </>
              ) : session.status === 'running' ? (
                <>
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    분석 진행 중
                  </h3>
                  <p className="text-gray-500">
                    에이전트가 분석을 완료하면 리포트가 여기에 표시됩니다.
                  </p>
                </>
              ) : (
                <>
                  <FileText className="size-12 text-gray-300 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-gray-900 mb-2">
                    사용 가능한 리포트 없음
                  </h3>
                  <p className="text-gray-500">
                    아직 이 세션에 대한 분석 리포트가 생성되지 않았습니다.
                  </p>
                </>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Final Analysis Summary */}
      {session.final_decision && (
        <Card className="border-l-4 border-l-blue-500">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <MessageSquare className="size-5 text-blue-600" />
              최종 분석 결과
            </CardTitle>
            <CardDescription>
              AI 분석 완료 시점:{' '}
              {session.completed_at && formatDate(session.completed_at)}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-6">
              <div className="prose prose-sm max-w-none">
                <MarkdownRenderer
                  content={session.final_decision || ''}
                  variant="summary"
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Performance Metrics Dashboard */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <PieChart className="size-5" />
            성과 메트릭스
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 md:gap-6">
            {/* Messages Count */}
            <div className="bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm font-medium text-blue-600">
                    리포트 섹션
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-blue-900">
                    {session.report_sections?.length || 0}
                  </p>
                </div>
                <MessageSquare className="size-6 md:size-8 text-blue-500" />
              </div>
            </div>

            {/* Agent Performance */}
            <div className="bg-gradient-to-br from-green-50 to-green-100 rounded-lg p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm font-medium text-green-600">
                    완료된 에이전트
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-green-900">
                    {getCompletedAgentCount()} /{' '}
                    {session.agent_executions?.length || 0}
                  </p>
                </div>
                <Users className="size-6 md:size-8 text-green-500" />
              </div>
            </div>

            {/* Execution Time */}
            <div className="bg-gradient-to-br from-yellow-50 to-yellow-100 rounded-lg p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm font-medium text-yellow-600">
                    실행 시간
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-yellow-900">
                    {formatDuration(session.execution_time_seconds)}
                  </p>
                </div>
                <Clock className="size-6 md:size-8 text-yellow-500" />
              </div>
            </div>

            {/* Cost Information */}
            <div className="bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg p-3 md:p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs md:text-sm font-medium text-purple-600">
                    예상 비용
                  </p>
                  <p className="text-lg md:text-2xl font-bold text-purple-900">
                    -
                  </p>
                </div>
                <DollarSign className="size-6 md:size-8 text-purple-500" />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Agent Execution Timeline */}
      {session.agent_executions && session.agent_executions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="size-5" />
              에이전트 실행 현황
            </CardTitle>
            <CardDescription>
              각 AI 분석 에이전트의 실행 상태와 성과
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {session.agent_executions.map((execution, index: number) => (
                <motion.div
                  key={execution.execution_id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="border rounded-lg p-3 md:p-4 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div
                        className={`p-2 rounded-lg ${
                          execution.status === 'completed'
                            ? 'bg-green-100'
                            : execution.status === 'failed'
                              ? 'bg-red-100'
                              : 'bg-yellow-100'
                        }`}
                      >
                        {execution.status === 'completed' ? (
                          <CheckCircle className="size-5 text-green-600" />
                        ) : execution.status === 'failed' ? (
                          <XCircle className="size-5 text-red-600" />
                        ) : (
                          <Clock className="size-5 text-yellow-600" />
                        )}
                      </div>
                      <div>
                        <h3 className="font-semibold text-gray-900 text-sm md:text-base">
                          {execution.agent_name}
                        </h3>
                        <p className="text-xs md:text-sm text-gray-600">
                          상태:{' '}
                          <span
                            className={`font-medium ${
                              execution.status === 'completed'
                                ? 'text-green-600'
                                : execution.status === 'failed'
                                  ? 'text-red-600'
                                  : 'text-yellow-600'
                            }`}
                          >
                            {execution.status === 'completed'
                              ? '완료'
                              : execution.status === 'failed'
                                ? '실패'
                                : '진행중'}
                          </span>
                        </p>
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-xs md:text-sm text-gray-600">
                        상태: {execution.status === 'completed' ? '완료' : execution.status === 'failed' ? '실패' : '진행중'}
                      </div>
                      {execution.execution_time_seconds && (
                        <div className="text-xs md:text-sm text-gray-500">
                          소요시간: {formatDuration(execution.execution_time_seconds)}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Progress bar */}
                  <div className="mt-3">
                    <div className="w-full bg-gray-200 rounded-full h-2">
                      <div
                        className={`h-2 rounded-full transition-all duration-300 ${
                          execution.status === 'completed'
                            ? 'bg-green-500'
                            : execution.status === 'failed'
                              ? 'bg-red-500'
                              : 'bg-blue-500'
                        }`}
                        style={{
                          width: `${execution.status === 'completed' ? 100 : execution.status === 'failed' ? 100 : 50}%`
                        }}
                      ></div>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Error Message if any */}
      {session.error_message && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700">
              <AlertTriangle className="size-5" />
              오류 정보
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700">{session.error_message}</p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

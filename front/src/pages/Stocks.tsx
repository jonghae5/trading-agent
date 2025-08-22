import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  Search,
  Filter,
  Star,
  BarChart3,
  DollarSign,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  RefreshCw,
  Zap,
  Eye,
  Bell,
  Settings
} from 'lucide-react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  ScatterChart,
  Scatter
} from 'recharts'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../components/ui/card'
import { Button } from '../components/ui/button'
import { Input } from '../components/ui/input'
import { StockAutocomplete } from '../components/ui/stock-autocomplete'
import { useAnalysisStore } from '../stores/analysisStore'
import { apiClient } from '../api'
import { getKSTDate } from '../lib/utils'

const mockStocks = [
  {
    symbol: 'AAPL',
    name: 'Apple Inc.',
    price: '$173.50',
    change: '+$2.15',
    changePercent: '+1.25%',
    volume: '45.2M',
    marketCap: '$2.75T',
    pe: '28.9',
    trend: 'up' as const,
    favorite: true
  },
  {
    symbol: 'TSLA',
    name: 'Tesla Inc.',
    price: '$248.75',
    change: '-$5.20',
    changePercent: '-2.05%',
    volume: '62.1M',
    marketCap: '$789B',
    pe: '59.2',
    trend: 'down' as const,
    favorite: true
  },
  {
    symbol: 'MSFT',
    name: 'Microsoft Corporation',
    price: '$334.89',
    change: '+$1.85',
    changePercent: '+0.56%',
    volume: '28.4M',
    marketCap: '$2.48T',
    pe: '32.1',
    trend: 'up' as const,
    favorite: false
  },
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    price: '$445.67',
    change: '+$12.30',
    changePercent: '+2.84%',
    volume: '89.7M',
    marketCap: '$1.1T',
    pe: '65.8',
    trend: 'up' as const,
    favorite: true
  },
  {
    symbol: 'GOOGL',
    name: 'Alphabet Inc.',
    price: '$139.25',
    change: '-$0.75',
    changePercent: '-0.54%',
    volume: '35.6M',
    marketCap: '$1.75T',
    pe: '26.4',
    trend: 'down' as const,
    favorite: false
  },
  {
    symbol: 'AMZN',
    name: 'Amazon.com Inc.',
    price: '$142.18',
    change: '+$3.42',
    changePercent: '+2.47%',
    volume: '42.8M',
    marketCap: '$1.48T',
    pe: '48.9',
    trend: 'up' as const,
    favorite: false
  }
]

const mockSectors = [
  { name: 'Technology', change: '+1.25%', trend: 'up' as const },
  { name: 'Healthcare', change: '+0.85%', trend: 'up' as const },
  { name: 'Financial', change: '-0.32%', trend: 'down' as const },
  { name: 'Energy', change: '+2.15%', trend: 'up' as const },
  { name: 'Consumer', change: '-1.05%', trend: 'down' as const },
  { name: 'Industrial', change: '+0.67%', trend: 'up' as const }
]

// Mock data for stock charts
const mockPriceHistory = [
  { time: '9:30', AAPL: 173.2, TSLA: 248.1, MSFT: 334.5, NVDA: 445.2 },
  { time: '10:00', AAPL: 173.8, TSLA: 249.3, MSFT: 335.1, NVDA: 447.8 },
  { time: '10:30', AAPL: 174.1, TSLA: 247.9, MSFT: 334.8, NVDA: 449.2 },
  { time: '11:00', AAPL: 173.9, TSLA: 246.5, MSFT: 335.4, NVDA: 451.6 },
  { time: '11:30', AAPL: 174.3, TSLA: 248.7, MSFT: 336.2, NVDA: 448.9 },
  { time: '12:00', AAPL: 173.5, TSLA: 248.8, MSFT: 334.9, NVDA: 445.7 }
]

const mockVolumeData = [
  { stock: 'AAPL', volume: 45200000, avgVolume: 38500000 },
  { stock: 'TSLA', volume: 62100000, avgVolume: 54200000 },
  { stock: 'MSFT', volume: 28400000, avgVolume: 31200000 },
  { stock: 'NVDA', volume: 89700000, avgVolume: 72300000 },
  { stock: 'GOOGL', volume: 35600000, avgVolume: 29800000 }
]

const mockRiskReturn = [
  { stock: 'AAPL', risk: 18.2, return: 12.5, marketCap: 2750 },
  { stock: 'TSLA', risk: 45.6, return: 8.9, marketCap: 789 },
  { stock: 'MSFT', risk: 22.1, return: 15.2, marketCap: 2480 },
  { stock: 'NVDA', risk: 38.7, return: 22.8, marketCap: 1100 },
  { stock: 'GOOGL', risk: 25.4, return: 9.2, marketCap: 1750 }
]

export const Stocks: React.FC = () => {
  const [selectedStocks, setSelectedStocks] = useState<string[]>([
    'AAPL',
    'TSLA',
    'MSFT',
    'NVDA',
    'GOOGL',
    'AMZN'
  ])
  const [searchQuery, setSearchQuery] = useState('')
  const [watchlist, setWatchlist] = useState<string[]>(['AAPL', 'TSLA', 'NVDA'])
  const [isLoading, setIsLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(getKSTDate())
  const [realTimeData, setRealTimeData] = useState<Record<string, any>>({})
  const [activeFilter, setActiveFilter] = useState<
    'all' | 'favorites' | 'gainers' | 'active'
  >('all')

  const { analysisHistory } = useAnalysisStore()

  // Simulate real-time data updates
  useEffect(() => {
    const interval = setInterval(() => {
      setLastUpdate(getKSTDate())
      // In a real app, this would fetch actual real-time data
      fetchRealTimeData()
    }, 30000) // Update every 30 seconds

    return () => clearInterval(interval)
  }, [])

  const fetchRealTimeData = async () => {
    setIsLoading(true)
    try {
      // Simulate API call for real-time data
      const promises = selectedStocks.map(async (ticker) => {
        // In production, this would be a real API call
        const response = await apiClient.get(`/market/quote/${ticker}`)
        return { ticker, data: (response as any).data }
      })

      const results = await Promise.all(promises)
      const newData = results.reduce(
        (acc, { ticker, data }) => {
          acc[ticker] = data
          return acc
        },
        {} as Record<string, any>
      )

      setRealTimeData(newData)
    } catch (error) {
      console.error('Failed to fetch real-time data:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const toggleWatchlist = (ticker: string) => {
    setWatchlist((prev) =>
      prev.includes(ticker)
        ? prev.filter((t) => t !== ticker)
        : [...prev, ticker]
    )
  }

  const filteredStocks = mockStocks.filter((stock) => {
    const matchesSearch =
      stock.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
      stock.name.toLowerCase().includes(searchQuery.toLowerCase())

    if (!matchesSearch) return false

    switch (activeFilter) {
      case 'favorites':
        return watchlist.includes(stock.symbol)
      case 'gainers':
        return stock.trend === 'up'
      case 'active':
        return parseInt(stock.volume.replace('M', '')) > 40
      default:
        return true
    }
  })

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Stock Analysis
          </h1>
          <p className="text-gray-600 mt-1">
            Real-time stock data and AI-powered market insights
          </p>
        </div>
      </div>

      {/* Enhanced Search and Filters */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <Card>
          <CardContent className="p-6">
            <div className="flex flex-col lg:flex-row gap-4 items-center">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 size-4 text-gray-400" />
                <Input
                  placeholder="Search stocks by symbol or company name..."
                  className="pl-10"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={activeFilter === 'all' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveFilter('all')}
                >
                  All Stocks
                </Button>
                <Button
                  variant={activeFilter === 'favorites' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveFilter('favorites')}
                >
                  <Star className="size-3 mr-1" />
                  Favorites ({watchlist.length})
                </Button>
                <Button
                  variant={activeFilter === 'gainers' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveFilter('gainers')}
                >
                  <TrendingUp className="size-3 mr-1" />
                  Top Gainers
                </Button>
                <Button
                  variant={activeFilter === 'active' ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setActiveFilter('active')}
                >
                  <Activity className="size-3 mr-1" />
                  Most Active
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={fetchRealTimeData}
                  disabled={isLoading}
                >
                  <RefreshCw
                    className={`size-3 mr-1 ${isLoading ? 'animate-spin' : ''}`}
                  />
                  Refresh
                </Button>
              </div>
            </div>
            <div className="mt-3 flex items-center justify-between text-sm text-gray-500">
              <span>
                Showing {filteredStocks.length} stocks • Last updated:{' '}
                {lastUpdate.toLocaleTimeString()}
              </span>
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span>Live data</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Stock List */}
        <div className="lg:col-span-3">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2 }}
          >
            <Card>
              <CardHeader>
                <CardTitle>Market Overview</CardTitle>
                <CardDescription>
                  Real-time stock prices and market data
                </CardDescription>
              </CardHeader>
              <CardContent>
                <AnimatePresence mode="wait">
                  <div className="space-y-3">
                    {filteredStocks.map((stock, index) => {
                      const isInWatchlist =
                        Array.isArray(watchlist) &&
                        typeof stock?.symbol === 'string'
                          ? watchlist.includes(stock.symbol)
                          : false
                      const aiAnalysis =
                        analysisHistory && typeof stock?.symbol === 'string'
                          ? analysisHistory.find(
                              (analysis) => analysis.ticker === stock.symbol
                            )
                          : null
                      const hasAIAnalysis = !!aiAnalysis

                      return (
                        <motion.div
                          key={stock.symbol}
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: -10 }}
                          transition={{ delay: index * 0.05 }}
                          className="group relative overflow-hidden border border-gray-200 rounded-lg hover:shadow-lg hover:border-blue-200 transition-all duration-200 bg-gradient-to-r from-white to-gray-50"
                        >
                          {hasAIAnalysis && (
                            <div className="absolute top-2 left-2 z-10">
                              <div className="flex items-center gap-1 bg-blue-100 text-blue-700 px-2 py-1 rounded-full text-xs font-medium">
                                <Zap className="size-3" />
                                AI Analysis
                              </div>
                            </div>
                          )}

                          <div className="flex items-center justify-between p-4">
                            <div className="flex items-center gap-4">
                              <div className="flex items-center gap-3">
                                <button
                                  className="text-gray-400 hover:text-yellow-500 transition-colors"
                                  onClick={() => toggleWatchlist(stock.symbol)}
                                >
                                  <Star
                                    className={`size-4 transition-all ${
                                      isInWatchlist
                                        ? 'fill-yellow-400 text-yellow-400 scale-110'
                                        : 'hover:scale-110'
                                    }`}
                                  />
                                </button>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <p className="font-bold text-lg">
                                      {stock.symbol}
                                    </p>
                                    {isLoading && (
                                      <RefreshCw className="size-3 animate-spin text-blue-500" />
                                    )}
                                  </div>
                                  <p className="text-sm text-gray-600">
                                    {stock.name}
                                  </p>
                                  {hasAIAnalysis && (
                                    <div className="flex items-center gap-2 mt-1">
                                      <div className="text-xs text-blue-600 font-medium">
                                        Confidence:{' '}
                                        {aiAnalysis?.confidence_score || 'N/A'}%
                                      </div>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </div>

                            <div className="flex items-center gap-6">
                              <div className="text-right">
                                <p className="font-bold text-lg">
                                  {stock.price}
                                </p>
                                <div
                                  className={`flex items-center gap-1 text-sm ${
                                    stock.trend === 'up'
                                      ? 'text-green-600'
                                      : 'text-red-600'
                                  }`}
                                >
                                  {stock.trend === 'up' ? (
                                    <ArrowUpRight className="size-3" />
                                  ) : (
                                    <ArrowDownRight className="size-3" />
                                  )}
                                  <span>
                                    {stock.change} ({stock.changePercent})
                                  </span>
                                </div>
                              </div>

                              <div className="text-right text-sm text-gray-600 hidden md:block">
                                <p>Vol: {stock.volume}</p>
                                <p>P/E: {stock.pe}</p>
                              </div>

                              <div className="text-right text-sm text-gray-600 hidden lg:block">
                                <p>Market Cap</p>
                                <p className="font-medium">{stock.marketCap}</p>
                              </div>

                              <div className="flex items-center gap-3">
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                                >
                                  <Eye className="size-3 mr-1" />
                                  View
                                </Button>
                                <Button size="sm" variant="default">
                                  <BarChart3 className="size-3 mr-1" />
                                  Analyze
                                </Button>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      )
                    })}

                    {filteredStocks.length === 0 && (
                      <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="text-center py-12 text-gray-500"
                      >
                        <Search className="size-12 mx-auto mb-4 text-gray-300" />
                        <p className="text-lg font-medium mb-2">
                          No stocks found
                        </p>
                        <p>Try adjusting your search or filter criteria</p>
                      </motion.div>
                    )}
                  </div>
                </AnimatePresence>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Market Summary */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Market Summary</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">S&P 500</span>
                  <div className="text-right">
                    <p className="font-medium">4,567.89</p>
                    <p className="text-xs text-green-600">+0.85%</p>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">NASDAQ</span>
                  <div className="text-right">
                    <p className="font-medium">14,234.56</p>
                    <p className="text-xs text-green-600">+1.24%</p>
                  </div>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-gray-600">DOW</span>
                  <div className="text-right">
                    <p className="font-medium">34,890.12</p>
                    <p className="text-xs text-red-600">-0.32%</p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Sector Performance */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Sector Performance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {mockSectors.map((sector, index) => (
                  <div
                    key={sector.name}
                    className="flex justify-between items-center"
                  >
                    <span className="text-sm text-gray-600">{sector.name}</span>
                    <div
                      className={`flex items-center gap-1 text-sm ${
                        sector.trend === 'up'
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {sector.trend === 'up' ? (
                        <TrendingUp className="size-3" />
                      ) : (
                        <TrendingDown className="size-3" />
                      )}
                      <span className="font-medium">{sector.change}</span>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </motion.div>

          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.6 }}
          >
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Quick Actions</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  size="sm"
                >
                  <Activity className="size-4 mr-2" />
                  Watchlist
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  size="sm"
                >
                  <DollarSign className="size-4 mr-2" />
                  Portfolio
                </Button>
                <Button
                  variant="outline"
                  className="w-full justify-start"
                  size="sm"
                >
                  <BarChart3 className="size-4 mr-2" />
                  Screener
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      </div>

      {/* Stock Analysis Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Intraday Price Movement */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Intraday Price Movement</CardTitle>
              <CardDescription>
                Real-time price tracking for major stocks
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mockPriceHistory}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis dataKey="time" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip formatter={(value) => [`$${value}`, '']} />
                  <Line
                    type="monotone"
                    dataKey="AAPL"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    name="AAPL"
                  />
                  <Line
                    type="monotone"
                    dataKey="TSLA"
                    stroke="#ef4444"
                    strokeWidth={2}
                    name="TSLA"
                  />
                  <Line
                    type="monotone"
                    dataKey="MSFT"
                    stroke="#10b981"
                    strokeWidth={2}
                    name="MSFT"
                  />
                  <Line
                    type="monotone"
                    dataKey="NVDA"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    name="NVDA"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Volume Analysis */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Trading Volume Analysis</CardTitle>
              <CardDescription>
                Current vs average trading volume
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={mockVolumeData}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis dataKey="stock" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip
                    formatter={(value) => [
                      new Intl.NumberFormat().format(Number(value)),
                      ''
                    ]}
                  />
                  <Bar dataKey="avgVolume" fill="#e2e8f0" name="Avg Volume" />
                  <Bar dataKey="volume" fill="#3b82f6" name="Current Volume" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Risk vs Return Scatter Plot */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.9 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>Risk vs Return Analysis</CardTitle>
            <CardDescription>
              Portfolio positioning analysis (Risk % vs Return %, bubble size =
              Market Cap)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={400}>
              <ScatterChart data={mockRiskReturn}>
                <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                <XAxis
                  type="number"
                  dataKey="risk"
                  name="Risk %"
                  fontSize={12}
                  label={{
                    value: 'Risk %',
                    position: 'insideBottom',
                    offset: -10
                  }}
                />
                <YAxis
                  type="number"
                  dataKey="return"
                  name="Return %"
                  fontSize={12}
                  label={{
                    value: 'Return %',
                    angle: -90,
                    position: 'insideLeft'
                  }}
                />
                <Tooltip
                  formatter={(value, name) => [
                    name === 'risk'
                      ? `${value}%`
                      : name === 'return'
                        ? `${value}%`
                        : `$${value}B`,
                    name === 'risk'
                      ? 'Risk'
                      : name === 'return'
                        ? 'Return'
                        : 'Market Cap'
                  ]}
                  labelFormatter={(label, payload) => {
                    if (payload && payload.length > 0) {
                      return `${payload[0]?.payload?.stock || ''}`
                    }
                    return label
                  }}
                />
                <Scatter dataKey="marketCap" fill="#3b82f6" fillOpacity={0.7} />
              </ScatterChart>
            </ResponsiveContainer>
            <div className="mt-4 text-sm text-gray-600">
              <p>• Larger bubbles represent higher market capitalization</p>
              <p>• Top-right quadrant shows high return, high risk stocks</p>
              <p>• Bottom-left quadrant shows low return, low risk stocks</p>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

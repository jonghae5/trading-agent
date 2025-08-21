import React from 'react'
import { motion } from 'framer-motion'
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  BarChart3,
  Activity,
  ArrowUpRight,
  ArrowDownRight,
  Brain,
  Zap
} from 'lucide-react'
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell
} from 'recharts'

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '../components/ui/card'
import { Button } from '../components/ui/button'

// Mock data for dashboard
const mockStats = [
  {
    title: 'Portfolio Value',
    value: '$124,567.89',
    change: '+12.34%',
    changeType: 'positive' as const,
    icon: DollarSign
  },
  {
    title: 'Active Strategies',
    value: '8',
    change: '+2 this week',
    changeType: 'positive' as const,
    icon: Brain
  },
  {
    title: 'Success Rate',
    value: '87.2%',
    change: '+5.1%',
    changeType: 'positive' as const,
    icon: TrendingUp
  },
  {
    title: 'Daily P&L',
    value: '$2,456.78',
    change: '-1.2%',
    changeType: 'negative' as const,
    icon: Activity
  }
]

const mockTrades = [
  {
    symbol: 'AAPL',
    type: 'BUY',
    amount: '$5,000',
    profit: '+$234',
    time: '2 min ago'
  },
  {
    symbol: 'TSLA',
    type: 'SELL',
    amount: '$3,200',
    profit: '+$156',
    time: '5 min ago'
  },
  {
    symbol: 'MSFT',
    type: 'BUY',
    amount: '$4,500',
    profit: '+$98',
    time: '12 min ago'
  },
  {
    symbol: 'NVDA',
    type: 'SELL',
    amount: '$2,800',
    profit: '-$45',
    time: '18 min ago'
  }
]

const mockMarketData = [
  {
    name: 'S&P 500',
    value: '4,567.89',
    change: '+0.85%',
    changeType: 'positive' as const
  },
  {
    name: 'NASDAQ',
    value: '14,234.56',
    change: '+1.24%',
    changeType: 'positive' as const
  },
  {
    name: 'DOW',
    value: '34,890.12',
    change: '-0.32%',
    changeType: 'negative' as const
  },
  {
    name: 'VIX',
    value: '18.45',
    change: '-2.1%',
    changeType: 'negative' as const
  }
]

const mockAgentStatus = [
  { name: 'Momentum Scanner', status: 'active', trades: 12, profit: '+$456' },
  { name: 'Mean Reversion', status: 'active', trades: 8, profit: '+$234' },
  { name: 'Arbitrage Bot', status: 'paused', trades: 0, profit: '$0' },
  { name: 'Options Strategy', status: 'active', trades: 4, profit: '+$189' }
]

// Mock data for charts
const mockPortfolioData = [
  { date: '1/1', value: 100000, benchmark: 100000 },
  { date: '1/8', value: 102500, benchmark: 101200 },
  { date: '1/15', value: 98750, benchmark: 99800 },
  { date: '1/22', value: 105200, benchmark: 102100 },
  { date: '1/29', value: 108900, benchmark: 103500 },
  { date: '2/5', value: 112400, benchmark: 105200 },
  { date: '2/12', value: 118700, benchmark: 106800 },
  { date: '2/19', value: 124567, benchmark: 108900 }
]

const mockMarketTrendData = [
  { time: '9:30', spy: 456.2, qqq: 382.1, iwm: 198.4 },
  { time: '10:00', spy: 457.8, qqq: 383.5, iwm: 199.2 },
  { time: '10:30', spy: 459.1, qqq: 385.2, iwm: 200.8 },
  { time: '11:00', spy: 461.3, qqq: 387.8, iwm: 202.1 },
  { time: '11:30', spy: 463.7, qqq: 389.4, iwm: 201.5 },
  { time: '12:00', spy: 465.2, qqq: 391.2, iwm: 203.7 },
  { time: '12:30', spy: 467.9, qqq: 393.8, iwm: 205.2 },
  { time: '1:00', spy: 469.5, qqq: 395.1, iwm: 206.8 }
]

const mockAnalysisResults = [
  { analysis: 'Technical', bullish: 75, bearish: 25 },
  { analysis: 'Fundamental', bullish: 60, bearish: 40 },
  { analysis: 'Sentiment', bullish: 85, bearish: 15 },
  { analysis: 'Risk Assessment', bullish: 45, bearish: 55 }
]

const mockRiskDistribution = [
  { name: 'Low Risk', value: 35, color: '#10b981' },
  { name: 'Medium Risk', value: 45, color: '#f59e0b' },
  { name: 'High Risk', value: 20, color: '#ef4444' }
]

const mockTradingVolume = [
  { date: '1/15', volume: 1250000, trades: 45 },
  { date: '1/16', volume: 980000, trades: 38 },
  { date: '1/17', volume: 1580000, trades: 52 },
  { date: '1/18', volume: 1320000, trades: 41 },
  { date: '1/19', volume: 2100000, trades: 67 },
  { date: '1/22', volume: 1890000, trades: 59 },
  { date: '1/23', volume: 1650000, trades: 48 }
]

export const Dashboard: React.FC = () => {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Dashboard Overview
          </h1>
          <p className="text-gray-600 mt-1">
            Real-time insights into your AI trading performance
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline">
            <BarChart3 className="size-4 mr-2" />
            Export Report
          </Button>
          <Button>
            <Zap className="size-4 mr-2" />
            Run Analysis
          </Button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {mockStats.map((stat, index) => (
          <motion.div
            key={stat.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
          >
            <Card className="hover:shadow-md transition-shadow">
              <CardContent className="p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="p-2 bg-blue-50 rounded-lg">
                      <stat.icon className="size-5 text-blue-600" />
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">{stat.title}</p>
                      <p className="text-2xl font-bold text-gray-900">
                        {stat.value}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <div
                      className={`flex items-center gap-1 ${
                        stat.changeType === 'positive'
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {stat.changeType === 'positive' ? (
                        <ArrowUpRight className="size-4" />
                      ) : (
                        <ArrowDownRight className="size-4" />
                      )}
                      <span className="text-sm font-medium">{stat.change}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent Trades */}
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.4 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Recent Trades</CardTitle>
              <CardDescription>
                Latest trading activity from your AI agents
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {mockTrades.map((trade, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className={`px-2 py-1 rounded text-xs font-medium ${
                        trade.type === 'BUY'
                          ? 'bg-green-100 text-green-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {trade.type}
                    </div>
                    <div>
                      <p className="font-medium">{trade.symbol}</p>
                      <p className="text-sm text-gray-600">{trade.amount}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p
                      className={`font-medium ${
                        trade.profit.startsWith('+')
                          ? 'text-green-600'
                          : 'text-red-600'
                      }`}
                    >
                      {trade.profit}
                    </p>
                    <p className="text-xs text-gray-500">{trade.time}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>

        {/* Market Overview */}
        <motion.div
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.5 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Market Overview</CardTitle>
              <CardDescription>
                Current market conditions and indices
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {mockMarketData.map((market, index) => (
                <div key={index} className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{market.name}</p>
                    <p className="text-xl font-bold text-gray-900">
                      {market.value}
                    </p>
                  </div>
                  <div
                    className={`flex items-center gap-1 ${
                      market.changeType === 'positive'
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}
                  >
                    {market.changeType === 'positive' ? (
                      <TrendingUp className="size-4" />
                    ) : (
                      <TrendingDown className="size-4" />
                    )}
                    <span className="font-medium">{market.change}</span>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Portfolio Performance Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Portfolio Performance</CardTitle>
              <CardDescription>
                Portfolio value vs benchmark over time
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <AreaChart data={mockPortfolioData}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip
                    formatter={(value, name) => [
                      new Intl.NumberFormat('en-US', {
                        style: 'currency',
                        currency: 'USD'
                      }).format(Number(value)),
                      name === 'value' ? 'Portfolio' : 'Benchmark'
                    ]}
                  />
                  <Area
                    type="monotone"
                    dataKey="benchmark"
                    stackId="1"
                    stroke="#94a3b8"
                    fill="#e2e8f0"
                    fillOpacity={0.6}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stackId="2"
                    stroke="#3b82f6"
                    fill="#3b82f6"
                    fillOpacity={0.8}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Market Trends Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.7 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Intraday Market Trends</CardTitle>
              <CardDescription>
                Real-time ETF performance throughout the day
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={mockMarketTrendData}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis dataKey="time" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip formatter={(value) => [`$${value}`, '']} />
                  <Line
                    type="monotone"
                    dataKey="spy"
                    stroke="#ef4444"
                    strokeWidth={2}
                    name="SPY"
                  />
                  <Line
                    type="monotone"
                    dataKey="qqq"
                    stroke="#10b981"
                    strokeWidth={2}
                    name="QQQ"
                  />
                  <Line
                    type="monotone"
                    dataKey="iwm"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    name="IWM"
                  />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* AI Analysis Results */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>AI Analysis Results</CardTitle>
              <CardDescription>
                Bullish vs Bearish sentiment by analysis type
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={mockAnalysisResults}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis dataKey="analysis" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip formatter={(value) => [`${value}%`, '']} />
                  <Bar dataKey="bullish" fill="#10b981" name="Bullish" />
                  <Bar dataKey="bearish" fill="#ef4444" name="Bearish" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Risk Distribution */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.9 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Risk Distribution</CardTitle>
              <CardDescription>
                Portfolio risk allocation breakdown
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <PieChart>
                  <Pie
                    data={mockRiskDistribution}
                    cx="50%"
                    cy="50%"
                    outerRadius={80}
                    dataKey="value"
                    label={({ name, value }) => `${name}: ${value}%`}
                  >
                    {mockRiskDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [`${value}%`, '']} />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>

        {/* Trading Volume */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.0 }}
        >
          <Card>
            <CardHeader>
              <CardTitle>Trading Volume</CardTitle>
              <CardDescription>
                Daily trading volume and number of trades
              </CardDescription>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={mockTradingVolume}>
                  <CartesianGrid strokeDasharray="3 3" className="opacity-30" />
                  <XAxis dataKey="date" fontSize={12} />
                  <YAxis fontSize={12} />
                  <Tooltip
                    formatter={(value, name) => [
                      name === 'volume'
                        ? new Intl.NumberFormat().format(Number(value))
                        : value,
                      name === 'volume' ? 'Volume' : 'Trades'
                    ]}
                  />
                  <Bar dataKey="volume" fill="#3b82f6" name="Volume" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* AI Agent Status */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 1.1 }}
      >
        <Card>
          <CardHeader>
            <CardTitle>AI Trading Agents</CardTitle>
            <CardDescription>
              Monitor the performance of your automated trading strategies
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {mockAgentStatus.map((agent, index) => (
                <div
                  key={index}
                  className="p-4 border border-gray-200 rounded-lg"
                >
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-medium">{agent.name}</h3>
                    <div
                      className={`w-2 h-2 rounded-full ${
                        agent.status === 'active'
                          ? 'bg-green-500'
                          : 'bg-gray-400'
                      }`}
                    />
                  </div>
                  <div className="space-y-1 text-sm">
                    <div className="flex justify-between">
                      <span className="text-gray-600">Trades:</span>
                      <span className="font-medium">{agent.trades}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Profit:</span>
                      <span
                        className={`font-medium ${
                          agent.profit.startsWith('+')
                            ? 'text-green-600'
                            : agent.profit === '$0'
                              ? 'text-gray-600'
                              : 'text-red-600'
                        }`}
                      >
                        {agent.profit}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">Status:</span>
                      <span
                        className={`font-medium capitalize ${
                          agent.status === 'active'
                            ? 'text-green-600'
                            : 'text-gray-600'
                        }`}
                      >
                        {agent.status}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

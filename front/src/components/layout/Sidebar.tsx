import React from 'react'
import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Brain,
  History,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Shield,
  Activity,
  LogOut,
  Newspaper,
  PieChart
} from 'lucide-react'

import { useUIStore } from '../../stores/uiStore'
import { useAuthStore } from '../../stores/authStore'
import { cn } from '../../lib/utils'

interface NavigationItem {
  name: string
  href: string
  icon: React.ComponentType<{ className?: string }>
  description: string
}

const navigation: NavigationItem[] = [
  {
    name: '🧠 AI분석',
    href: '/analysis',
    icon: Brain,
    description: 'Run AI trading analysis'
  },
  {
    name: '📚 히스토리',
    href: '/history',
    icon: History,
    description: 'View analysis history'
  },
  {
    name: '📊 포트폴리오',
    href: '/portfolio',
    icon: PieChart,
    description: 'Portfolio optimization'
  },
  {
    name: '📰 뉴스',
    href: '/news',
    icon: Newspaper,
    description: 'Real-time financial news'
  },
  // {
  //   name: '📈 주식분석',
  //   href: '/stocks',
  //   icon: TrendingUp,
  //   description: 'Stock market analysis'
  // },
  {
    name: '📊 거시경제',
    href: '/economics',
    icon: BarChart3,
    description: 'Economic data and indicators'
  }
]

export const Sidebar: React.FC = () => {
  const { sidebarCollapsed, setSidebarCollapsed } = useUIStore()
  const { user, logout } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()

  // Default user for development
  const isDevelopment =
    import.meta.env.DEV || import.meta.env.MODE === 'development'
  const displayUser = user || (isDevelopment ? { username: 'Developer' } : null)

  const toggleSidebar = () => {
    setSidebarCollapsed(!sidebarCollapsed)
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div
      className={cn(
        'fixed inset-y-0 left-0 z-40 bg-white border-r border-gray-100 shadow-xl transition-all duration-300 ease-in-out',
        // Desktop
        'lg:translate-x-0',
        sidebarCollapsed ? 'lg:w-16' : 'lg:w-64',
        // Mobile
        sidebarCollapsed
          ? '-translate-x-full lg:translate-x-0'
          : 'w-64 translate-x-0',
        'lg:shadow-lg'
      )}
    >
      {/* Header */}
      <div className="flex h-16 items-center justify-between border-b border-gray-100 px-4">
        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-3 overflow-hidden"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-600 to-blue-700 shadow-sm">
                <Shield className="h-5 w-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">
                  TradingAgents
                </h1>
                <p className="text-xs text-gray-500">AI Dashboard</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Toggle Button */}
        <button
          onClick={toggleSidebar}
          className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-600 lg:flex hidden"
          title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {sidebarCollapsed ? (
            <ChevronRight className="h-4 w-4" />
          ) : (
            <ChevronLeft className="h-4 w-4" />
          )}
        </button>

        {/* Mobile Close Button */}
        <button
          onClick={toggleSidebar}
          className="rounded-lg p-1.5 text-gray-400 transition-colors hover:bg-gray-50 hover:text-gray-600 lg:hidden"
          title="Close sidebar"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
      </div>

      {/* User Info */}
      <div className="border-b border-gray-100 p-4">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-700 font-medium text-white shadow-sm">
            {displayUser?.username?.charAt(0)?.toUpperCase() || 'U'}
          </div>

          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
                className="min-w-0 flex-1 overflow-hidden"
              >
                <p className="truncate text-sm font-medium text-gray-900">
                  {displayUser?.username || 'Guest'}
                </p>
                <div className="flex items-center gap-1">
                  <Activity className="h-3 w-3 text-emerald-500" />
                  <span className="text-xs text-emerald-600">Active</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-4">
        {navigation.map((item) => {
          const isActive = location.pathname === item.href

          return (
            <NavLink
              key={item.name}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'group relative flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200',
                  isActive
                    ? 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 shadow-sm ring-1 ring-blue-100'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )
              }
              title={sidebarCollapsed ? item.name : undefined}
            >
              <item.icon
                className={cn(
                  'h-5 w-5 flex-shrink-0 transition-colors',
                  isActive
                    ? 'text-blue-600'
                    : 'text-gray-400 group-hover:text-gray-600'
                )}
              />

              <AnimatePresence>
                {!sidebarCollapsed && (
                  <motion.div
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    transition={{ duration: 0.2 }}
                    className="ml-3 overflow-hidden"
                  >
                    <span className="truncate">{item.name}</span>
                    <p className="mt-0.5 truncate text-xs text-gray-500">
                      {item.description}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Active Indicator */}
              {isActive && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute right-2 h-6 w-1 rounded-full bg-blue-600"
                  transition={{ type: 'spring', bounce: 0.2, duration: 0.6 }}
                />
              )}
            </NavLink>
          )
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-100 p-4 space-y-3">
        {/* Logout Button */}
        <button
          onClick={handleLogout}
          className={cn(
            'group relative flex items-center rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-200 w-full',
            'text-red-600 hover:bg-red-50 hover:text-red-700'
          )}
          title={sidebarCollapsed ? '로그아웃' : undefined}
        >
          <LogOut className="h-5 w-5 flex-shrink-0 transition-colors text-red-500 group-hover:text-red-600" />

          <AnimatePresence>
            {!sidebarCollapsed && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                transition={{ duration: 0.2 }}
                className="ml-3 overflow-hidden truncate"
              >
                로그아웃
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        <AnimatePresence>
          {!sidebarCollapsed && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden text-center text-xs text-gray-400"
            >
              <p>Version 1.0.0</p>
              <p className="mt-1">© 2024 TradingAgents</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}

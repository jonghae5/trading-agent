import React from 'react'
import { Outlet } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Toaster } from 'react-hot-toast'

import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { SessionManager } from '../auth/SessionManager'

import { useUIStore } from '../../stores/uiStore'
import { useAuthStore } from '../../stores/authStore'
import { cn } from '../../lib/utils'

export const DashboardLayout: React.FC = () => {
  const { sidebarCollapsed } = useUIStore()
  const { isAuthenticated } = useAuthStore()

  return (
    <div className="min-h-screen bg-white">
      {/* Mobile Backdrop */}
      {!sidebarCollapsed && (
        <div
          className="fixed inset-0 z-30 bg-black/50 lg:hidden"
          onClick={() => useUIStore.getState().setSidebarCollapsed(true)}
        />
      )}

      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div
        className={cn(
          'transition-all duration-300 ease-in-out min-h-screen',
          // Desktop sidebar spacing
          'lg:ml-64',
          sidebarCollapsed && 'lg:ml-16',
          // Mobile: full width when sidebar is collapsed
          'ml-0'
        )}
      >
        {/* Header */}
        <Header />

        {/* Page Content */}
        <main className="p-3 sm:p-4 md:p-6">
          <motion.div
            key="dashboard-content"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3 }}
            className="max-w-full overflow-hidden"
          >
            <Outlet />
          </motion.div>
        </main>

        {/* Session Manager - Floating */}
        <div className="fixed bottom-4 right-4 z-50 sm:bottom-6 sm:right-6">
          <SessionManager compact />
        </div>
      </div>

      {/* Global Toast Notifications */}
      <Toaster
        position="top-right"
        toastOptions={{
          duration: 4000,
          className: 'bg-white text-gray-900 border border-gray-200 shadow-lg',
          style: {
            background: '#ffffff',
            color: '#111827',
            border: '1px solid #e5e7eb',
            borderRadius: '8px',
            boxShadow:
              '0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)'
          }
        }}
      />
    </div>
  )
}

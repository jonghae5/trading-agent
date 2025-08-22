import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { DashboardLayout } from './layout/DashboardLayout'
import { ProtectedRoute } from './ProtectedRoute'
import { Login } from '../pages/Login'
import { Analysis } from '../pages/Analysis'
import { History } from '../pages/History'
import { Stocks } from '../pages/Stocks'
import { Economics } from '../pages/Economics'
import { News } from '../pages/News'
import { useAuthStore } from '../stores/authStore'
import { initStorageErrorHandling } from '../utils/storage'

function App() {
  const { isLoading, initializeAuth } = useAuthStore()

  // Initialize auth and storage error handling
  useEffect(() => {
    initStorageErrorHandling()

    // Initialize auth state - 쿠키에서 인증 상태를 확인
    initializeAuth()
  }, [initializeAuth])

  // Show loading screen during auth initialization
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-2 text-sm text-gray-600 dark:text-gray-400">
            Loading...
          </p>
        </div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        {/* Login route - outside of DashboardLayout */}
        <Route path="/login" element={<Login />} />

        <Route path="/" element={<DashboardLayout />}>
          {/* Default route redirects to AI Analysis */}
          <Route index element={<Navigate to="/analysis" replace />} />

          {/* Main 4 tabs matching streamlit structure */}
          <Route
            path="analysis"
            element={
              <ProtectedRoute>
                <Analysis />
              </ProtectedRoute>
            }
          />
          <Route path="history" element={<History />} />
          <Route path="news" element={<News />} />
          <Route path="stocks" element={<Stocks />} />
          <Route path="economics" element={<Economics />} />

          {/* Catch all route */}
          <Route path="*" element={<Navigate to="/analysis" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App

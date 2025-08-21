import React, { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { LoginForm } from '../components/auth/LoginForm'
import { useAuthStore } from '../stores/authStore'

export const Login: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    // 이미 인증된 사용자라면 원래 경로로 리다이렉트
    if (!isLoading && isAuthenticated) {
      const from = (location.state as { from?: string })?.from || '/analysis'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, isLoading, navigate, location.state])

  // 인증 상태 확인 중일 때 로딩 화면
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 dark:text-gray-400">Checking authentication...</p>
        </div>
      </div>
    )
  }

  // 인증되지 않은 사용자에게만 로그인 폼 표시
  if (!isAuthenticated) {
    return <LoginForm />
  }

  // 인증된 사용자는 리다이렉트 중
  return null
}
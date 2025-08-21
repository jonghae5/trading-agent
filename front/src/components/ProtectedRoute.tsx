import React, { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '../stores/authStore'

interface ProtectedRouteProps {
  children: React.ReactNode
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuthStore()
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    // 인증 초기화가 완료된 후에만 리다이렉트 수행
    if (!isLoading && !isAuthenticated) {
      // 현재 경로를 state로 저장하여 로그인 후 돌아올 수 있도록 함
      navigate('/login', {
        replace: true,
        state: { from: location.pathname }
      })
    }
  }, [isAuthenticated, isLoading, navigate, location.pathname])

  // 인증 상태 확인 중이거나 로그인되지 않은 경우 로딩 화면 표시
  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">
            {isLoading ? 'Checking authentication...' : 'Redirecting to login...'}
          </p>
        </div>
      </div>
    )
  }

  // 로그인된 경우에만 자식 컴포넌트 렌더링
  return <>{children}</>
}

import React, { useState, useCallback } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { motion, AnimatePresence } from 'framer-motion'
import { Eye, EyeOff, AlertCircle, Shield } from 'lucide-react'
import { useNavigate, useLocation } from 'react-router-dom'

import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Label } from '../ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { useAuthStore } from '../../stores/authStore'

const loginSchema = z.object({
  username: z
    .string()
    .min(1, '아이디를 입력해주세요')
    .max(50, '아이디는 50자 미만이어야 합니다'),
  password: z.string().min(1, '비밀번호를 입력해주세요')
})

type LoginFormData = z.infer<typeof loginSchema>

export const LoginForm: React.FC = () => {
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const location = useLocation()

  const { login, isLoading } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
    reset
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema)
  })

  const togglePasswordVisibility = useCallback(() => {
    setShowPassword(prev => !prev)
  }, [])

  const onSubmit = useCallback(
    async (data: LoginFormData) => {
      setError(null)

      try {
        const success = await login(data.username, data.password)

        if (success) {
          reset()
          // 로그인 성공 후 원래 경로로 돌아가기 (없으면 기본 경로로)
          const from =
            (location.state as { from?: string })?.from || '/analysis'
          navigate(from, { replace: true })
        } else {
          setError('아이디 또는 비밀번호가 틀렸습니다')
        }
      } catch (err) {
        setError('로그인 중 오류가 발생했습니다')
      }
    },
    [login, reset, location.state, navigate]
  )

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-50 via-white to-slate-100 dark:from-gray-900 dark:to-gray-800 p-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >
        {/* Header */}
        <div className="text-center mb-8">
          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.1 }}
            className="mb-6"
          >
            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-2xl shadow-xl">
              <Shield className="w-10 h-10 text-white" />
            </div>
          </motion.div>

          <motion.h1
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="text-3xl font-bold text-gray-900 dark:text-white mb-2"
          >
            TradingAgents
          </motion.h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            AI 기반 투자 분석 플랫폼
          </p>
        </div>

        {/* Login Card */}
        <Card className="border-0 shadow-xl">
          <CardContent className="pt-6">
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* Username Field */}
              <div className="space-y-2">
                <Label htmlFor="username" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  아이디
                </Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="아이디"
                  error={errors.username?.message}
                  disabled={isLoading || isSubmitting}
                  {...register('username')}
                  className="h-11"
                />
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <Label htmlFor="password" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  비밀번호
                </Label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="비밀번호"
                    error={errors.password?.message}
                    disabled={isLoading || isSubmitting}
                    {...register('password')}
                    className="pr-10 h-11"
                  />
                  <button
                    type="button"
                    onClick={togglePasswordVisibility}
                    disabled={isLoading || isSubmitting}
                    className="absolute inset-y-0 right-0 flex items-center pr-3 text-gray-400 hover:text-gray-600 disabled:opacity-50 transition-colors"
                    aria-label={showPassword ? '비밀번호 숨기기' : '비밀번호 보기'}
                  >
                    {showPassword ? (
                      <EyeOff className="w-5 h-5" />
                    ) : (
                      <Eye className="w-5 h-5" />
                    )}
                  </button>
                </div>
              </div>

              {/* Error Message */}
              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
                  >
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-600 flex-shrink-0" />
                      <p className="text-sm text-red-700 dark:text-red-300">
                        {error}
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full h-11 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium shadow-lg hover:shadow-xl transition-all"
                disabled={isLoading || isSubmitting}
                loading={isLoading || isSubmitting}
              >
                {isLoading || isSubmitting ? '로그인 중...' : '로그인'}
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Footer Note */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="mt-6 text-center"
        >
          <p className="text-xs text-gray-500 dark:text-gray-400">
            보안 연결로 안전하게 보호됩니다
          </p>
        </motion.div>
      </motion.div>
    </div>
  )
}

import { create } from 'zustand'
import { authApi, apiClient } from '../api'

interface User {
  id: number
  username: string
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

interface AuthActions {
  login: (username: string, password: string) => Promise<boolean>
  logout: () => Promise<void>
  checkAuth: () => Promise<void>
  initializeAuth: () => void
}

type AuthStore = AuthState & AuthActions

export const useAuthStore = create<AuthStore>()((set, get) => ({
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: false,

  login: async (username: string, password: string) => {
    set({ isLoading: true })

    try {
      const loginResponse = await authApi.login({ username, password })

      // Get user info - 쿠키가 자동으로 포함됨
      const user = await authApi.getCurrentUser()

      set({
        user: user,
        token: loginResponse.access_token,
        isAuthenticated: true,
        isLoading: false
      })

      return true
    } catch (error) {
      set({ isLoading: false })
      return false
    }
  },

  logout: async () => {
    try {
      await authApi.logout()
    } catch (error) {
      console.warn('Logout API call failed:', error)
    }

    set({
      user: null,
      token: null,
      isAuthenticated: false,
      isLoading: false
    })
  },

  checkAuth: async () => {
    try {
      const user = await authApi.getCurrentUser()
      set({
        user: user,
        isAuthenticated: true
      })
    } catch (error) {
      set({
        user: null,
        token: null,
        isAuthenticated: false
      })
    }
  },

  initializeAuth: () => {
    set({ isLoading: true })
    get()
      .checkAuth()
      .finally(() => {
        set({ isLoading: false })
      })
  }
}))

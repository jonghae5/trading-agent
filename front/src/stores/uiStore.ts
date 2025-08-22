import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { Theme } from '../types'
import { getKSTDate } from '../lib/utils'

interface UIState {
  theme: Theme
  sidebarCollapsed: boolean
  autoRefresh: boolean
  notifications: boolean
  loading: Record<string, boolean>
  toasts: Toast[]
}

interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  title: string
  message?: string
  duration?: number
  timestamp: Date
}

interface UIActions {
  setTheme: (theme: Theme) => void
  toggleTheme: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  toggleSidebar: () => void
  setAutoRefresh: (enabled: boolean) => void
  setNotifications: (enabled: boolean) => void
  setLoading: (key: string, loading: boolean) => void
  clearLoading: (key: string) => void
  addToast: (toast: Omit<Toast, 'id' | 'timestamp'>) => void
  removeToast: (id: string) => void
  clearToasts: () => void
  showSuccess: (title: string, message?: string) => void
  showError: (title: string, message?: string) => void
  showWarning: (title: string, message?: string) => void
  showInfo: (title: string, message?: string) => void
}

type UIStore = UIState & UIActions

const initialState: UIState = {
  theme: Theme.LIGHT,
  sidebarCollapsed: window.innerWidth < 1024, // Collapse on mobile by default
  autoRefresh: true,
  notifications: true,
  loading: {},
  toasts: []
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      ...initialState,

      setTheme: (theme) => {
        set({ theme })

        // Update document class for theme
        document.documentElement.classList.remove('light', 'dark')
        document.documentElement.classList.add(theme)
      },

      toggleTheme: () => {
        const currentTheme = get().theme
        const newTheme = currentTheme === Theme.LIGHT ? Theme.DARK : Theme.LIGHT
        get().setTheme(newTheme)
      },

      setSidebarCollapsed: (collapsed) => {
        set({ sidebarCollapsed: collapsed })
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
      },

      setAutoRefresh: (enabled) => {
        set({ autoRefresh: enabled })
      },

      setNotifications: (enabled) => {
        set({ notifications: enabled })
      },

      setLoading: (key, loading) => {
        set((state) => ({
          loading: {
            ...state.loading,
            [key]: loading
          }
        }))
      },

      clearLoading: (key) => {
        set((state) => {
          const newLoading = { ...state.loading }
          delete newLoading[key]
          return { loading: newLoading }
        })
      },

      addToast: (toast) => {
        const id = Math.random().toString(36).substr(2, 9)
        const newToast: Toast = {
          ...toast,
          id,
          timestamp: getKSTDate(),
          duration: toast.duration ?? 5000
        }

        set((state) => ({
          toasts: [...state.toasts, newToast]
        }))

        // Auto-remove toast after duration
        if (
          newToast.duration &&
          typeof newToast.duration === 'number' &&
          newToast.duration > 0
        ) {
          setTimeout(() => {
            get().removeToast(id)
          }, newToast.duration)
        }
      },

      removeToast: (id) => {
        set((state) => ({
          toasts: state.toasts.filter((toast) => toast.id !== id)
        }))
      },

      clearToasts: () => {
        set({ toasts: [] })
      },

      showSuccess: (title, message) => {
        get().addToast({
          type: 'success',
          title,
          message,
          duration: 4000
        })
      },

      showError: (title, message) => {
        get().addToast({
          type: 'error',
          title,
          message,
          duration: 6000
        })
      },

      showWarning: (title, message) => {
        get().addToast({
          type: 'warning',
          title,
          message,
          duration: 5000
        })
      },

      showInfo: (title, message) => {
        get().addToast({
          type: 'info',
          title,
          message,
          duration: 4000
        })
      }
    }),
    {
      name: 'ui-preferences',
      version: 1,
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        autoRefresh: state.autoRefresh,
        notifications: state.notifications
      }),
      onRehydrateStorage: () => (state) => {
        // Handle any rehydration errors gracefully
        if (state) {
          // Ensure theme is applied to DOM
          document.documentElement.classList.remove('light', 'dark')
          document.documentElement.classList.add(state.theme)

          // Force re-render to ensure UI reflects persisted state
          console.log('UI state rehydrated:', {
            theme: state.theme,
            autoRefresh: state.autoRefresh,
            sidebarCollapsed: state.sidebarCollapsed,
            notifications: state.notifications
          })
        }
      },
      skipHydration: false
    }
  )
)

// Initialize theme and ensure hydration on store creation
const initializeStore = () => {
  const state = useUIStore.getState()
  document.documentElement.classList.add(state.theme)

  // Ensure proper hydration by triggering a state update
  setTimeout(() => {
    const currentState = useUIStore.getState()
    console.log('Store initialized with state:', {
      theme: currentState.theme,
      autoRefresh: currentState.autoRefresh,
      sidebarCollapsed: currentState.sidebarCollapsed
    })
  }, 0)
}

initializeStore()

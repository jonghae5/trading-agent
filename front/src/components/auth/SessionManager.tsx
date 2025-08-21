import React from 'react'
import { LogOut, Shield } from 'lucide-react'

import { Button } from '../ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card'

import { useAuthStore } from '../../stores/authStore'

interface SessionManagerProps {
  compact?: boolean
}

export const SessionManager: React.FC<SessionManagerProps> = ({
  compact = false
}) => {
  const { user, logout } = useAuthStore()

  const handleLogout = () => {
    logout()
  }

  if (!user) return null

  if (compact) {
    return (
      <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        {/* User Avatar */}
        <div className="flex items-center justify-center w-8 h-8 bg-blue-600 rounded-full text-white text-sm font-medium">
          {user.username.charAt(0).toUpperCase()}
        </div>

        {/* User Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
            {user.username}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            Authenticated
          </p>
        </div>

        {/* Logout Button */}
        <Button
          variant="ghost"
          size="icon"
          onClick={handleLogout}
          className="h-8 w-8"
          title="Logout"
        >
          <LogOut className="w-4 h-4" />
        </Button>
      </div>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2 text-sm">
          <Shield className="w-4 h-4" />
          User Information
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* User Information */}
        <div className="flex items-center gap-3">
          <div className="flex items-center justify-center w-10 h-10 bg-blue-600 rounded-full text-white font-medium">
            {user.username.charAt(0).toUpperCase()}
          </div>
          <div>
            <p className="font-medium text-gray-900 dark:text-white">
              {user.username}
            </p>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Authenticated User
            </p>
          </div>
        </div>

        {/* Action Button */}
        <Button
          variant="destructive"
          size="sm"
          onClick={handleLogout}
          className="w-full"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Logout
        </Button>
      </CardContent>
    </Card>
  )
}

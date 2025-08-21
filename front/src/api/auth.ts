/**
 * Simple authentication API
 */

import { apiClient } from './client'
import { API_BASE_URL } from '../lib/constants'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface User {
  id: number
  username: string
}

export const authApi = {
  async login(credentials: LoginRequest): Promise<LoginResponse> {
    // Create FormData for OAuth2 endpoint
    const formData = new FormData()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      body: formData,
      credentials: 'include' // 쿠키를 포함하여 요청
    })

    if (!response.ok) {
      throw new Error('Login failed')
    }

    return await response.json()
  },

  async getCurrentUser(): Promise<User> {
    return await apiClient.get<User>('/api/v1/auth/me')
  },

  async logout(): Promise<void> {
    await apiClient.post('/api/v1/auth/logout')
  }
}

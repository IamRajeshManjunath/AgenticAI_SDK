'use client'

import { useEffect, useState, ReactNode } from 'react'
import { useRouter } from 'next/navigation'
import { useAuthStore } from '@/lib/auth-store'

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const { token, refreshToken, loadSession, logout } = useAuthStore()
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    // Load session on mount
    const init = async () => {
      // Check if we have a refresh token but no access token
      const authStore = useAuthStore.getState()
      if (authStore.refreshToken && !authStore.token) {
        try {
          await authStore.refreshAccessToken()
        } catch {
          // Refresh failed, user will need to login
        }
      }
      setInitialized(true)
    }
    init()
  }, [])

  // Handle 401 responses globally
  useEffect(() => {
    const originalFetch = window.fetch
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const response = await originalFetch(input, init)
      
      if (response.status === 401) {
        const authStore = useAuthStore.getState()
        if (authStore.refreshToken) {
          try {
            await authStore.refreshAccessToken()
            // Retry the original request
            const authStore2 = useAuthStore.getState()
            const newInit = {
              ...init,
              headers: {
                ...init?.headers,
                'Authorization': `Bearer ${useAuthStore.getState().token}`,
              },
            }
            return window.fetch(input, newInit)
          } catch {
            // Refresh failed, logout
            useAuthStore.getState().logout()
            window.location.href = '/login'
          }
        } else {
          // No refresh token, redirect to login
          useAuthStore.getState().logout()
          window.location.href = '/login'
        }
      }
      return response
    }

    return () => {
      window.fetch = originalFetch
    }
  }, [])

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent"></div>
      </div>
    )
  }

  return <>{children}</>
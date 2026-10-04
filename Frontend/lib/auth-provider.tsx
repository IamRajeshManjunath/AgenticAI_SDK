'use client'

import { useEffect, useState, type ReactNode } from 'react'
import { useAuthStore } from '@/lib/auth-store'

export function AuthProvider({ children }: { children: ReactNode }) {
  const loadSession = useAuthStore((state) => state.loadSession)
  const [initialized, setInitialized] = useState(false)

  useEffect(() => {
    let mounted = true
    void loadSession().finally(() => {
      if (mounted) setInitialized(true)
    })

    return () => {
      mounted = false
    }
  }, [loadSession])

  useEffect(() => {
    const originalFetch = window.fetch.bind(window)

    window.fetch = async (input, init) => {
      const response = await originalFetch(input, init)
      const requestUrl = input instanceof Request ? input.url : String(input)
      if (
        response.status !== 401 ||
        requestUrl.endsWith('/auth/login') ||
        requestUrl.endsWith('/auth/register') ||
        requestUrl.endsWith('/auth/refresh')
      ) {
        return response
      }

      const authStore = useAuthStore.getState()
      if (!authStore.refreshToken) {
        authStore.logout()
        window.location.assign('/login')
        return response
      }

      const accessToken = await authStore.refreshAccessToken()
      if (!accessToken) {
        window.location.assign('/login')
        return response
      }

      const headers = new Headers(input instanceof Request ? input.headers : undefined)
      new Headers(init?.headers).forEach((value, key) => headers.set(key, value))
      headers.set('Authorization', `Bearer ${accessToken}`)
      return originalFetch(input, { ...init, headers })
    }

    return () => {
      window.fetch = originalFetch
    }
  }, [])

  if (!initialized) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-4 border-primary border-t-transparent" />
      </div>
    )
  }

  return <>{children}</>
}

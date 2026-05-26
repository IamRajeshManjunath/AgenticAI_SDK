'use client'

import { useEffect, type ReactNode } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useAuthStore } from './auth-store'

const PUBLIC_PATHS = ['/login', '/register', '/landing', '/blog', '/templates']

const PUBLIC_PREFIXES = ['/blog/', '/templates/']

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_PATHS.includes(pathname)) return true
  return PUBLIC_PREFIXES.some((prefix) => pathname.startsWith(prefix))
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const { token, user, isLoading } = useAuthStore()
  const pathname = usePathname()
  const router = useRouter()

  const isPublic = isPublicPath(pathname)

  useEffect(() => {
    if (isLoading) return
    if (!isPublic && !token) {
      router.push('/login')
    }
    if (isPublic && token && user) {
      router.push('/')
    }
  }, [token, user, isLoading, isPublic, pathname, router])

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  if (!isPublic && !token) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return <>{children}</>
}

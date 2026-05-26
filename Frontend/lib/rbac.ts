import { useAuthStore } from './auth-store'
import type { UserRole } from './types'

export interface RBACInfo {
  role: UserRole | null
  isAdmin: boolean
  isEditor: boolean
  isViewer: boolean
  canEdit: boolean
  canAdmin: boolean
  canView: boolean
}

export function useRBAC(): RBACInfo {
  const user = useAuthStore((s) => s.user)
  const role: UserRole | null = null

  return {
    role,
    isAdmin: role === 'admin',
    isEditor: role === 'editor',
    isViewer: role === 'viewer',
    canEdit: role === 'admin' || role === 'editor',
    canAdmin: role === 'admin',
    canView: true,
  }
}

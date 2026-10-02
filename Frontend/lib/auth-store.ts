import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthState, AuthResponse, LoginCredentials, RegisterCredentials, User } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface AuthStore extends AuthState {
  apiKey: string | null
  refreshToken: string | null
  login: (credentials: LoginCredentials) => Promise<void>
  register: (credentials: RegisterCredentials) => Promise<void>
  logout: () => void
  clearError: () => void
  setUser: (user: User) => void
  setWorkspaceId: (workspaceId: string) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  setApiKey: (apiKey: string) => void
  refreshAccessToken: () => Promise<string | null>
  loadSession: () => Promise<void>
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      refreshToken: null,
      apiKey: null,
      workspaceId: null,
      isLoading: false,
      error: null,

      login: async (credentials) => {
        set({ isLoading: true, error: null })
        try {
          const res = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials),
          })
          if (!res.ok) {
            const err = await res.json()
            throw new Error(err.detail || 'Login failed')
          }
          const data = await res.json()
          set({
            user: data.user,
            token: data.access_token,
            refreshToken: data.refresh_token,
            workspaceId: data.user.default_workspace_id,
            isLoading: false,
            error: null,
          })
        } catch (err) {
          set({
            isLoading: false,
            error: err instanceof Error ? err.message : 'Login failed',
          })
          throw err
        }
      },

      register: async (credentials) => {
        set({ isLoading: true, error: null })
        try {
          const res = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(credentials),
          })
          if (!res.ok) {
            const err = await res.json()
            throw new Error(err.detail || 'Registration failed')
          }
          const data = await res.json()
          set({
            user: data.user,
            token: data.access_token,
            refreshToken: data.refresh_token,
            workspaceId: data.user.default_workspace_id,
            isLoading: false,
            error: null,
          })
        } catch (err) {
          set({
            isLoading: false,
            error: err instanceof Error ? err.message : 'Registration failed',
          })
          throw err
        }
      },

      logout: () => {
        set({ user: null, token: null, refreshToken: null, apiKey: null, workspaceId: null, error: null })
      },

      clearError: () => set({ error: null }),

      setUser: (user) => set({ user }),

      setWorkspaceId: (workspaceId) => set({ workspaceId }),

      setTokens: (accessToken, refreshToken) => {
        set({ token: accessToken, refreshToken })
      },

      setApiKey: (apiKey) => set({ apiKey }),

      refreshAccessToken: async () => {
        const refreshToken = get().refreshToken
        if (!refreshToken) return null

        try {
          const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
          })

          if (!res.ok) {
            get().logout()
            return null
          }

          const data = await res.json()
          set({
            token: data.access_token,
            refreshToken: data.refresh_token,
          })
          return data.access_token
        } catch {
          get().logout()
          return null
        }
      },

      loadSession: async () => {
        // Try to refresh token on app load if we have a refresh token
        const { refreshToken, token } = get()
        if (refreshToken && !token) {
          await get().refreshAccessToken()
        }
      },
    }),
    {
      name: 'agenticai-auth-store',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        apiKey: state.apiKey,
        workspaceId: state.workspaceId,
      }),
    }
  )
)
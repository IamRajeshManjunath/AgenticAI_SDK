import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { AuthState, AuthResponse, LoginCredentials, RegisterCredentials, User } from './types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface AuthStore extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>
  register: (credentials: RegisterCredentials) => Promise<void>
  logout: () => void
  clearError: () => void
  setUser: (user: User) => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      token: null,
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
          const data: AuthResponse = await res.json()
          set({
            user: data.user,
            token: data.access_token,
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
          const data: AuthResponse = await res.json()
          set({
            user: data.user,
            token: data.access_token,
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
        set({ user: null, token: null, error: null })
      },

      clearError: () => set({ error: null }),

      setUser: (user) => set({ user }),
    }),
    {
      name: 'agenticai-auth-store',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
      }),
    }
  )
)

import { useAuthStore } from './auth-store'
import { useRouter } from 'next/navigation'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

// Token refresh state
let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null

export interface ApiResponse<T> {
  data?: T
  error?: string
}

function getAuthHeaders(): Record<string, string> {
  const state = useAuthStore.getState()
  const token = state.token
  const apiKey = state.apiKey
  const workspaceId = state.workspaceId
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  
  if (state.token) {
    headers['Authorization'] = `Bearer ${state.token}`
  }
  if (state.apiKey) {
    headers['X-API-Key'] = state.apiKey
  }
  if (state.workspaceId) {
    headers['X-Workspace-ID'] = state.workspaceId
  }
  return headers
}

let isRefreshing = false
let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, logout } = useAuthStore.getState()
  if (!refreshToken) {
    return null
  }

  // Prevent multiple simultaneous refresh attempts
  if (isRefreshing) {
    return refreshPromise!
  }

  isRefreshing = true
  refreshPromise = (async () => {
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: useAuthStore.getState().refreshToken }),
      })

      if (!res.ok) {
        // Refresh failed - logout user
        const { logout } = useAuthStore.getState()
        logout()
        if (typeof window !== 'undefined') {
          window.location.href = '/login'
        }
        return null
      }

      const data = await res.json()
      const { setTokens } = useAuthStore.getState()
      setTokens(data.access_token, data.refresh_token)
      return data.access_token
    } catch {
      const { logout } = useAuthStore.getState()
      logout()
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
      return null
    } finally {
      // This will be set to false in the finally block of the caller
    }
  })()

  return refreshPromise
}

export interface ApiResponse<T> {
  data?: T
  error?: string
}

async function fetchWithAuth<T>(
  endpoint: string,
  options: RequestInit = {},
  retryCount = 0
): Promise<{ data?: T; error?: string }> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  
  const makeRequest = async (): Promise<Response> => {
    const headers = {
      'Content-Type': 'application/json',
      ...(typeof window !== 'undefined' ? {
        'Authorization': `Bearer ${useAuthStore.getState().token}`,
        'X-API-Key': useAuthStore.getState().apiKey || '',
        'X-Workspace-ID': useAuthStore.getState().workspaceId || '',
      } : {}),
    }

    return fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  try {
    const authHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    
    const state = typeof window !== 'undefined' ? useAuthStore.getState() : { token: null, apiKey: null, workspaceId: null }
    if (state.token) {
      headers['Authorization'] = `Bearer ${state.token}`
    }
    if (state.apiKey) {
      headers['X-API-Key'] = state.apiKey
    }
    if (state.workspaceId) {
      headers['X-Workspace-ID'] = state.workspaceId
    }

    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })

    // Handle 401 - try to refresh token and retry once
    if (response.status === 401) {
      // Try to refresh token
      const newToken = await refreshAccessToken()
      if (newToken) {
        // Retry the request with new token
        return fetchWithAuth(endpoint, options, retryCount + 1)
      }
    }

    if (!response.ok) {
      const error = await response.text()
      return { error: error || `HTTP error ${response.status}` }
    }

    if (response.status === 204) {
      return { data: undefined as any }
    }

    const data = await response.json()
    return { data }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' }
  }

async function refreshAccessToken(): Promise<string | null> {
  const refreshToken = useAuthStore.getState().refreshToken
  if (!refreshToken) return null

  try {
    const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/refresh`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: useAuthStore.getState().refreshToken }),
    })

    if (!res.ok) {
      const { logout } = useAuthStore.getState()
      logout()
      if (typeof window !== 'undefined') {
        window.location.href = '/login'
      }
      return null
    }

    const data = await res.json()
    const { setTokens } = useAuthStore.getState()
    setTokens(data.access_token, data.refresh_token)
    return data.access_token
  } catch {
    const { logout } = useAuthStore.getState()
    logout()
    if (typeof window !== 'undefined') {
      window.location.href = '/login'
    }
    return null
  }
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
  retryCount = 0
): Promise<{ data?: T; error?: string }> {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  
  const getAuthHeaders = (): Record<string, string> => {
    const state = useAuthStore.getState()
    const headers: Record<string, string> = {}
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`
    if (state.apiKey) headers['X-API-Key'] = state.apiKey
    if (state.workspaceId) headers['X-Workspace-ID'] = state.workspaceId
    return headers
  }

  const makeRequest = async (): Promise<Response> => {
    return fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...getAuthHeaders(),
        ...options.headers,
      },
    })
  }

  try {
    const response = await makeRequest()

    // Handle 401 - try to refresh token and retry once
    if (response.status === 401 && retryCount === 0) {
      const newToken = await refreshAccessToken()
      if (newToken) {
        return fetchApi(endpoint, options, retryCount + 1)
      }
    }

    if (!response.ok) {
      const error = await response.text()
      return { error: error || `HTTP error ${response.status}` }
    }

    if (response.status === 204) {
      return { data: undefined as T }
    }

    const data = await response.json()
    return { data }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' }
  }
}

// Typed API responses
export interface ApiResponse<T> {
  data?: T
  error?: string
}

export interface WorkflowRunResponse {
  trace_id: string
  status: 'started' | 'running' | 'completed' | 'failed'
}

export interface HITLApprovalRequest {
  agent_id: string
  action: 'approve' | 'reject'
  feedback?: string
}

export interface TraceResponse {
  spans: any[]
}

export interface MetricsResponse {
  token_usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  latency_ms: number
  cost: number
  consensus_score?: number
}

// Config types
export interface ConfigResponse {
  platform: Record<string, unknown>
  integrations: Record<string, unknown>
  version: string
  last_modified?: string
}

export interface ConfigUpdateRequest {
  config: Record<string, unknown>
  merge_strategy?: 'json_merge' | 'id_aware' | 'replace'
}

export interface ConfigSchemaResponse {
  type: string
  properties: Record<string, unknown>
  required: string[]
}

export { fetchApi }
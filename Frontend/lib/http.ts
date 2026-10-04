import { useAuthStore } from './auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

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
  spans: unknown[]
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

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  const { refreshToken, logout, setTokens } = useAuthStore.getState()
  if (!refreshToken) return null

  if (!refreshPromise) {
    refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken }),
        })

        if (!response.ok) {
          logout()
          return null
        }

        const data: { access_token: string; refresh_token: string } = await response.json()
        setTokens(data.access_token, data.refresh_token)
        return data.access_token
      } catch {
        logout()
        return null
      } finally {
        refreshPromise = null
      }
    })()
  }

  return refreshPromise
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
  retryCount = 0
): Promise<ApiResponse<T>> {
  const headers = new Headers(options.headers)
  const { token, apiKey, workspaceId } = useAuthStore.getState()

  if (!headers.has('Content-Type') && options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (apiKey) headers.set('X-API-Key', apiKey)
  if (workspaceId) headers.set('X-Workspace-ID', workspaceId)

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
    })

    if (response.status === 401 && retryCount === 0) {
      const newToken = await refreshAccessToken()
      if (newToken) return fetchApi(endpoint, options, 1)
    }

    if (!response.ok) {
      const error = await response.text()
      return { error: error || `HTTP error ${response.status}` }
    }

    if (response.status === 204) return { data: undefined }
    return { data: await response.json() as T }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' }
  }
}

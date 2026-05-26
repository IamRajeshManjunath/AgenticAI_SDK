import type { WorkflowSchema, HITLRequest, TraceSpan, WorkflowMetrics } from './types'
import { useAuthStore } from './auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface ApiResponse<T> {
  data?: T
  error?: string
}

interface WorkflowRunResponse {
  trace_id: string
  status: 'started' | 'running' | 'completed' | 'failed'
}

interface HITLApprovalRequest {
  agent_id: string
  action: 'approve' | 'reject'
  feedback?: string
}

interface TraceResponse {
  spans: TraceSpan[]
}

interface MetricsResponse {
  token_usage: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  latency_ms: number
  cost: number
  consensus_score?: number
}

function getAuthHeaders(): Record<string, string> {
  const token = useAuthStore.getState().token
  if (token) {
    return { 'Authorization': `Bearer ${token}` }
  }
  return {}
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const authHeaders = getAuthHeaders()
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...authHeaders,
        ...options?.headers,
      },
    })

    if (!response.ok) {
      const error = await response.text()
      return { error: error || `HTTP error ${response.status}` }
    }

    const data = await response.json()
    return { data }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Unknown error' }
  }
}

// Workflow API
export const workflowApi = {
  async run(
    workflow: WorkflowSchema,
    inputMessage: string
  ): Promise<ApiResponse<WorkflowRunResponse>> {
    return fetchApi<WorkflowRunResponse>('/workflow/run', {
      method: 'POST',
      body: JSON.stringify({
        workflow_schema: workflow,
        input_message: inputMessage,
      }),
    })
  },

  streamExecution(
    workflow: WorkflowSchema,
    inputMessage: string,
    onEvent: (event: {
      type: 'thought' | 'tool_call' | 'tool_result' | 'message' | 'error' | 'hitl' | 'complete'
      data: unknown
    }) => void,
    onError: (error: string) => void
  ): () => void {
    const token = useAuthStore.getState().token
    const eventSource = new EventSource(
      `${API_BASE_URL}/workflow/run/stream?workflow_id=${workflow.id}${token ? `&token=${token}` : ''}`
    )

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        onEvent(parsed)
      } catch {
        console.error('Failed to parse SSE event:', event.data)
      }
    }

    eventSource.onerror = () => {
      onError('Connection lost')
      eventSource.close()
    }

    return () => eventSource.close()
  },
}

// HITL (Human-in-the-Loop) API
export const hitlApi = {
  async approve(
    request: HITLApprovalRequest
  ): Promise<ApiResponse<{ success: boolean }>> {
    return fetchApi<{ success: boolean }>('/workflow/hitl/approve', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  },
}

// Observability API
export const observabilityApi = {
  async getTraces(workflowId: string): Promise<ApiResponse<TraceResponse>> {
    return fetchApi<TraceResponse>(`/observability/traces?workflow_id=${workflowId}`)
  },

  async getMetrics(workflowId: string): Promise<ApiResponse<MetricsResponse>> {
    return fetchApi<MetricsResponse>(`/observability/metrics?workflow_id=${workflowId}`)
  },

  streamMetrics(
    workflowId: string,
    onMetrics: (metrics: WorkflowMetrics) => void,
    onError: (error: string) => void
  ): () => void {
    const token = useAuthStore.getState().token
    const eventSource = new EventSource(
      `${API_BASE_URL}/observability/metrics/stream?workflow_id=${workflowId}${token ? `&token=${token}` : ''}`
    )

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        onMetrics({
          total_cost: parsed.cost,
          budget_limit: parsed.budget_limit || 1.0,
          total_tokens: parsed.token_usage.total_tokens,
          prompt_tokens: parsed.token_usage.prompt_tokens,
          completion_tokens: parsed.token_usage.completion_tokens,
          avg_latency_ms: parsed.latency_ms,
          consensus_score: parsed.consensus_score,
        })
      } catch {
        console.error('Failed to parse metrics event:', event.data)
      }
    }

    eventSource.onerror = () => {
      onError('Metrics stream connection lost')
      eventSource.close()
    }

    return () => eventSource.close()
  },
}

// Auth API
export const authApi = {
  async getProfile(): Promise<ApiResponse<{ id: string; email: string; full_name: string; is_active: boolean; default_workspace_id: string | null }>> {
    return fetchApi('/auth/me')
  },

  async listApiKeys(): Promise<ApiResponse<Array<{ id: string; name: string; key_prefix: string; is_active: boolean; last_used_at: string | null; created_at: string | null }>>> {
    return fetchApi('/auth/api-keys')
  },

  async createApiKey(name: string): Promise<ApiResponse<{ id: string; name: string; key: string; key_prefix: string }>> {
    return fetchApi('/auth/api-keys', {
      method: 'POST',
      body: JSON.stringify({ name }),
    })
  },

  async deleteApiKey(keyId: string): Promise<ApiResponse<void>> {
    return fetchApi(`/auth/api-keys/${keyId}`, { method: 'DELETE' })
  },
}

// Workspace / CRUD API
export const crudApi = {
  async getWorkflows(): Promise<ApiResponse<Array<{ id: string; name: string; description: string; config: unknown; workspace_id: string }>>> {
    return fetchApi('/workflow/workflows')
  },

  async createWorkflow(data: { name: string; description?: string; config?: unknown }): Promise<ApiResponse<{ id: string; name: string }>> {
    return fetchApi('/workflow/workflows', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async getWorkflow(id: string): Promise<ApiResponse<{ id: string; name: string; config: unknown }>> {
    return fetchApi(`/workflow/workflows/${id}`)
  },

  async updateWorkflow(id: string, data: { name?: string; config?: unknown }): Promise<ApiResponse<{ id: string; name: string }>> {
    return fetchApi(`/workflow/workflows/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  async deleteWorkflow(id: string): Promise<ApiResponse<{ success: boolean }>> {
    return fetchApi(`/workflow/workflows/${id}`, { method: 'DELETE' })
  },

  async getTools(): Promise<ApiResponse<Array<{ id: string; name: string; description: string; type: string }>>> {
    return fetchApi('/workflow/tools')
  },

  async createTool(data: { name: string; description?: string; type?: string; code?: string; mcp_url?: string }): Promise<ApiResponse<{ id: string; name: string }>> {
    return fetchApi('/workflow/tools', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async getActivity(): Promise<ApiResponse<Array<{ id: string; action: string; details: unknown; timestamp: string }>>> {
    return fetchApi('/workflow/activity')
  },
}

// Secrets API
export const secretApi = {
  async list(): Promise<ApiResponse<Array<{
    id: string
    name: string
    description: string | null
    created_at: string | null
    updated_at: string | null
  }>>> {
    return fetchApi('/secrets')
  },

  async get(id: string): Promise<ApiResponse<{
    id: string
    name: string
    description: string | null
    value: string
    created_at: string | null
    updated_at: string | null
  }>> {
    return fetchApi(`/secrets/${id}`)
  },

  async create(data: {
    name: string
    value: string
    description?: string
  }): Promise<ApiResponse<{
    id: string
    name: string
    description: string | null
    created_at: string | null
    updated_at: string | null
  }>> {
    return fetchApi('/secrets', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },

  async update(
    id: string,
    data: { name?: string; value?: string; description?: string }
  ): Promise<ApiResponse<{
    id: string
    name: string
    description: string | null
    created_at: string | null
    updated_at: string | null
  }>> {
    return fetchApi(`/secrets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  async delete(id: string): Promise<ApiResponse<void>> {
    return fetchApi(`/secrets/${id}`, { method: 'DELETE' })
  },

  async regenerate(
    id: string,
    data: { value: string; description?: string }
  ): Promise<ApiResponse<{
    id: string
    name: string
    description: string | null
    created_at: string | null
    updated_at: string | null
  }>> {
    return fetchApi(`/secrets/${id}/regenerate`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
}

export const api = {
  workflow: workflowApi,
  hitl: hitlApi,
  observability: observabilityApi,
  auth: authApi,
  crud: crudApi,
  secrets: secretApi,
}

export default api

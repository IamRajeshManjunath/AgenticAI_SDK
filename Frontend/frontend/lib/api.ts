import type { WorkflowSchema, HITLRequest, TraceSpan, WorkflowMetrics } from './types'

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

// Helper function for API calls
async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
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
  /**
   * Run a workflow with the given schema and input message
   */
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

  /**
   * Stream workflow execution events
   */
  streamExecution(
    workflow: WorkflowSchema,
    inputMessage: string,
    onEvent: (event: {
      type: 'thought' | 'tool_call' | 'tool_result' | 'message' | 'error' | 'hitl' | 'complete'
      data: unknown
    }) => void,
    onError: (error: string) => void
  ): () => void {
    const eventSource = new EventSource(
      `${API_BASE_URL}/workflow/run/stream?workflow_id=${workflow.id}`
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
  /**
   * Approve or reject a HITL breakpoint
   */
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
  /**
   * Fetch execution traces for a workflow
   */
  async getTraces(workflowId: string): Promise<ApiResponse<TraceResponse>> {
    return fetchApi<TraceResponse>(`/observability/traces?workflow_id=${workflowId}`)
  },

  /**
   * Fetch metrics for a workflow
   */
  async getMetrics(workflowId: string): Promise<ApiResponse<MetricsResponse>> {
    return fetchApi<MetricsResponse>(`/observability/metrics?workflow_id=${workflowId}`)
  },

  /**
   * Stream live metrics updates
   */
  streamMetrics(
    workflowId: string,
    onMetrics: (metrics: WorkflowMetrics) => void,
    onError: (error: string) => void
  ): () => void {
    const eventSource = new EventSource(
      `${API_BASE_URL}/observability/metrics/stream?workflow_id=${workflowId}`
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

// Export all APIs
export const api = {
  workflow: workflowApi,
  hitl: hitlApi,
  observability: observabilityApi,
}

export default api

import useSWR from 'swr'
import useSWRMutation from 'swr/mutation'
import { fetchApi, type ApiResponse, type WorkflowRunResponse, type HITLApprovalRequest, type TraceResponse, type MetricsResponse } from './http'
import { useWorkflowStore } from './store'
import type { WorkflowSchema, WorkflowMetrics, TraceSpan, ExecutionMessage } from './types'
import { useCallback, useEffect, useRef, useState } from 'react'

// SWR fetcher wrapper
const fetcher = async <T>(key: string, fetcher: () => Promise<{ data?: T; error?: string }>) => {
  const result = await fetcher()
  if (result.error) throw new Error(result.error)
  return result.data
}

function getEventSourceAuthParams(): string {
  if (typeof window === 'undefined') return ''
  const state = typeof window !== 'undefined' ? (window as any).__AUTH_STORE__?.getState?.() : null
  if (!state) return ''
  const token = state.token
  const apiKey = state.apiKey
  const authParam = token ? `&token=${token}` : (apiKey ? `&api_key=${apiKey}` : '')
  return authParam
}

function getEventSourceUrl(endpoint: string, workflowId: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  const authParam = getEventSourceAuthParams()
  return `${baseUrl}${endpoint}?workflow_id=${workflowId}${authParam ? `&${authParam}` : ''}`
}

/**
 * Hook for fetching workflow traces
 */
export function useWorkflowTraces(workflowId: string | null) {
  const { data, error, isLoading, mutate } = useSWR(
    workflowId ? `traces-${workflowId}` : null,
    () => fetcher(`traces-${workflowId}`, () => fetchApi<any>(`/observability/traces?workflow_id=${workflowId!}`)),
    {
      refreshInterval: 5000,
    }
  )

  return {
    traces: data?.spans || [],
    isLoading,
    error: error?.message,
    refresh: mutate,
  }
}

/**
 * Hook for fetching workflow metrics
 */
export function useWorkflowMetrics(workflowId: string | null) {
  const { setMetrics } = useWorkflowStore()

  const { data, error, isLoading, mutate } = useSWR(
    workflowId ? `metrics-${workflowId}` : null,
    () => fetcher(`metrics-${workflowId}`, () => fetchApi<any>(`/observability/metrics?workflow_id=${workflowId!}`)),
    {
      refreshInterval: 3000,
      onSuccess: (data) => {
        if (data && workflowId) {
          setMetrics(workflowId, {
            total_cost: data.cost,
            budget_limit: 1.0,
            total_tokens: data.token_usage.total_tokens,
            prompt_tokens: data.token_usage.prompt_tokens,
            completion_tokens: data.token_usage.completion_tokens,
            avg_latency_ms: data.latency_ms,
            consensus_score: data.consensus_score,
          })
        }
      },
    }
  )

  return {
    metrics: data,
    isLoading,
    error: error?.message,
    refresh: mutate,
  }
}

/**
 * Hook for running a workflow with SSE streaming
 */
export function useWorkflowRun(workflowId: string) {
  const { workflows, setExecutionState, addExecutionMessage, setMetrics, setTrace } = useWorkflowStore()
  const workflow = workflows[workflowId]
  const streamCleanupRef = useRef<EventSource | null>(null)
  const [isRunning, setIsRunning] = useState(false)

  const run = useCallback(async (inputMessage: string) => {
    if (!workflow) throw new Error('Workflow not found')
    setIsRunning(true)

    setExecutionState(workflowId, {
      scratchpad: {},
      messages: [],
      status: 'running',
    })

    // Use the streaming endpoint
    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/run/stream?workflow_id=${workflowId}`
    )

    let cleanup: (() => void) | null = null

    try {
      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data)
          switch (parsed.type) {
            case 'thought':
            case 'tool_call':
            case 'tool_result':
            case 'message':
            case 'error':
            case 'hitl':
              // Add execution message to store
              const store = require('./store').useWorkflowStore.getState()
              store.addExecutionMessage(workflowId, {
                id: Math.random().toString(36).substring(2),
                timestamp: Date.now(),
                type: parsed.type,
                agent_id: (parsed.data as { agent_id?: string }).agent_id || 'system',
                content: (parsed.data as { content?: string }).content || JSON.stringify(parsed.data),
                metadata: parsed.data as Record<string, unknown>,
              })
              break
            case 'complete':
              require('./store').useWorkflowStore.getState().setExecutionState(workflowId, {
                scratchpad: (parsed.data as { scratchpad?: Record<string, unknown> }).scratchpad || {},
                messages: [],
                status: 'completed',
              })
              break
          }
        } catch {
          console.error('Failed to parse SSE event:', event.data)
        }
      }

      eventSource.onerror = () => {
        // Connection lost - could implement reconnection logic here
      }
    } catch (error) {
      console.error('SSE connection error:', error)
    }

    // For now, also call the regular run endpoint for backwards compatibility
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        workflow_schema: workflow,
        input_message: inputMessage,
      }),
    })

    if (!response.ok) {
      const error = await response.text()
      throw new Error(error || 'Failed to run workflow')
    }

    const result = await response.json()
    return result
  }, [workflowId])

  const stop = useCallback(() => {
    // Note: EventSource doesn't have a stop method, it closes on close()
  }, [workflowId])

  return {
    run: (inputMessage: string) => trigger({ inputMessage }),
    stop,
    isRunning: true, // Simplified for now
    error: null,
  }
}

/**
 * Hook for HITL approval
 */
export function useHITLApproval() {
  const { resolveHITLRequest } = useWorkflowStore()

  const { trigger, isMutating, error } = useSWRMutation(
    'hitl-approval',
    async (
      _key: string,
      { arg }: { arg: { agentId: string; action: 'approve' | 'reject'; feedback?: string; requestId: string } }
    ) => {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/hitl/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_id: arg.agentId,
          action: arg.action,
          feedback: arg.feedback,
        }),
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(error || 'Failed to approve/reject')
      }

      // Update local state
      const store = require('./store').useWorkflowStore.getState()
      store.resolveHITLRequest(arg.requestId, arg.action, arg.feedback)

      return response.json()
    }
  )

  return {
    approve: (requestId: string, agentId: string, feedback?: string) =>
      trigger({ requestId, agentId, action: 'approve', feedback }),
    reject: (requestId: string, agentId: string, feedback?: string) =>
      trigger({ requestId, agentId, action: 'reject', feedback }),
    isLoading: isMutating,
    error: error?.message,
  }
}

/**
 * Hook for streaming metrics updates
 */
export function useStreamingMetrics(workflowId: string | null, enabled: boolean = true) {
  const { setMetrics } = useWorkflowStore()
  const cleanupRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!workflowId || !enabled) return

    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/observability/metrics/stream?workflow_id=${workflowId}`
    )

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        setMetrics(workflowId, {
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
      console.error('Metrics stream connection lost')
      eventSource.close()
    }

    return () => eventSource.close()
  }, [workflowId, enabled, setMetrics])
}

/**
 * Hook for streaming workflow execution events
 */
export function useWorkflowStream(workflowId: string | null) {
  const { addExecutionMessage, setExecutionState } = useWorkflowStore()
  const cleanupRef = useRef<EventSource | null>(null)

  useEffect(() => {
    if (!workflowId) return

    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/run/stream?workflow_id=${workflowId}`
    )

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        addExecutionMessage(workflowId, {
          id: Math.random().toString(36).substring(2),
          timestamp: Date.now(),
          type: parsed.type,
          agent_id: parsed.data?.agent_id || 'system',
          content: parsed.data?.content || JSON.stringify(parsed.data),
          metadata: parsed.data as Record<string, unknown>,
        })
      } catch {
        console.error('Failed to parse SSE event:', event.data)
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
    }

    cleanupRef.current = eventSource

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current.close()
      }
    }
  }, [workflowId, addExecutionMessage])
}

export function useConfigStream() {
  const cleanupRef = useRef<EventSource | null>(null)

  useEffect(() => {
    const eventSource = new EventSource(
      `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config/stream`
    )

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data)
        if (parsed.type === 'config_updated' || parsed.type === 'initial') {
          window.location.reload()
        }
      } catch {
        console.error('Failed to parse config SSE event:', event.data)
      }
    }

    eventSource.onerror = () => {
      eventSource.close()
    }

    cleanupRef.current = eventSource

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current.close()
      }
    }
  }, [])
}
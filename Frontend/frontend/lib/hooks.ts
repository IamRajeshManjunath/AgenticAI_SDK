import useSWR from 'swr'
import useSWRMutation from 'swr/mutation'
import { api } from './api'
import { useWorkflowStore } from './store'
import type { WorkflowSchema, WorkflowMetrics, TraceSpan, ExecutionMessage } from './types'
import { useCallback, useEffect, useRef } from 'react'

// SWR fetcher wrapper
const fetcher = async <T>(key: string, fetcher: () => Promise<{ data?: T; error?: string }>) => {
  const result = await fetcher()
  if (result.error) throw new Error(result.error)
  return result.data
}

/**
 * Hook for fetching workflow traces
 */
export function useWorkflowTraces(workflowId: string | null) {
  const { data, error, isLoading, mutate } = useSWR(
    workflowId ? `traces-${workflowId}` : null,
    () => fetcher(`traces-${workflowId}`, () => api.observability.getTraces(workflowId!)),
    {
      refreshInterval: 5000, // Refresh every 5 seconds during active runs
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
    () => fetcher(`metrics-${workflowId}`, () => api.observability.getMetrics(workflowId!)),
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
 * Hook for running a workflow
 */
export function useWorkflowRun(workflowId: string) {
  const { workflows, setExecutionState, addExecutionMessage, setMetrics, setTrace } =
    useWorkflowStore()
  const workflow = workflows[workflowId]
  const streamCleanupRef = useRef<(() => void) | null>(null)

  const { trigger, isMutating, error } = useSWRMutation(
    `run-${workflowId}`,
    async (_key: string, { arg }: { arg: { inputMessage: string } }) => {
      if (!workflow) throw new Error('Workflow not found')

      // Initialize execution state
      setExecutionState(workflowId, {
        scratchpad: {},
        messages: [],
        status: 'running',
      })

      // Start streaming execution
      streamCleanupRef.current = api.workflow.streamExecution(
        workflow,
        arg.inputMessage,
        (event) => {
          switch (event.type) {
            case 'thought':
            case 'tool_call':
            case 'tool_result':
            case 'message':
            case 'error':
            case 'hitl':
              addExecutionMessage(workflowId, {
                id: Math.random().toString(36).substring(2),
                timestamp: Date.now(),
                type: event.type,
                agent_id: (event.data as { agent_id?: string }).agent_id || 'system',
                content: (event.data as { content?: string }).content || JSON.stringify(event.data),
                metadata: event.data as Record<string, unknown>,
              })
              break
            case 'complete':
              setExecutionState(workflowId, {
                scratchpad: (event.data as { scratchpad?: Record<string, unknown> }).scratchpad || {},
                messages: [],
                status: 'completed',
              })
              break
          }
        },
        (error) => {
          setExecutionState(workflowId, {
            scratchpad: {},
            messages: [],
            status: 'failed',
          })
          addExecutionMessage(workflowId, {
            id: Math.random().toString(36).substring(2),
            timestamp: Date.now(),
            type: 'error',
            agent_id: 'system',
            content: error,
          })
        }
      )

      return { started: true }
    }
  )

  const stop = useCallback(() => {
    if (streamCleanupRef.current) {
      streamCleanupRef.current()
      streamCleanupRef.current = null
    }
    setExecutionState(workflowId, {
      scratchpad: {},
      messages: [],
      status: 'idle',
    })
  }, [workflowId, setExecutionState])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (streamCleanupRef.current) {
        streamCleanupRef.current()
      }
    }
  }, [])

  return {
    run: (inputMessage: string) => trigger({ inputMessage }),
    stop,
    isRunning: isMutating,
    error: error?.message,
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
      const result = await api.hitl.approve({
        agent_id: arg.agentId,
        action: arg.action,
        feedback: arg.feedback,
      })

      if (result.error) throw new Error(result.error)

      // Update local state
      resolveHITLRequest(arg.requestId, arg.action, arg.feedback)

      return result.data
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
  const cleanupRef = useRef<(() => void) | null>(null)

  useEffect(() => {
    if (!workflowId || !enabled) return

    cleanupRef.current = api.observability.streamMetrics(
      workflowId,
      (metrics) => setMetrics(workflowId, metrics),
      (error) => console.error('Metrics stream error:', error)
    )

    return () => {
      if (cleanupRef.current) {
        cleanupRef.current()
      }
    }
  }, [workflowId, enabled, setMetrics])
}

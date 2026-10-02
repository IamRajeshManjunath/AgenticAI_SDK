'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { RefreshCw, Play, Pause, Stop, Square, Download, Filter, Search, ChevronDown, ChevronUp } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface ExecutionMessage {
  id: string
  timestamp: number
  type: 'thought' | 'tool_call' | 'tool_result' | 'message' | 'error' | 'hitl' | 'complete'
  agent_id: string
  content: string
  metadata?: Record<string, unknown>
}

interface ExecutionState {
  scratchpad: Record<string, unknown>
  messages: ExecutionMessage[]
  current_agent?: string
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed'
}

interface WorkflowExecution {
  workflow_id: string
  thread_id: string
  status: 'running' | 'paused' | 'completed' | 'failed'
  messages: ExecutionMessage[]
  scratchpad: Record<string, unknown>
  current_agent?: string
  total_cost: number
  total_tokens: number
  latency_ms: number
}

export default function WorkflowExecutionMonitor() {
  const { workflows, activeWorkflowId, executionStates, setExecutionState, addExecutionMessage } = useWorkflowStore()
  const { token } = useAuthStore()
  
  const [activeExecution, setActiveExecution] = useState<WorkflowExecution | null>(null)
  const [selectedExecutionId, setSelectedExecutionId] = useState<string | null>(null)
  const [isStreaming, setIsStreaming] = useState(false)
  const [logs, setLogs] = useState<string[]>([])
  const [isStreamingLogs, setIsStreamingLogs] = useState(false)

  const activeWorkflow = activeWorkflowId ? workflows[activeWorkflowId] : null

  useEffect(() => {
    if (activeWorkflowId) {
      setSelectedExecutionId(activeWorkflowId)
      // Initialize execution state if not exists
      if (!executionStates[activeWorkflowId]) {
        setExecutionState(activeWorkflowId, {
          scratchpad: {},
          messages: [],
          status: 'idle',
        })
      }
    }
  }, [activeWorkflowId, executionStates, setExecutionState])

  const handleRunWorkflow = useCallback(async (inputMessage: string) => {
    const workflow = workflows[activeWorkflowId]
    if (!workflow) return

    try {
      setExecutionState(activeWorkflowId!, {
        scratchpad: {},
        messages: [],
        status: 'running',
      })

      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${useAuthStore.getState().token}`,
          'X-Workspace-ID': useAuthStore.getState().workspaceId || '',
        },
        body: JSON.stringify({
          workflow_schema: workflows[activeWorkflowId],
          input_message: inputMessage,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to run workflow')
      }

      const result = await response.json()
      return result
    } catch (error) {
      console.error('Failed to run workflow:', error)
    }
  }, [activeWorkflowId, workflows, setExecutionState])

  const handleStreamExecution = useCallback(async (inputMessage: string) => {
    const workflow = workflows[activeWorkflowId]
    if (!workflow) return

    setIsStreaming(true)

    try {
      const eventSource = new EventSource(
        `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/run/stream?workflow_id=${activeWorkflowId}&token=${useAuthStore.getState().token}`
      )

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data)
          // Add execution message to store
          useWorkflowStore.getState().addExecutionMessage(activeWorkflowId!, {
            id: Math.random().toString(36).substring(2),
            timestamp: Date.now(),
            type: parsed.type,
            agent_id: parsed.data?.agent_id || 'system',
            content: parsed.data?.content || JSON.stringify(parsed.data),
            metadata: parsed.data,
          })
        } catch {
          console.error('Failed to parse SSE event:', event.data)
        }
      }

      eventSource.onerror = () => {
        eventSource.close()
      }
    } catch (error) {
      console.error('SSE connection error:', error)
    }
  }, [activeWorkflowId])

  const stopExecution = useCallback(() => {
    // Stop execution logic
  }, [activeWorkflowId])

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Workflow Execution Monitor</h1>
          <p className="text-muted-foreground mt-1">Monitor and debug workflow executions in real-time</p>
        </div>
      </div>

      {/* Active Workflow Selector */}
      <div className="mb-6">
        <Label className="block text-sm font-medium mb-2">Active Workflow</Label>
        <select
          value={activeWorkflowId || ''}
          onChange={(e) => {
            const workflowId = e.target.value
            useWorkflowStore.getState().setActiveWorkflow(workflowId || null)
          }}
          className="w-full max-w-md px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
        >
          <option value="">Select a workflow to monitor</option>
          {Object.entries(workflows).map(([id, wf]) => (
            <option key={id} value={id}>
              {wf.name} ({wf.agents?.length || 0} agents)
            </option>
          ))}
        </select>
      </div>

      {/* Execution Controls */}
      <div className="flex flex-wrap gap-3 mb-6">
        <input
          type="text"
          placeholder="Enter input message..."
          className="flex-1 min-w-[300px] px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          placeholder="Enter input message for workflow..."
        />
        <Button onClick={() => handleStreamExecution('test message')} disabled={isStreaming} className="gap-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
          Run Workflow
        </Button>
        <Button variant="outline" onClick={stopExecution} disabled={!activeExecution}>
          <Square className="w-4 h-4" />
          Stop
        </Button>
        <Button variant="secondary" onClick={() => setLogs([])} className="gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
          Clear Logs
        </Button>
      </div>

      {/* Execution Tabs */}
      <Tabs defaultValue="logs" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="logs">Live Logs</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="hitl">HITL Queue</TabsTrigger>
        </TabsList>

        <TabsContent value="logs" className="mt-4">
          <div className="bg-card border border-border rounded-lg">
            <div className="flex items-center justify-between p-4 border-b border-border">
              <h3 className="font-semibold">Live Execution Logs</h3>
              <div className="flex items-center gap-2">
                <Badge variant={isStreaming ? 'default' : 'secondary'}>
                  {isStreaming ? 'Streaming' : 'Idle'}
                </Badge>
              </div>
            </div>
            <div className="h-[500px] overflow-y-auto p-4 font-mono text-sm bg-background/50">
              {logs.map((log, index) => (
                <div key={index} className="text-sm text-muted-foreground font-mono py-1 border-b border-border/50 last:border-0">
                  {log}
                </div>
              )}
              {logs.length === 0 && (
                <div className="h-[500px] flex items-center justify-center text-muted-foreground">
                  No logs yet. Start a workflow execution to see live logs.
                </div>
              )}
            </div>
          </TabsContent>

          <TabsContent value="metrics" className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Cost</p>
                    <p className="text-2xl font-bold text-green-500">${0}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-green-100">
                    <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.105 0 2-.895 3-2s-.895-2-3-2-3 .895-3 2-3 .895-3 2z" />
                    </svg>
                  </div>
                </div>
              </div>
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Tokens</p>
                    <p className="text-2xl font-bold text-blue-500">0</p>
                  </div>
                  <div className="p-2 rounded-lg bg-blue-100">
                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                </div>
              </div>
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Avg Latency</p>
                    <p className="text-2xl font-bold text-purple-500">0ms</p>
                  </div>
                  <div className="p-2 rounded-lg bg-purple-100">
                    <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Tokens</p>
                    <p className="text-2xl font-bold text-blue-500">0</p>
                  </div>
                  <div className="p-2 rounded-lg bg-blue-100">
                    <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="hitl" className="mt-4">
            <div className="bg-card border border-border rounded-lg p-6">
              <h3 className="text-lg font-semibold mb-4">HITL Approval Queue</p>
              <p className="text-muted-foreground mb-4">Human-in-the-loop approval requests waiting for review</p>
              <div className="text-center py-12">
                <svg className="w-12 h-12 mx-auto text-muted-foreground mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 11l-2 2-4-4m-6 11l-2-2 4-4m-6 11l-2-2 4-4" />
                </svg>
                <h3 className="text-lg font-medium mb-2">No pending approvals</h3>
                <p className="text-muted-foreground">All caught up! No HITL approvals at the moment.</p>
              </div>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default WorkflowExecutionMonitor
'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { RefreshCw, Download, Filter, Search, TrendingUp, DollarSign, Clock, Zap, Activity, BarChart3 } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { cn } from '@/lib/utils'

interface TraceSummary {
  trace_id: string
  workflow_id: string
  workflow_name: string
  status: 'started' | 'running' | 'completed' | 'failed'
  total_cost: number
  total_tokens: number
  latency_ms: number
  started_at: string
  completed_at: string | null
}

interface MetricsSummary {
  total_cost: number
  budget_limit: number
  total_tokens: number
  prompt_tokens: number
  completion_tokens: number
  avg_latency_ms: number
  consensus_score?: number
}

export default function ObservabilityDashboard() {
  const [traces, setTraces] = useState<TraceSummary[]>([])
  const [metrics, setMetrics] = useState<MetricsSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [selectedTrace, setSelectedTrace] = useState<TraceSummary | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [statusFilter, setStatusFilter] = useState<'all' | 'running' | 'completed' | 'failed'>('all')
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h')
  const { token } = useAuthStore()

  useEffect(() => {
    fetchTraces()
    fetchMetrics()
  }, [])

  const fetchTraces = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/observability/traces?limit=100`, {
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setTraces(data.traces || [])
      }
    } catch (error) {
      console.error('Failed to fetch traces:', error)
    }
  }

  const fetchMetrics = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/observability/metrics`, {
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setMetrics(data)
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error)
    }
  }

  const filteredTraces = traces.filter(trace => {
    if (searchQuery && !trace.workflow_name.toLowerCase().includes(searchQuery.toLowerCase())) return false
    if (statusFilter !== 'all' && trace.status !== statusFilter) return false
    return true
  })

  const stats = {
    totalTraces: traces.length,
    completed: traces.filter(t => t.status === 'completed').length,
    failed: traces.filter(t => t.status === 'failed').length,
    running: traces.filter(t => t.status === 'running').length,
    totalCost: traces.reduce((sum, t) => sum + t.total_cost, 0),
    avgLatency: traces.length > 0 ? traces.reduce((sum, t) => sum + t.latency_ms, 0) / traces.length : 0,
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Observability</h1>
          <p className="text-muted-foreground mt-1">Monitor workflow executions, costs, and performance</p>
        </div>
        <div className="flex items-center gap-2">
          <Button onClick={fetchTraces} className="gap-2" disabled={isLoading}>
            <RefreshCw className="w-4 h-4" />
            Refresh
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Traces</p>
              <p className="text-2xl font-bold">{traces.length}</p>
            </div>
            <div className="p-2 rounded-lg bg-muted">
              <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
              </svg>
            </div>
          </div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Completed</p>
              <p className="text-2xl font-bold text-green-500">{traces.filter(t => t.status === 'completed').length}</p>
            </div>
            <div className="p-2 rounded-lg bg-green-100">
              <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Failed</p>
              <p className="text-2xl font-bold text-red-500">{traces.filter(t => t.status === 'failed').length}</p>
            </div>
            <div className="p-2 rounded-lg bg-red-100">
              <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
          </div>
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total Cost</p>
              <p className="text-2xl font-bold text-green-500">${traces.reduce((sum, t) => sum + t.total_cost, 0).toFixed(4)}</p>
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
              <p className="text-sm text-muted-foreground">Avg Latency</p>
              <p className="text-2xl font-bold">{traces.length > 0 ? Math.round(traces.reduce((sum, t) => sum + t.latency_ms, 0) / traces.length) : 0}ms</p>
            </div>
            <div className="p-2 rounded-lg bg-muted">
              <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="traces" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="traces">Traces</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="costs">Costs</TabsTrigger>
          <TabsTrigger value="traces-detail">Trace Detail</TabsTrigger>
        </TabsList>

        <TabsContent value="traces" className="mt-4">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-4">
            <div className="flex gap-2">
              <input
                type="text"
                placeholder="Search traces..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="flex-1 max-w-xs px-3 py-2 bg-background border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as any)}
                className="px-3 py-2 bg-background border border-border rounded-lg text-sm"
              >
                <option value="all">All Status</option>
                <option value="running">Running</option>
                <option value="completed">Completed</option>
                <option value="failed">Failed</option>
              </select>
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value as any)}
                className="px-3 py-2 bg-background border border-border rounded-lg text-sm"
              >
                <option value="1h">Last Hour</option>
                <option value="24h">Last 24 Hours</option>
                <option value="7d">Last 7 Days</option>
                <option value="30d">Last 30 Days</option>
              </select>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left p-3 text-sm font-medium text-muted-foreground">Workflow</th>
                  <th className="text-left p-3 text-sm font-medium text-muted-foreground">Status</th>
                  <th className="text-left p-3 text-sm font-medium text-muted-foreground">Cost</th>
                  <th className="text-left p-3 text-sm font-medium text-muted-foreground">Tokens</th>
                  <th className="text-left p-3 text-sm font-medium text-muted-foreground">Latency</th>
                  <th className="text-left p-3 text-sm font-medium text-muted-foreground">Started</th>
                  <th className="text-left p-3 text-sm font-medium text-muted-foreground">Completed</th>
                  <th className="text-right p-3 text-sm font-medium text-muted-foreground">Actions</th>
                </thead>
                <tbody className="divide-y divide-border">
                  {traces.map((trace) => (
                    <tr key={trace.trace_id} className="hover:bg-muted/50 cursor-pointer" onClick={() => setSelectedTrace(trace)}>
                      <td className="p-3 font-mono text-sm">{trace.workflow_name}</td>
                      <td className="p-3">
                        <Badge variant={
                          trace.status === 'completed' ? 'default' :
                          trace.status === 'failed' ? 'destructive' :
                          trace.status === 'running' ? 'secondary' : 'outline'
                        }>
                          {trace.status}
                        </Badge>
                      </td>
                      <td className="p-3 font-mono text-sm">${trace.total_cost.toFixed(4)}</td>
                      <td className="p-3 font-mono text-sm">{trace.total_tokens.toLocaleString()}</td>
                      <td className="p-3 font-mono text-sm">{trace.latency_ms}ms</td>
                      <td className="p-3 text-sm text-muted-foreground">{new Date(trace.started_at).toLocaleString()}</td>
                      <td className="p-3 text-sm text-muted-foreground">
                        {trace.completed_at ? new Date(trace.completed_at).toLocaleString() : '-'}
                      </td>
                      <td className="p-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setSelectedTrace(trace)
                          }}
                          className="text-primary hover:underline text-sm"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="metrics" className="mt-4">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Requests</p>
                    <p className="text-2xl font-bold">{(metrics as any)?.total_requests || 0}</p>
                  </div>
                  <div className="p-2 rounded-lg bg-muted">
                    <Activity className="w-5 h-5 text-muted-foreground" />
                  </div>
                </div>
              </div>
              <div className="bg-card border border-border rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">Total Tokens</p>
                    <p className="text-2xl font-bold text-blue-500">{(metrics as any)?.total_tokens?.toLocaleString() || 0}</p>
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
                    <p className="text-sm text-muted-foreground">Total Cost</p>
                    <p className="text-2xl font-bold text-green-500">${(metrics as any)?.total_cost_usd?.toFixed(4) || 0}</p>
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
                    <p className="text-sm text-muted-foreground">Avg Latency</p>
                    <p className="text-2xl font-bold text-purple-500">{(metrics as any)?.avg_latency_ms?.toFixed(0) || 0}ms</p>
                  </div>
                  <div className="p-2 rounded-lg bg-purple-100">
                    <svg className="w-5 h-5 text-purple-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="costs" className="mt-4">
          <div className="bg-card border border-border rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Cost Breakdown</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-muted/50 rounded-lg p-4">
                <h4 className="font-medium mb-2">By Workflow</h4>
                <p className="text-muted-foreground text-sm">Cost breakdown by workflow coming soon...</p>
              </div>
              <div className="bg-muted/50 rounded-lg p-4">
                <h4 className="font-medium mb-2">By Model</h4>
                <p className="text-muted-foreground text-sm">Cost breakdown by model coming soon...</p>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="traces-detail" className="mt-4">
          <div className="bg-card border border-border rounded-lg p-6">
            <h3 className="text-lg font-semibold mb-4">Trace Detail</h3>
            <p className="text-muted-foreground">Select a trace from the Traces tab to view detailed span information</p>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ObservabilityDashboard
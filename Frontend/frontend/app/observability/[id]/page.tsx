'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ArrowLeft,
  Play,
  Pause,
  RotateCcw,
  DollarSign,
  Zap,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  Terminal,
  Bot,
  Wrench,
  MessageSquare,
  AlertCircle,
  User,
  FileJson,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import type { TraceSpan, ExecutionMessage, HITLRequest } from '@/lib/types'

import useSWR from 'swr'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

export default function ObservabilityPage() {
  const params = useParams()
  const workflowId = params.id as string
  const { workflows, resolveHITLRequest } = useWorkflowStore()
  const workflow = workflows[workflowId]
  const feedRef = useRef<HTMLDivElement>(null)
  
  const [isRunning, setIsRunning] = useState(false)
  const [showHITLModal, setShowHITLModal] = useState(false)
  const [hitlFeedback, setHitlFeedback] = useState('')
  const [currentHITL, setCurrentHITL] = useState<HITLRequest | null>(null)
  const [stateDrawerOpen, setStateDrawerOpen] = useState(false)

  // Real Data Fetching
  const { data: traceData, error: traceError } = useSWR(
    `http://localhost:8000/api/v1/workflow/observability/traces/${workflowId}`,
    fetcher,
    { 
      refreshInterval: (traceData && (traceData.status === 'completed' || traceData.status === 'failed')) 
        ? 0 
        : 2000 
    }
  )

  const { data: metricsData } = useSWR(
    `http://localhost:8000/api/v1/workflow/observability/metrics/${workflowId}`,
    fetcher,
    { refreshInterval: 5000 }
  )

  const currentMetrics = metricsData || {
    total_cost: 0,
    budget_limit: 100,
    total_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    avg_latency_ms: 0,
    consensus_score: 0,
  }

  const messages: ExecutionMessage[] = traceData?.messages || []
  const trace: TraceSpan | null = traceData?.trace || null

  // Handle run via API
  const handleStartRun = async () => {
    setIsRunning(true)
    try {
      await fetch('http://localhost:8000/api/v1/workflow/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(workflow),
      })
    } catch (error) {
      console.error('Run error:', error)
      setIsRunning(false)
    }
  }

  // Scroll to bottom of feed
  useEffect(() => {
    if (messages.length > 0) {
      feedRef.current?.scrollTo({
        top: feedRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [messages])

  // Simulate HITL trigger
  const handleSimulateHITL = () => {
    const hitl: HITLRequest = {
      id: Math.random().toString(36).substring(2),
      agent_id: 'coordinator',
      proposed_action: 'send_email',
      proposed_output: 'Dear Customer,\n\nThank you for your inquiry about our AI services...',
      timestamp: Date.now(),
      status: 'pending',
    }
    setCurrentHITL(hitl)
    setShowHITLModal(true)
  }

  const handleHITLResolve = (action: 'approve' | 'reject') => {
    if (currentHITL) {
      resolveHITLRequest(currentHITL.id, action, hitlFeedback)
    }
    setShowHITLModal(false)
    setHitlFeedback('')
    setCurrentHITL(null)
  }

  if (!workflow) {
    return (
      <DashboardLayout>
        <div className="flex flex-col items-center justify-center h-[calc(100vh-4rem)]">
          <h2 className="text-xl font-semibold mb-2">Workflow not found</h2>
          <p className="text-muted-foreground mb-4">
            The workflow you are looking for does not exist.
          </p>
          <Button asChild>
            <Link href="/">Back to Dashboard</Link>
          </Button>
        </div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="h-screen flex flex-col">
        {/* Top Bar */}
        <div className="h-14 border-b border-border bg-card/50 backdrop-blur-sm flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" asChild className="gap-2">
              <Link href={`/workflows/${workflowId}`}>
                <ArrowLeft className="w-4 h-4" />
                Builder
              </Link>
            </Button>
            <div className="h-6 w-px bg-border" />
            <div>
              <h1 className="text-sm font-semibold">{workflow.name} - Observability</h1>
              <p className="text-xs text-muted-foreground">
                Real-time execution monitoring
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSimulateHITL}
              className="gap-2"
            >
              <AlertTriangle className="w-4 h-4" />
              Simulate HITL
            </Button>
            {isRunning ? (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setIsRunning(false)}
                className="gap-2"
              >
                <Pause className="w-4 h-4" />
                Pause
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={handleStartRun}
                className="gap-2 glow-primary-sm"
              >
                <Play className="w-4 h-4" />
                Start Run
              </Button>
            )}
          </div>
        </div>

        {/* Metrics Strip */}
        <div className="border-b border-border bg-card/30 px-4 py-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              icon={<DollarSign className="w-4 h-4" />}
              label="Total Cost"
              value={`$${currentMetrics.total_cost.toFixed(4)}`}
              subValue={
                <Progress
                  value={(currentMetrics.total_cost / currentMetrics.budget_limit) * 100}
                  className="h-1.5 mt-1"
                />
              }
              color="text-warning"
            />
            <MetricCard
              icon={<Zap className="w-4 h-4" />}
              label="Total Tokens"
              value={currentMetrics.total_tokens.toLocaleString()}
              subValue={
                <span className="text-xs text-muted-foreground">
                  {currentMetrics.prompt_tokens} prompt + {currentMetrics.completion_tokens} completion
                </span>
              }
              color="text-success"
            />
            <MetricCard
              icon={<Clock className="w-4 h-4" />}
              label="Avg Latency"
              value={`${currentMetrics.avg_latency_ms}ms`}
              color="text-chart-2"
            />
            <MetricCard
              icon={<CheckCircle className="w-4 h-4" />}
              label="Consensus Score"
              value={`${(currentMetrics.consensus_score * 100).toFixed(0)}%`}
              subValue={
                <span className="text-xs text-muted-foreground">High Confidence</span>
              }
              color="text-primary"
            />
          </div>
        </div>

        {/* Main Content */}
        <div className="flex-1 flex overflow-hidden">
          {/* Execution Feed */}
          <div className="flex-1 flex flex-col border-r border-border">
            <div className="p-3 border-b border-border bg-card/30">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <Terminal className="w-4 h-4" />
                Live Execution Feed
              </h3>
            </div>
            <div
              ref={feedRef}
              className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-3 bg-background/50 font-mono text-sm"
            >
              {messages.length === 0 ? (
                <div className="text-center text-muted-foreground py-12">
                  <Terminal className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No execution data yet.</p>
                  <p className="text-xs mt-1">Start a workflow run to see live output.</p>
                </div>
              ) : (
                <AnimatePresence>
                  {messages.map((msg) => (
                    <ExecutionMessageCard key={msg.id} message={msg} />
                  ))}
                </AnimatePresence>
              )}
            </div>
          </div>

          {/* Trace Tree */}
          <div className="w-80 flex flex-col bg-card/30">
            <div className="p-3 border-b border-border">
              <h3 className="text-sm font-medium flex items-center gap-2">
                <FileJson className="w-4 h-4" />
                Trace Span Tree
              </h3>
            </div>
            <div className="flex-1 overflow-y-auto scrollbar-thin p-4">
              {trace ? (
                <TraceSpanTree span={trace} depth={0} />
              ) : (
                <div className="text-center text-muted-foreground py-12">
                  <FileJson className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-sm">No trace data available.</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* State Introspection Drawer */}
        <div className="border-t border-border">
          <button
            onClick={() => setStateDrawerOpen(!stateDrawerOpen)}
            className="w-full p-2 flex items-center justify-center gap-2 bg-card/50 hover:bg-card/80 transition-colors text-sm"
          >
            {stateDrawerOpen ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
            State Introspection
          </button>
          <AnimatePresence>
            {stateDrawerOpen && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 200 }}
                exit={{ height: 0 }}
                className="overflow-hidden"
              >
                <Tabs defaultValue="scratchpad" className="h-full">
                  <div className="px-4 border-b border-border">
                    <TabsList className="bg-transparent">
                      <TabsTrigger value="scratchpad">Scratchpad</TabsTrigger>
                      <TabsTrigger value="messages">Messages</TabsTrigger>
                    </TabsList>
                  </div>
                  <TabsContent value="scratchpad" className="h-[150px] p-0 m-0">
                    <pre className="h-full overflow-auto scrollbar-thin p-4 bg-background/50 text-xs font-mono">
                      {JSON.stringify(traceData?.scratchpad || {}, null, 2)}
                    </pre>
                  </TabsContent>
                  <TabsContent value="messages" className="h-[150px] p-0 m-0">
                    <pre className="h-full overflow-auto scrollbar-thin p-4 bg-background/50 text-xs font-mono">
                      {JSON.stringify(
                        workflowState.messages.map((m) => ({
                          type: m.type,
                          agent: m.agent_id,
                          content: m.content.substring(0, 50) + '...',
                        })),
                        null,
                        2
                      )}
                    </pre>
                  </TabsContent>
                </Tabs>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* HITL Modal */}
        <Dialog open={showHITLModal} onOpenChange={setShowHITLModal}>
          <DialogContent className="max-w-lg">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2 text-warning">
                <AlertTriangle className="w-5 h-5" />
                Human-in-the-Loop Approval Required
              </DialogTitle>
              <DialogDescription>
                Agent <strong>{currentHITL?.agent_id}</strong> is requesting approval for
                the following action.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <label className="text-sm font-medium">Proposed Action</label>
                <Badge variant="secondary" className="ml-2">
                  {currentHITL?.proposed_action}
                </Badge>
              </div>
              <div>
                <label className="text-sm font-medium">Proposed Output</label>
                <pre className="mt-2 p-3 rounded-lg bg-secondary text-sm overflow-auto max-h-48 scrollbar-thin">
                  {currentHITL?.proposed_output}
                </pre>
              </div>
              <div>
                <label className="text-sm font-medium">Corrective Feedback (optional)</label>
                <Textarea
                  value={hitlFeedback}
                  onChange={(e) => setHitlFeedback(e.target.value)}
                  placeholder="Provide feedback or corrections..."
                  className="mt-2"
                />
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button
                variant="destructive"
                onClick={() => handleHITLResolve('reject')}
                className="gap-2"
              >
                <XCircle className="w-4 h-4" />
                Reject
              </Button>
              <Button
                onClick={() => handleHITLResolve('approve')}
                className="gap-2 bg-success hover:bg-success/80"
              >
                <CheckCircle className="w-4 h-4" />
                Approve
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  )
}

interface MetricCardProps {
  icon: React.ReactNode
  label: string
  value: string
  subValue?: React.ReactNode
  color?: string
}

function MetricCard({ icon, label, value, subValue, color }: MetricCardProps) {
  return (
    <div className="glass-card p-3 rounded-lg">
      <div className="flex items-center gap-2 mb-1">
        <span className={color}>{icon}</span>
        <span className="text-xs text-muted-foreground">{label}</span>
      </div>
      <p className="text-lg font-semibold">{value}</p>
      {subValue}
    </div>
  )
}

interface ExecutionMessageCardProps {
  message: ExecutionMessage
}

function ExecutionMessageCard({ message }: ExecutionMessageCardProps) {
  const getIcon = () => {
    switch (message.type) {
      case 'thought':
        return <Bot className="w-4 h-4 text-primary" />
      case 'tool_call':
        return <Wrench className="w-4 h-4 text-warning" />
      case 'tool_result':
        return <CheckCircle className="w-4 h-4 text-success" />
      case 'message':
        return <MessageSquare className="w-4 h-4 text-chart-2" />
      case 'error':
        return <AlertCircle className="w-4 h-4 text-destructive" />
      case 'hitl':
        return <User className="w-4 h-4 text-warning" />
      default:
        return <MessageSquare className="w-4 h-4" />
    }
  }

  const getBgColor = () => {
    switch (message.type) {
      case 'thought':
        return 'border-l-primary/50 bg-primary/5'
      case 'tool_call':
        return 'border-l-warning/50 bg-warning/5'
      case 'tool_result':
        return 'border-l-success/50 bg-success/5'
      case 'error':
        return 'border-l-destructive/50 bg-destructive/5'
      default:
        return 'border-l-border bg-card/30'
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      className={cn(
        'rounded-lg border-l-4 p-3',
        getBgColor()
      )}
    >
      <div className="flex items-start gap-3">
        {getIcon()}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className="text-xs py-0">
              {message.agent_id}
            </Badge>
            <span className="text-xs text-muted-foreground">
              {new Date(message.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <p className="text-sm break-words">{message.content}</p>
          {message.metadata && (
            <pre className="mt-2 text-xs text-muted-foreground bg-secondary/50 p-2 rounded overflow-x-auto">
              {JSON.stringify(message.metadata, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </motion.div>
  )
}

interface TraceSpanTreeProps {
  span: TraceSpan
  depth: number
}

function TraceSpanTree({ span, depth }: TraceSpanTreeProps) {
  const [expanded, setExpanded] = useState(true)
  const hasChildren = span.children && span.children.length > 0

  const getStatusColor = () => {
    switch (span.status) {
      case 'running':
        return 'text-primary pulse-glow'
      case 'completed':
        return 'text-success'
      case 'failed':
        return 'text-destructive'
      default:
        return 'text-muted-foreground'
    }
  }

  const getStatusIcon = () => {
    switch (span.status) {
      case 'running':
        return <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
      case 'completed':
        return <CheckCircle className="w-3 h-3 text-success" />
      case 'failed':
        return <XCircle className="w-3 h-3 text-destructive" />
      default:
        return <div className="w-2 h-2 rounded-full bg-muted-foreground" />
    }
  }

  return (
    <div className="text-sm">
      <button
        onClick={() => hasChildren && setExpanded(!expanded)}
        className={cn(
          'flex items-center gap-2 w-full p-2 rounded-lg transition-colors',
          'hover:bg-secondary/50',
          span.status === 'running' && 'bg-primary/10'
        )}
        style={{ paddingLeft: `${depth * 16 + 8}px` }}
      >
        {hasChildren ? (
          expanded ? (
            <ChevronDown className="w-3 h-3 text-muted-foreground" />
          ) : (
            <ChevronRight className="w-3 h-3 text-muted-foreground" />
          )
        ) : (
          <div className="w-3" />
        )}
        {getStatusIcon()}
        <span className="flex-1 text-left truncate">{span.name}</span>
        {span.duration_ms && (
          <span className="text-xs text-muted-foreground">
            {span.duration_ms >= 1000
              ? `${(span.duration_ms / 1000).toFixed(1)}s`
              : `${span.duration_ms}ms`}
          </span>
        )}
      </button>
      {hasChildren && expanded && (
        <div>
          {span.children.map((child) => (
            <TraceSpanTree key={child.id} span={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  )
}

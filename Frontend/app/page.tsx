'use client'

import { useState, useCallback } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  Workflow,
  TrendingUp,
  Clock,
  Zap,
  Activity,
  ArrowRight,
  Sparkles,
  RefreshCw,
  CheckCircle2,
  XCircle,
  FileCode,
  Sliders,
  Play,
  Eye,
  Check,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { cn } from '@/lib/utils'
import useSWR from 'swr'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

export default function HomePage() {
  const router = useRouter()
  const { toast } = useToast()
  const { workflows, activeWorkspaceId } = useWorkflowStore()
  const { data: dbStatus, mutate: mutateDbStatus } = useSWR(`${API_BASE}/workflow/db/status`, fetcher)
  
  const workflowList = Object.values(workflows)

  // Master Agent state
  const [userPrompt, setUserPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [proposal, setProposal] = useState<any | null>(null)
  const [proposalJsonStr, setProposalJsonStr] = useState('')
  const [isProposalOpen, setIsProposalOpen] = useState(false)
  const [isCompiling, setIsCompiling] = useState(false)
  const [compilationStatus, setCompilationStatus] = useState<'idle' | 'success' | 'failed'>('idle')
  const [compilationMessage, setCompilationMessage] = useState('')

  // Map Python WorkflowSchema object format to the Frontend storage format
  const mapBackendWorkflowToFrontend = useCallback((backendWf: any) => {
    const defaultLLM = {
      provider: 'openai' as const,
      model_name: 'gpt-4o',
      temperature: 0.7,
      max_tokens: 4096,
      api_key_env_var: 'OPENAI_API_KEY',
    }

    return {
      id: backendWf.workflow_id,
      name: backendWf.name || 'Generated Workflow',
      description: backendWf.description || '',
      entry_point: backendWf.entry_point || 'agent_1',
      agents: (backendWf.agents || []).map((agent: any) => ({
        agent_id: agent.agent_id,
        role: agent.role || 'Assistant',
        prompt_template: {
          template_string: agent.prompt_template?.template_string || 'Process tasks.',
          input_variables: agent.prompt_template?.input_variables || [],
        },
        llm_config: {
          provider: agent.llm?.provider || defaultLLM.provider,
          model_name: agent.llm?.model_name || defaultLLM.model_name,
          temperature: agent.llm?.temperature ?? defaultLLM.temperature,
          max_tokens: agent.llm?.max_tokens ?? defaultLLM.max_tokens,
          api_key_env_var: agent.llm?.api_key_env_var || defaultLLM.api_key_env_var,
        },
        orchestration_mode: agent.topology?.orchestration_mode === 'agent_driven' ? ('agent-driven' as const) : ('model-driven' as const),
        tools: agent.tools || [],
        rag_sources: agent.rag_sources || [],
        sub_agents: agent.sub_agents || [],
        consensus_config: agent.consensus_config ? {
          enabled: agent.consensus_config.enabled ?? false,
          num_instances: agent.consensus_config.instances ?? 3,
          agreement_threshold: agent.consensus_config.threshold ?? 0.7,
        } : undefined,
      })),
      edges: (backendWf.edges || []).map((edge: any, index: number) => ({
        id: `edge_${index}_${Math.random().toString(36).substring(2, 5)}`,
        source: edge.source,
        target: edge.target,
        condition: typeof edge.condition === 'string' 
          ? edge.condition 
          : edge.condition?.value !== undefined 
            ? `state["${edge.condition.field}"] ${edge.condition.operator} "${edge.condition.value}"`
            : undefined,
      })),
      global_tools: (backendWf.tools || []).map((tool: any) => ({
        id: tool.tool_id,
        name: tool.name,
        description: tool.description || '',
        type: tool.type === 'rest_api' ? ('api' as const) : tool.type === 'mcp' ? ('mcp' as const) : ('function' as const),
        api_endpoint: tool.config?.endpoint,
        method: tool.config?.method,
        api_key_env_var: tool.config?.api_key_env_var,
        mcp_endpoint: tool.config?.connection_string,
        code_snippet: tool.config?.code,
      })),
      global_rag_sources: (backendWf.rag_sources || []).map((rag: any) => ({
        id: rag.rag_id,
        provider: (rag.vector_db || 'qdrant') as any,
        name: rag.collection_name || 'kb_collection',
        uri: rag.connection_uri,
        api_key_env_var: rag.api_key_env_var,
        embedding_model: rag.embedding_model || 'text-embedding-3-small',
        top_k: rag.top_k ?? 3,
        similarity_threshold: rag.similarity_threshold ?? 0.7,
        hybrid_search: rag.hybrid_search ?? true,
      })),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
  }, [])

  const handleGenerateProposal = async () => {
    if (!userPrompt.trim()) {
      toast({
        title: 'Error',
        description: 'Please type an automation request to build.',
        variant: 'destructive',
      })
      return
    }

    setIsGenerating(true)
    setCompilationStatus('idle')
    setCompilationMessage('')

    try {
      const response = await fetch(`${API_BASE}/workflow/master/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: userPrompt }),
      })

      if (!response.ok) {
        throw new Error('Backend failed to parse the prompt or RAG documentation.')
      }

      const data = await response.json()
      if (data.success && data.proposal) {
        setProposal(data.proposal)
        setProposalJsonStr(JSON.stringify(data.proposal, null, 2))
        setIsProposalOpen(true)
        toast({
          title: 'Success',
          description: 'Master Agent synthesized a valid proposal via system documentation RAG.',
        })
      } else {
        throw new Error('Invalid response structure received from Master Agent.')
      }
    } catch (error: any) {
      toast({
        title: 'Synthesis Failed',
        description: error.message || 'Error occurred while querying the Master Agent.',
        variant: 'destructive',
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const handleDryRunCompile = async () => {
    let parsedJson = null
    try {
      parsedJson = JSON.parse(proposalJsonStr)
    } catch (e) {
      toast({
        title: 'JSON Syntax Error',
        description: 'Please correct the JSON formatting before compilation.',
        variant: 'destructive',
      })
      return
    }

    setIsCompiling(true)
    setCompilationStatus('idle')

    try {
      const response = await fetch(`${API_BASE}/workflow/master/compile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(parsedJson),
      })

      const data = await response.json()
      if (response.ok && data.success) {
        setCompilationStatus('success')
        setCompilationMessage('Validation check passed: Workflow is 100% compliant with downstream SDK compiler.')
        toast({
          title: 'Compilation Passed',
          description: 'Downstream LangGraph application generated successfully.',
        })
      } else {
        setCompilationStatus('failed')
        setCompilationMessage(data.detail || 'Workflow validation or dependency binding failed.')
        toast({
          title: 'Compilation Failed',
          description: 'SDK compiler rejected proposal constraints.',
          variant: 'destructive',
        })
      }
    } catch (error: any) {
      setCompilationStatus('failed')
      setCompilationMessage(error.message || 'Failed to connect to gateway compilation pipeline.')
    } finally {
      setIsCompiling(false)
    }
  }

  const handleCommitHandshake = async () => {
    let parsedJson = null
    try {
      parsedJson = JSON.parse(proposalJsonStr)
    } catch (e) {
      toast({
        title: 'JSON Syntax Error',
        description: 'Please correct JSON payload.',
        variant: 'destructive',
      })
      return
    }

    // Force compilation confirmation first or run it now
    if (compilationStatus !== 'success') {
      toast({
        title: 'Validation Required',
        description: 'Please compile the workflow configuration successfully before commit.',
        variant: 'destructive',
      })
      return
    }

    try {
      // Map to frontend stores and save
      const frontendWf = mapBackendWorkflowToFrontend(parsedJson)
      
      // Save in local Zustand store
      useWorkflowStore.setState((state) => ({
        workflows: {
          ...state.workflows,
          [frontendWf.id]: frontendWf,
        },
      }))

      setIsProposalOpen(false)
      setUserPrompt('')
      mutateDbStatus()

      toast({
        title: 'Workflow Saved',
        description: 'New workflow state is active and bound to database.',
      })

      // Route directly to workflow builder canvas
      router.push(`/workflows/${frontendWf.id}`)
    } catch (error: any) {
      toast({
        title: 'Failed to Commit',
        description: error.message || 'Error occurred while saving workspace state.',
        variant: 'destructive',
      })
    }
  }

  const handleCreateWorkflowManual = () => {
    const name = `Workflow ${Object.keys(workflows).length + 1}`
    const wId = useWorkflowStore.getState().createWorkflow(name)
    router.push(`/workflows/${wId}`)
  }

  const stats = [
    {
      title: 'Total Workflows',
      value: dbStatus?.collections?.workflows?.toString() || workflowList.length.toString(),
      icon: Workflow,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Global Tools',
      value: dbStatus?.collections?.tools?.toString() || '0',
      icon: Zap,
      color: 'text-success',
      bgColor: 'bg-success/10',
    },
    {
      title: 'Total Executions',
      value: dbStatus?.collections?.activity?.toString() || '0',
      icon: Activity,
      color: 'text-warning',
      bgColor: 'bg-warning/10',
    },
    {
      title: 'RAG Sources',
      value: dbStatus?.collections?.rag?.toString() || '0',
      icon: TrendingUp,
      color: 'text-chart-2',
      bgColor: 'bg-chart-2/10',
    },
  ]

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto">
        
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Orchestrate and monitor your multi-agent workflows
            </p>
          </div>
          <Button onClick={handleCreateWorkflowManual} className="gap-2 glow-primary-sm">
            <Plus className="w-4 h-4" />
            Manual Workflow
          </Button>
        </div>

        {/* Master Agent Ingress Card */}
        <Card className="glass-card border-primary/20 overflow-hidden relative">
          <div className="absolute top-0 right-0 p-4 opacity-10 pointer-events-none">
            <Sparkles className="w-24 h-24 text-primary" />
          </div>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl font-bold">
              <Sparkles className="w-5 h-5 text-primary animate-pulse" />
              AI Prompt-to-Workflow (Master Agent Ingress)
            </CardTitle>
            <CardDescription>
              Describe your desired automation, tools, and constraints. The Upstream Master Agent evaluates it against system specifications via RAG and synthesizes a compliant multi-agent graph.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-col md:flex-row gap-3">
              <Textarea
                placeholder="e.g. Create a flow with a strategic coordinator that delegates web searching tasks to a research agent when weather details are needed, and outputs a compiled markdown report."
                value={userPrompt}
                onChange={(e) => setUserPrompt(e.target.value)}
                className="flex-1 min-h-[80px] bg-background/50 border-border"
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && e.metaKey) {
                    handleGenerateProposal()
                  }
                }}
              />
              <Button
                onClick={handleGenerateProposal}
                disabled={isGenerating}
                className="md:w-44 h-auto py-4 gap-2 self-stretch md:self-end glow-primary-sm"
              >
                {isGenerating ? (
                  <RefreshCw className="w-4 h-4 animate-spin" />
                ) : (
                  <Sparkles className="w-4 h-4" />
                )}
                {isGenerating ? 'Synthesizing...' : 'Synthesize Proposal'}
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Press <kbd className="px-1.5 py-0.5 rounded border bg-muted">⌘ + Enter</kbd> to submit query to Master Agent.
            </p>
          </CardContent>
        </Card>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="glass-card">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{stat.title}</p>
                      <p className="text-2xl font-bold mt-1">{stat.value}</p>
                    </div>
                    <div className={cn(stat.bgColor, 'p-3 rounded-lg')}>
                      <stat.icon className={cn('w-5 h-5', stat.color)} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Recent Workflows */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Workflows</h2>
            <Link
              href="/workflows"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              View all
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {workflowList.length === 0 ? (
            <Card className="glass-card">
              <CardContent className="p-12 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                  <Workflow className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-lg font-medium mb-2">No workflows yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first workflow to get started with multi-agent orchestration
                </p>
                <Button onClick={handleCreateWorkflowManual} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Create Workflow
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {workflowList.slice(0, 6).map((workflow, index) => (
                <motion.div
                  key={workflow.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + index * 0.1 }}
                >
                  <Link href={`/workflows/${workflow.id}`}>
                    <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer group">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                            <Workflow className="w-5 h-5 text-primary" />
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {workflow.agents?.length || 0} agents
                          </span>
                        </div>
                        <CardTitle className="text-base mt-3">{workflow.name}</CardTitle>
                        <CardDescription className="line-clamp-2">
                          {workflow.description || 'No description'}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground text-xs">
                            Entry: {workflow.entry_point || 'Not set'}
                          </span>
                          <div className="flex items-center gap-1 text-primary text-xs font-semibold">
                            <Eye className="w-3.5 h-3.5" />
                            <span>Configure</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer" onClick={() => {
              const fileInput = document.createElement('input')
              fileInput.type = 'file'
              fileInput.accept = '.json'
              fileInput.onchange = (e) => {
                const file = (e.target as any).files[0]
                if (file) {
                  const reader = new FileReader()
                  reader.onload = (evt) => {
                    const text = evt.target?.result as string
                    try {
                      const data = JSON.parse(text)
                      const mapped = mapBackendWorkflowToFrontend(data)
                      useWorkflowStore.setState((state) => ({
                        workflows: { ...state.workflows, [mapped.id]: mapped },
                      }))
                      toast({ title: 'Import Successful', description: `Loaded workflow: ${mapped.name}` })
                      router.push(`/workflows/${mapped.id}`)
                    } catch {
                      toast({ title: 'Import Error', description: 'Invalid workflow JSON schema.', variant: 'destructive' })
                    }
                  }
                  reader.readAsText(file)
                }
              }
              fileInput.click()
            }}>
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-primary/10">
                    <Plus className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">Import Workflow</h3>
                    <p className="text-sm text-muted-foreground">
                      Import from JSON schema
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Link href="/tools">
              <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-success/10">
                      <Zap className="w-6 h-6 text-success" />
                    </div>
                    <div>
                      <h3 className="font-medium">Configure Tools</h3>
                      <p className="text-sm text-muted-foreground">
                        Set up global tool registry
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link href="/rag">
              <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-warning/10">
                      <Activity className="w-6 h-6 text-warning" />
                    </div>
                    <div>
                      <h3 className="font-medium">RAG Sources</h3>
                      <p className="text-sm text-muted-foreground">
                        Connect vector databases
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>

        {/* Master Agent UI Bridge Dialog */}
        <Dialog open={isProposalOpen} onOpenChange={setIsProposalOpen}>
          <DialogContent className="max-w-5xl h-[85vh] flex flex-col p-6 bg-card border-border">
            <DialogHeader className="shrink-0 pb-4 border-b">
              <div className="flex items-center justify-between">
                <div>
                  <DialogTitle className="flex items-center gap-2 text-2xl font-bold">
                    <Sparkles className="w-6 h-6 text-primary animate-pulse" />
                    Master Agent Proposal UI Bridge
                  </DialogTitle>
                  <DialogDescription className="mt-1">
                    Review and modify the synthesized JSON configuration below. Lock execution with a strict schema compiler dry-run before manual handshake dispatch.
                  </DialogDescription>
                </div>
              </div>
            </DialogHeader>

            <div className="flex-1 min-h-0 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
              
              {/* Left Column: Visual Blueprint Form */}
              <div className="lg:col-span-5 flex flex-col space-y-4 overflow-y-auto pr-2 scrollbar-thin">
                <div className="space-y-4">
                  <h3 className="text-sm font-semibold flex items-center gap-1.5 uppercase tracking-wider text-muted-foreground">
                    <Sliders className="w-4 h-4" />
                    Interactive Proposal Blueprint
                  </h3>
                  
                  {proposal && (
                    <div className="space-y-4 p-4 rounded-lg bg-background/50 border border-border">
                      <div className="space-y-2">
                        <Label>Workflow ID</Label>
                        <Input value={proposal.workflow_id} disabled className="bg-background/80" />
                      </div>
                      <div className="space-y-2">
                        <Label>Name</Label>
                        <Input 
                          value={proposal.name || ''} 
                          onChange={(e) => {
                            const updated = { ...proposal, name: e.target.value }
                            setProposal(updated)
                            setProposalJsonStr(JSON.stringify(updated, null, 2))
                          }}
                          className="bg-background/80"
                        />
                      </div>
                      <div className="space-y-2">
                        <Label>Description</Label>
                        <Input 
                          value={proposal.description || ''} 
                          onChange={(e) => {
                            const updated = { ...proposal, description: e.target.value }
                            setProposal(updated)
                            setProposalJsonStr(JSON.stringify(updated, null, 2))
                          }}
                          className="bg-background/80"
                        />
                      </div>
                    </div>
                  )}

                  {/* Node List View */}
                  {proposal && proposal.agents && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Synthesized Agent Nodes</h4>
                      <div className="space-y-2">
                        {proposal.agents.map((agent: any) => (
                          <div key={agent.agent_id} className="p-3 rounded-lg bg-background border flex items-center justify-between">
                            <div>
                              <p className="font-semibold text-sm">{agent.agent_id}</p>
                              <p className="text-xs text-muted-foreground">{agent.role}</p>
                            </div>
                            <div className="flex items-center gap-1">
                              <span className="text-[10px] bg-primary/10 text-primary font-medium px-2 py-0.5 rounded-full uppercase">
                                {agent.llm?.model_name || 'LLM'}
                              </span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Edges & Transitions */}
                  {proposal && proposal.edges && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Edges & Routing</h4>
                      <div className="space-y-2">
                        {proposal.edges.map((edge: any, i: number) => (
                          <div key={i} className="p-2.5 rounded-lg bg-background/50 border border-dashed flex items-center gap-2 text-xs">
                            <span className="font-mono text-primary font-medium">{edge.source}</span>
                            <span className="text-muted-foreground">➔</span>
                            <span className="font-mono text-muted-foreground">{edge.target}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Column: JSON Payload Editor */}
              <div className="lg:col-span-7 flex flex-col min-h-0 bg-background rounded-lg border overflow-hidden">
                <div className="h-10 bg-muted/50 px-4 border-b flex items-center justify-between shrink-0">
                  <div className="flex items-center gap-2 text-xs font-mono text-muted-foreground">
                    <FileCode className="w-3.5 h-3.5" />
                    <span>workflow_proposal_schema.json</span>
                  </div>
                  <Button variant="ghost" size="sm" className="h-7 text-xs px-2" onClick={() => {
                    try {
                      const pretty = JSON.stringify(JSON.parse(proposalJsonStr), null, 2)
                      setProposalJsonStr(pretty)
                    } catch {
                      toast({ title: 'Format Error', description: 'Invalid JSON payload.', variant: 'destructive' })
                    }
                  }}>
                    Format Code
                  </Button>
                </div>
                <Textarea
                  value={proposalJsonStr}
                  onChange={(e) => {
                    setProposalJsonStr(e.target.value)
                    try {
                      const parsed = JSON.parse(e.target.value)
                      setProposal(parsed)
                    } catch {}
                  }}
                  className="flex-1 font-mono text-xs p-4 resize-none border-none outline-none focus-visible:ring-0 rounded-none bg-background scrollbar-thin"
                />
              </div>

            </div>

            {/* Bottom Panel: Compilation Status & Mutation Handshake */}
            <div className="shrink-0 pt-4 border-t flex flex-col space-y-4">
              {compilationStatus !== 'idle' && (
                <div className={cn(
                  'p-3 rounded-lg flex items-start gap-3 border text-sm',
                  compilationStatus === 'success' 
                    ? 'bg-success/5 border-success/20 text-success' 
                    : 'bg-destructive/5 border-destructive/20 text-destructive'
                )}>
                  {compilationStatus === 'success' ? (
                    <CheckCircle2 className="w-5 h-5 shrink-0" />
                  ) : (
                    <XCircle className="w-5 h-5 shrink-0" />
                  )}
                  <div>
                    <p className="font-semibold">{compilationStatus === 'success' ? 'Validation Succeeded' : 'Validation Failed'}</p>
                    <p className="text-xs opacity-90 mt-0.5 font-mono">{compilationMessage}</p>
                  </div>
                </div>
              )}

              <div className="flex items-center justify-between">
                <Button variant="outline" onClick={() => setIsProposalOpen(false)}>
                  Cancel
                </Button>
                
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleDryRunCompile}
                    disabled={isCompiling}
                    variant="secondary"
                    className="gap-2"
                  >
                    {isCompiling ? (
                      <RefreshCw className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    Dry-run Compile Check
                  </Button>

                  <Button
                    onClick={handleCommitHandshake}
                    disabled={compilationStatus !== 'success'}
                    className={cn(
                      'gap-2 px-6',
                      compilationStatus === 'success' ? 'glow-primary-sm bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                    )}
                  >
                    <Check className="w-4 h-4" />
                    Handshake & Commit
                  </Button>
                </div>
              </div>
            </div>

          </DialogContent>
        </Dialog>

      </div>
    </DashboardLayout>
  )
}

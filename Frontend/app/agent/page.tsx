'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import {
  Send,
  Bot,
  Sparkles,
  CheckCircle2,
  XCircle,
  Loader2,
  Check,
  Play,
  Copy,
  Key,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { useWorkflowStore } from '@/lib/store'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { WorkflowBuilder } from '@/components/workflow-builder'
import type { ProposalResponse } from '@/lib/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

export default function AgentPage() {
  const router = useRouter()
  const { toast } = useToast()
  const { createWorkflow, setActiveWorkflow } = useWorkflowStore()
  const token = useAuthStore((s) => s.token)

  const [prompt, setPrompt] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'assistant',
      content: "Hello! I'm the **Master Agent**. Describe the automation workflow you want to build, and I'll generate a complete multi-agent workflow for you.\n\nTry something like:\n- *\"Create a customer support agent that can answer FAQs and escalate to a human\"*\n- *\"Build a research pipeline that searches the web, summarizes findings, and emails a report\"*\n- *\"Make an agent that monitors social media sentiment and posts responses\"*",
      timestamp: new Date(),
    },
  ])
  const [isGenerating, setIsGenerating] = useState(false)

  // Proposal state
  const [proposal, setProposal] = useState<ProposalResponse | null>(null)
  const [proposalJsonStr, setProposalJsonStr] = useState('')
  const [isProposalOpen, setIsProposalOpen] = useState(false)
  const [isCompiling, setIsCompiling] = useState(false)
  const [compilationStatus, setCompilationStatus] = useState<'idle' | 'success' | 'failed'>('idle')
  const [compilationMessage, setCompilationMessage] = useState('')
  const [deployedApiKey, setDeployedApiKey] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const authHeaders: Record<string, string> = token
    ? { 'Authorization': `Bearer ${token}` }
    : {}

  const sendMessage = async () => {
    if (!prompt.trim() || isGenerating) return

    const userMsg: ChatMessage = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: prompt,
      timestamp: new Date(),
    }
    setMessages((prev) => [...prev, userMsg])
    setPrompt('')
    setIsGenerating(true)
    setCompilationStatus('idle')
    setCompilationMessage('')

    try {
      const response = await fetch(`${API_BASE_URL}/workflow/master/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify({ prompt }),
      })

      if (!response.ok) {
        throw new Error('Failed to generate workflow proposal')
      }

      const data = await response.json()
      if (!data.success || !data.proposal) {
        throw new Error('Invalid response from Master Agent')
      }

      const proposalData = data.proposal as ProposalResponse
      setProposal(proposalData)
      setProposalJsonStr(JSON.stringify(proposalData, null, 2))
      setIsProposalOpen(true)

      const assistantMsg: ChatMessage = {
        id: `msg_${Date.now()}_resp`,
        role: 'assistant',
        content: `I've generated a **${proposalData.agents?.length || 0}-agent workflow** called "${proposalData.name}". Opening the proposal for review...`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      const errorMsg: ChatMessage = {
        id: `msg_${Date.now()}_err`,
        role: 'assistant',
        content: `Error: ${err instanceof Error ? err.message : 'Failed to generate proposal'}`,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
      toast({
        title: 'Generation Failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      })
    } finally {
      setIsGenerating(false)
    }
  }

  const handleCompile = async () => {
    let parsedJson: ProposalResponse
    try {
      parsedJson = JSON.parse(proposalJsonStr)
    } catch {
      toast({ title: 'JSON Error', description: 'Invalid JSON syntax', variant: 'destructive' })
      return
    }

    setIsCompiling(true)
    setCompilationStatus('idle')

    try {
      const response = await fetch(`${API_BASE_URL}/workflow/master/compile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders },
        body: JSON.stringify(parsedJson),
      })

      const data = await response.json()
      if (response.ok && data.success) {
        setCompilationStatus('success')
        setCompilationMessage('Workflow validated and compiled successfully')
        if (data.api_key) {
          setDeployedApiKey(data.api_key)
        }
        toast({ title: 'Compilation Passed', description: 'Workflow is ready to deploy' })
      } else {
        setCompilationStatus('failed')
        setCompilationMessage(data.detail || 'Workflow validation failed')
        toast({ title: 'Compilation Failed', description: data.detail || 'SDK compiler rejected the proposal', variant: 'destructive' })
      }
    } catch (err) {
      setCompilationStatus('failed')
      setCompilationMessage(err instanceof Error ? err.message : 'Connection failed')
    } finally {
      setIsCompiling(false)
    }
  }

  const handleDeploy = () => {
    if (compilationStatus !== 'success') {
      toast({ title: 'Compile First', description: 'Please compile the workflow before deploying', variant: 'destructive' })
      return
    }

    try {
      const parsedJson = JSON.parse(proposalJsonStr)
      const frontendWf = mapProposalToWorkflow(parsedJson)

      useWorkflowStore.setState((state) => ({
        workflows: { ...state.workflows, [frontendWf.id]: frontendWf },
      }))

      setIsProposalOpen(false)
      setActiveWorkflow(frontendWf.id)
      toast({ title: 'Workflow Deployed', description: `${frontendWf.name} is now in your workspace` })
      router.push(`/workflows/${frontendWf.id}`)
    } catch (err) {
      toast({ title: 'Deploy Failed', description: err instanceof Error ? err.message : 'Unknown error', variant: 'destructive' })
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <DashboardLayout>
      <div className="flex flex-col h-[calc(100vh-4rem)]">
        {/* Header */}
        <div className="border-b border-border p-4 flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-primary/20 flex items-center justify-center">
            <Bot className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Master Agent</h1>
            <p className="text-sm text-muted-foreground">
              Describe your automation, I&apos;ll build the workflow
            </p>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0 mt-1">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
              )}
              <div
                className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-br-md'
                    : 'bg-card border border-border rounded-bl-md'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
              {msg.role === 'user' && (
                <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center shrink-0 mt-1">
                  <span className="text-xs text-primary-foreground font-medium">You</span>
                </div>
              )}
            </motion.div>
          ))}

          {isGenerating && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-3"
            >
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-primary" />
              </div>
              <div className="bg-card border border-border rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Generating workflow...
                </div>
              </div>
            </motion.div>
          )}
        </div>

        {/* Input */}
        <div className="border-t border-border p-4">
          <div className="flex gap-3 max-w-4xl mx-auto">
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe the workflow you want to build..."
              className="min-h-[48px] max-h-[120px] resize-none"
              rows={1}
              disabled={isGenerating}
            />
            <Button
              onClick={sendMessage}
              disabled={!prompt.trim() || isGenerating}
              className="shrink-0 h-[48px] px-4"
            >
              {isGenerating ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* Proposal Dialog */}
      <Dialog open={isProposalOpen} onOpenChange={setIsProposalOpen}>
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-primary" />
              Workflow Proposal
            </DialogTitle>
            <DialogDescription>
              {proposal?.name || 'Generated Workflow'} &middot; {proposal?.agents?.length || 0} agents &middot; {proposal?.edges?.length || 0} connections
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">{proposal?.name}</CardTitle>
                <CardDescription>{proposal?.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {proposal?.agents?.map((agent) => (
                    <Badge key={agent.agent_id} variant="secondary">
                      {agent.role} ({agent.agent_id})
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Compile status */}
            {compilationStatus === 'success' && (
              <div className="flex items-center gap-2 text-sm text-success bg-success/10 rounded-lg p-3">
                <CheckCircle2 className="w-4 h-4" />
                {compilationMessage}
              </div>
            )}
            {compilationStatus === 'failed' && (
              <div className="flex items-center gap-2 text-sm text-destructive bg-destructive/10 rounded-lg p-3">
                <XCircle className="w-4 h-4" />
                {compilationMessage}
              </div>
            )}

            {/* One-time API key banner */}
            {deployedApiKey && (
              <div className="border border-primary/30 bg-primary/5 rounded-lg p-4 space-y-3">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Key className="w-4 h-4 text-primary" />
                  Workflow API Key
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 px-3 py-2 bg-muted rounded-md text-xs font-mono break-all">
                    {deployedApiKey}
                  </code>
                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0 gap-1"
                    onClick={async () => {
                      await navigator.clipboard.writeText(deployedApiKey)
                      setCopied(true)
                      toast({ title: 'Copied', description: 'API key copied to clipboard' })
                      setTimeout(() => setCopied(false), 2000)
                    }}
                  >
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  ⚠️ This key will only be shown once. Store it securely. You can regenerate it from the workflow settings later.
                </p>
              </div>
            )}

            {/* Workflow Builder — Visual Editor + Raw JSON */}
            <WorkflowBuilder
              value={proposalJsonStr}
              onChange={(v) => {
                setProposalJsonStr(v)
                setCompilationStatus('idle')
              }}
              onStatusChange={() => setCompilationStatus('idle')}
            />
          </div>

          <div className="flex items-center justify-between gap-3 pt-2">
            <Button variant="outline" onClick={() => setIsProposalOpen(false)}>
              Cancel
            </Button>
            <div className="flex items-center gap-2">
              <Button
                variant="secondary"
                onClick={handleCompile}
                disabled={isCompiling}
              >
                {isCompiling ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                Validate & Compile
              </Button>
              <Button
                onClick={handleDeploy}
                disabled={compilationStatus !== 'success'}
              >
                <Check className="w-4 h-4 mr-2" />
                Deploy to Workspace
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </DashboardLayout>
  )
}

function mapProposalToWorkflow(proposal: ProposalResponse) {
  const defaultLLM = {
    provider: 'openai' as const,
    model_name: 'gpt-4o',
    temperature: 0.7,
    max_tokens: 4096,
    api_key_env_var: 'OPENAI_API_KEY',
  }

  return {
    id: proposal.workflow_id,
    name: proposal.name || 'Generated Workflow',
    description: proposal.description || '',
    entry_point: proposal.entry_point || 'coordinator',
    agents: (proposal.agents || []).map((agent) => ({
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
    edges: (proposal.edges || []).map((edge, index) => ({
      id: `edge_${index}_${Math.random().toString(36).substring(2, 5)}`,
      source: edge.source,
      target: edge.target,
      condition: typeof edge.condition === 'string'
        ? edge.condition
        : edge.condition?.value !== undefined
          ? `state["${edge.condition.field}"] ${edge.condition.operator} "${edge.condition.value}"`
          : undefined,
    })),
    global_tools: (proposal.tools || []).map((tool) => ({
      id: tool.tool_id,
      name: tool.name,
      description: tool.description || '',
      type: tool.type === 'rest_api' ? ('api' as const) : tool.type === 'mcp' ? ('mcp' as const) : ('function' as const),
      api_endpoint: tool.config?.endpoint as string | undefined,
      method: tool.config?.method as string | undefined,
      api_key_env_var: tool.config?.api_key_env_var as string | undefined,
    })),
    global_rag_sources: (proposal.rag_sources || []).map((rag) => ({
      id: rag.rag_id,
      provider: (rag.provider || 'qdrant') as any,
      name: rag.collection_name || 'kb_collection',
      uri: rag.connection_uri as string | undefined,
      api_key_env_var: rag.api_key_env_var as string | undefined,
      embedding_model: rag.embedding_model || 'text-embedding-3-small',
      top_k: rag.top_k ?? 3,
      similarity_threshold: rag.similarity_threshold ?? 0.7,
      hybrid_search: true,
    })),
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  }
}

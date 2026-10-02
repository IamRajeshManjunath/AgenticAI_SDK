'use client'

import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { RefreshCw, Zap, Sparkles, Download, FileCode, Copy, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

export default function MasterAgentPage() {
  const [prompt, setPrompt] = useState('')
  const [isGenerating, setIsGenerating] = useState(false)
  const [proposal, setProposal] = useState<any>(null)
  const [proposalJsonStr, setProposalJsonStr] = useState('')
  const [isProposalOpen, setIsProposalOpen] = useState(false)
  const [isCompiling, setIsCompiling] = useState(false)
  const [compilationStatus, setCompilationStatus] = useState<'idle' | 'success' | 'failed'>('idle')
  const [compilationMessage, setCompilationMessage] = useState('')

  const { token } = useAuthStore()

  const handleGenerateProposal = useCallback(async () => {
    if (!prompt.trim()) {
      alert('Please enter a prompt')
      return
    }

    setIsGenerating(true)
    setCompilationStatus('idle')
    setCompilationMessage('')

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/master/generate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({ prompt }),
      })

      if (!response.ok) {
        const error = await response.text()
        throw new Error(error || 'Failed to generate proposal')
      }

      const data = await response.json()
      if (data.success && data.proposal) {
        setProposal(data.proposal)
        setProposalJsonStr(JSON.stringify(data.proposal, null, 2))
        setIsProposalOpen(true)
        alert('Proposal generated successfully!')
      } else {
        throw new Error('Invalid response structure')
      }
    } catch (error) {
      alert(`Generation failed: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsGenerating(false)
    }
  }, [prompt])

  const handleCompile = useCallback(async () => {
    let parsedJson = null
    try {
      parsedJson = JSON.parse(proposalJsonStr)
    } catch (e) {
      alert('Please correct the JSON formatting before compiling.')
      return
    }

    setIsCompiling(true)
    setCompilationStatus('idle')

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/master/compile`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(parsedJson),
      })

      const data = await response.json()
      if (response.ok && data.success) {
        setCompilationStatus('success')
        setCompilationMessage('Validation check passed: Workflow is 100% compliant with downstream SDK compiler.')
        alert('Compilation passed! Workflow is valid.')
      } else {
        setCompilationStatus('failed')
        setCompilationMessage(data.detail || 'Workflow validation or dependency binding failed.')
        alert('Compilation failed: ' + (data.detail || 'Unknown error'))
      }
    } catch (error) {
      setCompilationStatus('failed')
      setCompilationMessage(error instanceof Error ? error.message : 'Failed to connect to gateway compilation pipeline.')
    } finally {
      setIsCompiling(false)
    }
  }, [proposalJsonStr])

  const handleDownload = () => {
    const blob = new Blob([proposalJsonStr], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'master-agent-proposal.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleFormat = () => {
    try {
      const parsed = JSON.parse(proposalJsonStr)
      setProposalJsonStr(JSON.stringify(parsed, null, 2))
    } catch (e) {
      alert('Invalid JSON')
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Master Agent Ingress</h1>
          <p className="text-muted-foreground mt-1">
            Generate production-ready workflows from natural language prompts using the Master Agent
          </p>
        </div>
      </div>

      {/* Prompt Input Card */}
      <Card className="border-primary/20 overflow-hidden relative">
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
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
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
              className="md:w-44 h-auto py-4 gap-2 self-stretch glow-primary-sm"
            >
              {isGenerating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Zap className="w-4 h-4" />
              )}
              {isGenerating ? 'Generating...' : 'Synthesize Proposal'}
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Press <kbd className="px-1.5 py-0.5 rounded border bg-muted">⌘ + Enter</kbd> to submit query to Master Agent.
          </p>
        </CardContent>
      </Card>

      {/* Proposal Modal */}
      {isProposalOpen && (
        <Dialog open onOpenChange={(open) => !open && setIsProposalOpen(false)}>
          <DialogContent className="max-w-5xl max-h-[85vh] flex flex-col p-6 bg-card border-border">
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
              </DialogHeader>

              <div className="flex-1 min-h-0 py-6 grid grid-cols-1 lg:grid-cols-12 gap-6 overflow-hidden">
                {/* Left Column: Visual Blueprint Form */}
                <div className="lg:col-span-5 flex flex-col space-y-4 overflow-y-auto pr-2 scrollbar-thin">
                  <div className="space-y-4">
                    <h3 className="text-sm font-semibold flex items-center gap-1.5 uppercase tracking-wider text-muted-foreground">
                      <Settings2 className="w-4 h-4" />
                      Interactive Proposal Blueprint
                    </h3>

                    {proposal && (
                      <div className="space-y-4 p-4 rounded-lg bg-background/50 border border-border">
                        <div className="space-y-2">
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
                            <span className="text-muted-foreground">→</span>
                            <span className="font-mono text-muted-foreground">{edge.target}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Tools & RAG Sources */}
                  {proposal && proposal.tools && proposal.tools.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Global Tools</h4>
                      <div className="flex flex-wrap gap-1">
                        {proposal.tools.map((t: any) => (
                          <Badge key={t.tool_id} variant="secondary" className="text-xs gap-1 pr-1">
                            {t.name}
                            <button type="button" onClick={() => {}} className="hover:text-destructive">
                              <X className="w-3 h-3" />
                            </button>
                          </Badge>
                        ))}
                      </div>
                    </div>
                  )}

                  {proposal && proposal.rag_sources && proposal.rag_sources.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">RAG Sources</h4>
                      <div className="space-y-2">
                        {proposal.rag_sources.map((r: any) => (
                          <div key={r.rag_id} className="p-2 rounded-lg bg-background border flex items-center gap-2">
                            <Badge variant="secondary" className="text-xs">{r.provider}</Badge>
                            <span className="text-xs font-mono text-muted-foreground truncate flex-1">{r.collection_name}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* HITL & Budget */}
                  {proposal && (proposal.hitl?.enabled || proposal.policies?.budget) && (
                    <div className="space-y-3">
                      {proposal.hitl?.enabled && (
                        <div className="p-3 rounded-lg bg-background border flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <AlertCircle className="w-4 h-4 text-warning" />
                            <span className="text-sm">HITL enabled - approval required</span>
                          </div>
                        </div>
                      )}
                      {proposal.policies?.budget && (
                        <div className="p-3 rounded-lg bg-background border">
                          <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-2">Budget Guardrails</div>
                          <div className="grid grid-cols-4 gap-2 text-xs">
                            <div><Label>Max Iterations</Label><p className="font-mono">{proposal.policies.budget.maxIterations}</p></div>
                            <div><Label>Max Cost</Label><p className="font-mono">${proposal.policies.budget.maxCostUsd}</p></div>
                            <div><Label>Max Input Tokens</Label><p className="font-mono">{proposal.policies.budget.maxInputTokens}</p></div>
                            <div><Label>Max Output Tokens</Label><p className="font-mono">{proposal.policies.budget.maxOutputTokens}</p></div>
                          </div>
                        </div>
                      )}
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
                  <Button variant="ghost" size="sm" className="h-7 text-xs px-2" onClick={handleFormat}>
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
                    ? 'bg-green-50 border-green-200 text-green-800 dark:bg-green-900/20 dark:border-green-800 dark:text-green-400'
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
                    onClick={handleCompile}
                    disabled={isCompiling}
                    variant="secondary"
                    className="gap-2"
                  >
                    {isCompiling ? (
                      <Loader2 className="w-4 h-4 animate-spin" />
                    ) : (
                      <Play className="w-4 h-4" />
                    )}
                    Dry-run Compile Check
                  </Button>

                  <Button
                    onClick={handleHandshake}
                    disabled={compilationStatus !== 'success'}
                    className={cn(
                      'gap-2 px-6',
                      compilationStatus === 'success' ? 'glow-primary-sm bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'
                    )}
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Handshake & Commit
                  </Button>
                </div>
              </div>
            </div>

          </DialogContent>
        </Dialog>
      )}

      {/* Master Agent Examples */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Zap className="w-4 h-4 text-primary" />
            Example Prompts
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {[
              {
                title: "Research & Report Pipeline",
                prompt: "Create a flow that searches the web for a topic, analyzes the sources, and generates a markdown report with citations.",
                tags: ["web-search", "document-analysis", "reasoning", "code-generation"],
              },
              {
                title: "Code Review Pipeline",
                prompt: "Create a flow that takes a PR diff, runs static analysis, runs tests, and generates a review summary with suggested fixes.",
                tags: ["code-analysis", "testing", "reasoning"],
              },
              {
                title: "Data Processing Pipeline",
                prompt: "Build a flow that ingests CSV data, cleans it with pandas, runs statistical analysis, and outputs visualizations.",
                tags: ["data-processing", "code-generation", "visualization"],
              },
              {
                title: "RAG QA Pipeline",
                prompt: "Build a RAG pipeline that loads documents from Qdrant, embeds queries with OpenAI, retrieves top-k, and synthesizes answers.",
                tags: ["rag", "vector-store", "embedding", "reasoning"],
              },
            ].map((example) => (
              <Button
                key={example.title}
                variant="outline"
                className="w-full justify-start gap-3 p-4 text-left hover:border-primary/50"
                onClick={() => setPrompt(example.prompt)}
              >
                <div className="flex-1 text-left">
                  <h4 className="font-medium">{example.title}</h4>
                  <p className="text-sm text-muted-foreground line-clamp-2">{example.prompt}</p>
                  <div className="flex flex-wrap gap-1 mt-2">
                    {example.tags.map((tag) => (
                      <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                    ))}
                  </div>
                </div>
              </Button>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default MasterAgentPage
'use client'

import { useCallback, useMemo, useState, useEffect } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  MarkerType,
  SelectionMode,
  Handle,
  Position,
} from 'reactflow'
import 'reactflow/dist/style.css'
import {
  Bot,
  Crown,
  Settings2,
  GitBranch,
  Trash2,
  Plus,
  ChevronLeft,
  Check,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import type { ProposalResponse, ProposalAgent, ProposalEdge } from '@/lib/types'

interface ProposalCanvasProps {
  proposal: ProposalResponse
  onUpdate: (proposal: ProposalResponse) => void
}

const nodeTypes = {
  proposalAgent: ProposalAgentNode,
}

export function ProposalCanvas({ proposal, onUpdate }: ProposalCanvasProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedEdgeId, setSelectedEdgeId] = useState<string | null>(null)
  const [edgeConditionText, setEdgeConditionText] = useState('')
  const [isDragging, setIsDragging] = useState(false)

  const toNodes = (agents: ProposalAgent[]): Node[] =>
    agents.map((agent, index) => ({
      id: agent.agent_id,
      type: 'proposalAgent',
      position: { x: 100 + (index % 3) * 320, y: 100 + Math.floor(index / 3) * 200 },
      data: { agent, isEntryPoint: agent.agent_id === proposal.entry_point },
    }))

  const toEdges = (edges: ProposalEdge[]): Edge[] =>
    edges.map((edge, i) => ({
      id: `edge_${i}`,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      animated: true,
      label: edge.condition ? 'conditional' : undefined,
      labelStyle: { fill: 'var(--muted-foreground)', fontSize: 10 },
      labelBgStyle: { fill: 'var(--card)', fillOpacity: 0.8 },
      markerEnd: { type: MarkerType.ArrowClosed, color: 'var(--primary)' },
      style: { stroke: 'var(--primary)', strokeWidth: 2 },
      data: edge,
    }))

  const [nodes, setNodes, onNodesChange] = useNodesState(toNodes(proposal.agents))
  const [edges, setEdges, onEdgesChange] = useEdgesState(toEdges(proposal.edges))

  const onConnect = useCallback(
    (params: Connection) => {
      if (!params.source || !params.target) return
      onUpdate({ ...proposal, edges: [...proposal.edges, { source: params.source, target: params.target }] })
    },
    [proposal, onUpdate]
  )

  const onEdgesDelete = useCallback(
    (edgesToDelete: Edge[]) => {
      const deleted = new Set(edgesToDelete.map((e) => `${e.source}→${e.target}`))
      onUpdate({ ...proposal, edges: proposal.edges.filter((e) => !deleted.has(`${e.source}→${e.target}`)) })
    },
    [proposal, onUpdate]
  )

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id)
    setSelectedEdgeId(null)
  }, [])

  const onEdgeClick = useCallback((_: React.MouseEvent, edge: Edge) => {
    setSelectedEdgeId(edge.id)
    setSelectedNodeId(null)
    const edgeData = edge.data as ProposalEdge | undefined
    const cond = edgeData?.condition
    setEdgeConditionText(typeof cond === 'string' ? cond : '')
  }, [])

  const onPaneClick = useCallback(() => {
    setSelectedNodeId(null)
    setSelectedEdgeId(null)
  }, [])

  const onNodeDragStart = useCallback(() => setIsDragging(true), [])
  const onNodeDragStop = useCallback(
    () => setIsDragging(false),
    []
  )

  const selectedEdgeIndex = selectedEdgeId
    ? proposal.edges.findIndex((_, i) => `edge_${i}` === selectedEdgeId)
    : -1

  const updateEdgeCondition = (condition: string) => {
    if (selectedEdgeIndex < 0) return
    const edges = [...proposal.edges]
    edges[selectedEdgeIndex] = { ...edges[selectedEdgeIndex], condition: condition || undefined }
    onUpdate({ ...proposal, edges })
  }

  const selectedAgent = selectedNodeId
    ? proposal.agents.find((a) => a.agent_id === selectedNodeId)
    : null
  const selectedAgentIndex = selectedNodeId
    ? proposal.agents.findIndex((a) => a.agent_id === selectedNodeId)
    : -1

  const updateAgent = (agent: ProposalAgent) => {
    const agents = [...proposal.agents]
    agents[selectedAgentIndex] = agent
    onUpdate({ ...proposal, agents })
    setSelectedNodeId(agent.agent_id)
  }

  const addAgent = () => {
    const id = `agent_${proposal.agents.length + 1}`
    const newAgent: ProposalAgent = {
      agent_id: id,
      role: 'New Agent',
      prompt_template: { template_string: 'Process the task: {{input}}', input_variables: ['input'] },
      llm: { provider: 'openai', model_name: 'gpt-4o', temperature: 0.5, max_tokens: 4096, api_key_env_var: 'OPENAI_API_KEY' },
      tools: [],
      rag_sources: [],
      sub_agents: [],
    }
    onUpdate({ ...proposal, agents: [...proposal.agents, newAgent] })
    setSelectedNodeId(id)
  }

  const removeAgent = (id: string) => {
    onUpdate({
      ...proposal,
      agents: proposal.agents.filter((a) => a.agent_id !== id),
      edges: proposal.edges.filter((e) => e.source !== id && e.target !== id),
    })
    setSelectedNodeId(null)
  }

  const deleteSelected = () => {
    if (!selectedNodeId) return
    removeAgent(selectedNodeId)
  }

  return (
    <div className="flex gap-4 h-[480px]">
      <div className="flex-1 relative rounded-lg border border-border overflow-hidden">
        <ReactFlow
          key={`flow-${proposal.agents.length}-${proposal.edges.length}`}
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={onNodeClick}
          onEdgeClick={onEdgeClick}
          onPaneClick={onPaneClick}
          onNodeDragStart={onNodeDragStart}
          onNodeDragStop={onNodeDragStop}
          onEdgesDelete={onEdgesDelete}
          nodeTypes={nodeTypes}
          fitView
          selectionMode={SelectionMode.Partial}
          proOptions={{ hideAttribution: true }}
          className="bg-background"
          deleteKeyCode={['Backspace', 'Delete']}
          onNodesDelete={(nodes) => {
            nodes.forEach((n) => removeAgent(n.id))
          }}
        >
          <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="var(--border)" />
          <Controls className="!bg-card !border-border !rounded-lg" />
          <MiniMap className="!bg-card !border-border !rounded-lg" nodeColor="var(--primary)" maskColor="var(--background)" />
        </ReactFlow>

        <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={addAgent} className="gap-1 bg-card/80 backdrop-blur-sm">
            <Plus className="w-3.5 h-3.5" /> Agent
          </Button>
          {selectedNodeId && (
            <Button variant="outline" size="sm" onClick={deleteSelected} className="gap-1 text-destructive bg-card/80 backdrop-blur-sm">
              <Trash2 className="w-3.5 h-3.5" /> Delete
            </Button>
          )}
        </div>
      </div>

      {selectedEdgeId !== null && selectedEdgeIndex >= 0 ? (
        <div className="w-72 shrink-0 border border-border rounded-lg p-4 space-y-3 bg-card">
          <div className="flex items-center justify-between">
            <Label className="text-xs font-semibold">Edge Condition</Label>
            <Button variant="ghost" size="sm" onClick={() => setSelectedEdgeId(null)}>
              <X className="w-4 h-4" />
            </Button>
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary" className="text-xs font-mono">{proposal.edges[selectedEdgeIndex].source}</Badge>
            <span>→</span>
            <Badge variant="secondary" className="text-xs font-mono">{proposal.edges[selectedEdgeIndex].target}</Badge>
          </div>
          <Textarea
            value={edgeConditionText}
            onChange={(e) => {
              setEdgeConditionText(e.target.value)
              updateEdgeCondition(e.target.value)
            }}
            placeholder='state["next_step"] == "review"'
            rows={4}
          />
          <p className="text-xs text-muted-foreground">
            Python expression. Leave empty for unconditional.
          </p>
        </div>
      ) : selectedAgent ? (
        <AgentPropertyPanel
          agent={selectedAgent}
          agents={proposal.agents}
          globalTools={proposal.tools}
          globalRagSources={proposal.rag_sources}
          onUpdate={updateAgent}
          onClose={() => setSelectedNodeId(null)}
        />
      ) : (
        <div className="w-72 shrink-0 flex flex-col items-center justify-center text-center text-muted-foreground border border-dashed border-border rounded-lg">
          <GitBranch className="w-8 h-8 mb-2 opacity-40" />
          <p className="text-sm">Click a node to edit agent properties</p>
          <p className="text-xs mt-1">Click an edge to set conditions</p>
        </div>
      )}
    </div>
  )
}

function ProposalAgentNode({ data, selected }: { data: { agent: ProposalAgent; isEntryPoint: boolean }; selected: boolean }) {
  const agent = data.agent
  const isCoordinator = agent.sub_agents && agent.sub_agents.length > 0

  return (
    <div
      className={cn(
        'px-3 py-2.5 rounded-xl min-w-[180px] max-w-[240px] bg-card/80 backdrop-blur-sm border-2 transition-all duration-200 cursor-pointer',
        selected ? 'border-primary shadow-lg' : 'border-border hover:border-primary/50',
        data.isEntryPoint && 'ring-2 ring-success/50 ring-offset-2 ring-offset-background'
      )}
    >
      {data.isEntryPoint && (
        <div className="absolute -top-2 -left-2 px-2 py-0.5 bg-success text-success-foreground text-xs font-medium rounded-full z-10">
          Entry
        </div>
      )}
      <Handle type="target" position={Position.Left} className="!w-3 !h-3 !bg-primary !border-2 !border-background" />
      <div className="flex items-start gap-2.5">
        <div className={cn('p-1.5 rounded-lg shrink-0', isCoordinator ? 'bg-warning/20' : 'bg-primary/20')}>
          {isCoordinator ? <Crown className="w-4 h-4 text-warning" /> : <Bot className="w-4 h-4 text-primary" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-sm text-foreground truncate">{agent.agent_id}</p>
          <p className="text-xs text-muted-foreground truncate">{agent.role}</p>
        </div>
      </div>
      <div className="flex items-center gap-1.5 mt-2 flex-wrap">
        <span className="px-1.5 py-0.5 bg-secondary rounded text-xs text-secondary-foreground">
          {agent.llm.model_name}
        </span>
        <span className={cn(
          'px-1.5 py-0.5 rounded text-xs',
          agent.topology?.orchestration_mode === 'agent_driven'
            ? 'bg-chart-4/20 text-chart-4' : 'bg-chart-2/20 text-chart-2'
        )}>
          {agent.topology?.orchestration_mode === 'agent_driven' ? 'Auto' : 'Model'}
        </span>
      </div>
      <Handle type="source" position={Position.Right} className="!w-3 !h-3 !bg-primary !border-2 !border-background" />
    </div>
  )
}

/* ── Tag input helper ───────────────────────────────────────────────── */

function TagInput({
  tags,
  onChange,
  placeholder,
  suggestions,
}: {
  tags: string[]
  onChange: (tags: string[]) => void
  placeholder?: string
  suggestions?: string[]
}) {
  const [input, setInput] = useState('')

  const add = (value: string) => {
    const trimmed = value.trim()
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed])
    }
    setInput('')
  }

  const remove = (tag: string) => onChange(tags.filter((t) => t !== tag))

  return (
    <div className="space-y-1.5">
      <div className="flex flex-wrap gap-1 mb-1">
        {tags.map((tag) => (
          <Badge key={tag} variant="secondary" className="text-xs gap-1 pr-1">
            {tag}
            <button type="button" onClick={() => remove(tag)} className="hover:text-destructive">
              <X className="w-3 h-3" />
            </button>
          </Badge>
        ))}
      </div>
      <div className="flex gap-1">
        <Input
          className="flex-1 text-xs h-7"
          placeholder={placeholder || 'Add...'}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              add(input)
            }
          }}
          onBlur={() => add(input)}
        />
        {suggestions && suggestions.length > 0 && input.length > 0 && (
          <div className="absolute mt-8 bg-card border border-border rounded-lg shadow-lg z-20 max-h-32 overflow-y-auto">
            {suggestions
              .filter((s) => s.includes(input) && !tags.includes(s))
              .slice(0, 5)
              .map((s) => (
                <button
                  key={s}
                  type="button"
                  className="block w-full text-left px-3 py-1.5 text-xs hover:bg-muted transition-colors"
                  onMouseDown={(e) => { e.preventDefault(); add(s) }}
                >
                  {s}
                </button>
              ))}
          </div>
        )}
      </div>
    </div>
  )
}


/* ── Agent Property Panel ──────────────────────────────────────────── */

function AgentPropertyPanel({
  agent,
  agents,
  globalTools,
  globalRagSources,
  onUpdate,
  onClose,
}: {
  agent: ProposalAgent
  agents: ProposalAgent[]
  globalTools: ProposalResponse['tools']
  globalRagSources: ProposalResponse['rag_sources']
  onUpdate: (agent: ProposalAgent) => void
  onClose: () => void
}) {
  const set = (partial: Partial<ProposalAgent>) => onUpdate({ ...agent, ...partial })

  return (
    <div className="w-80 shrink-0 border border-border rounded-lg overflow-y-auto bg-card">
      <div className="sticky top-0 bg-card border-b border-border px-4 py-3 flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <Settings2 className="w-4 h-4 text-primary" />
          <span className="text-sm font-semibold">Agent Properties</span>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose}>
          <ChevronLeft className="w-4 h-4" />
        </Button>
      </div>

      <div className="p-4 space-y-4">
        {/* Identity */}
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Agent ID</Label>
            <Input value={agent.agent_id} onChange={(e) => set({ agent_id: e.target.value })} />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Role</Label>
            <Input value={agent.role} onChange={(e) => set({ role: e.target.value })} />
          </div>
        </div>

        <Separator />

        {/* Prompt Template */}
        <div className="space-y-1.5">
          <Label className="text-xs">Prompt Template</Label>
          <Textarea
            value={agent.prompt_template.template_string}
            onChange={(e) =>
              onUpdate({ ...agent, prompt_template: { ...agent.prompt_template, template_string: e.target.value } })
            }
            rows={4}
          />
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Input Variables</Label>
          <TagInput
            tags={agent.prompt_template.input_variables}
            onChange={(vars) => onUpdate({ ...agent, prompt_template: { ...agent.prompt_template, input_variables: vars } })}
            placeholder="e.g. input, task, context"
          />
        </div>

        <Separator />

        {/* LLM */}
        <div className="space-y-1.5">
          <Label className="text-xs">LLM Provider</Label>
          <Select
            value={agent.llm.provider}
            onValueChange={(v) => onUpdate({ ...agent, llm: { ...agent.llm, provider: v } })}
          >
            <SelectTrigger><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="openai">OpenAI</SelectItem>
              <SelectItem value="anthropic">Anthropic</SelectItem>
              <SelectItem value="azure">Azure OpenAI</SelectItem>
              <SelectItem value="google">Google Gemini</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Model</Label>
            <Input
              value={agent.llm.model_name}
              onChange={(e) => onUpdate({ ...agent, llm: { ...agent.llm, model_name: e.target.value } })}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Temperature</Label>
            <Input
              type="number" min={0} max={2} step={0.1}
              value={agent.llm.temperature}
              onChange={(e) => onUpdate({ ...agent, llm: { ...agent.llm, temperature: parseFloat(e.target.value) || 0 } })}
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Max Tokens</Label>
            <Input
              type="number" min={1} step={1}
              value={agent.llm.max_tokens}
              onChange={(e) => onUpdate({ ...agent, llm: { ...agent.llm, max_tokens: parseInt(e.target.value) || 4096 } })}
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">API Key Env Var</Label>
            <Input
              value={agent.llm.api_key_env_var}
              onChange={(e) => onUpdate({ ...agent, llm: { ...agent.llm, api_key_env_var: e.target.value } })}
              placeholder="OPENAI_API_KEY"
            />
          </div>
        </div>

        <Separator />

        {/* Routing */}
        <div className="flex items-center justify-between">
          <Label className="text-xs cursor-pointer">Agent-driven routing (autonomous)</Label>
          <Switch
            checked={agent.topology?.orchestration_mode === 'agent_driven'}
            onCheckedChange={(checked) =>
              set({ topology: { orchestration_mode: checked ? 'agent_driven' : 'model_driven' } })
            }
          />
        </div>

        <Separator />

        {/* Consensus */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <Label className="text-xs cursor-pointer">Consensus voting</Label>
            <Switch
              checked={agent.consensus_config?.enabled ?? false}
              onCheckedChange={(enabled) =>
                set({ consensus_config: { enabled, instances: agent.consensus_config?.instances ?? 3, threshold: agent.consensus_config?.threshold ?? 0.7 } })
              }
            />
          </div>
          {agent.consensus_config?.enabled && (
            <div className="space-y-3 pl-2 border-l-2 border-primary/30">
              <div className="space-y-1.5">
                <Label className="text-xs">Number of Instances</Label>
                <Input
                  type="number" min={1} max={10} step={1}
                  value={agent.consensus_config.instances}
                  onChange={(e) =>
                    set({ consensus_config: { ...agent.consensus_config!, instances: parseInt(e.target.value) || 3 } })
                  }
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Agreement Threshold: {agent.consensus_config.threshold}</Label>
                <Slider
                  value={[agent.consensus_config.threshold]}
                  min={0.5} max={1} step={0.05}
                  onValueChange={([v]) =>
                    set({ consensus_config: { ...agent.consensus_config!, threshold: v } })
                  }
                />
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Sub-Agents */}
        <div className="space-y-1.5">
          <Label className="text-xs">Sub-Agents</Label>
          <TagInput
            tags={agent.sub_agents}
            onChange={(tags) => set({ sub_agents: tags })}
            placeholder="Sub-agent ID"
            suggestions={agents.map((a) => a.agent_id).filter((id) => id !== agent.agent_id)}
          />
        </div>

        <Separator />

        {/* Tools (references) */}
        <div className="space-y-1.5">
          <Label className="text-xs">Tool References</Label>
          <TagInput
            tags={agent.tools}
            onChange={(tags) => set({ tools: tags })}
            placeholder="Tool ID"
            suggestions={globalTools.map((t) => t.tool_id)}
          />
        </div>

        {/* Per-agent Tool Configs */}
        {agent.tools.length > 0 && (
          <div className="space-y-2 pl-2 border-l-2 border-primary/30">
            <Label className="text-xs text-muted-foreground">Per-Agent Tool Overrides</Label>
            {agent.tools.map((toolId) => {
              const tc = agent.tools_config?.find((c) => c.tool_id === toolId)
              const globalTool = globalTools.find((t) => t.tool_id === toolId)
              return (
                <div key={toolId} className="p-2 rounded border border-border space-y-1.5">
                  <Label className="text-xs font-mono">{toolId}</Label>
                  {tc ? (
                    <>
                      <Input
                        className="text-xs h-7"
                        placeholder="Description"
                        value={tc.description}
                        onChange={(e) => {
                          const newConfigs = [...(agent.tools_config || [])]
                          const idx = newConfigs.findIndex((c) => c.tool_id === toolId)
                          newConfigs[idx] = { ...tc, description: e.target.value }
                          set({ tools_config: newConfigs })
                        }}
                      />
                      <Input
                        className="text-xs h-7 font-mono"
                        placeholder='{"endpoint": "..."}'
                        value={JSON.stringify(tc.config)}
                        onChange={(e) => {
                          try {
                            const parsed = JSON.parse(e.target.value)
                            const newConfigs = [...(agent.tools_config || [])]
                            const idx = newConfigs.findIndex((c) => c.tool_id === toolId)
                            newConfigs[idx] = { ...tc, config: parsed }
                            set({ tools_config: newConfigs })
                          } catch { /* allow typing */ }
                        }}
                      />
                    </>
                  ) : (
                    <Button
                      variant="outline" size="sm" className="w-full text-xs h-7"
                      onClick={() => {
                        const defaultConfig = globalTool?.config || {}
                        set({
                          tools_config: [
                            ...(agent.tools_config || []),
                            { tool_id: toolId, name: toolId, description: globalTool?.name || toolId, type: globalTool?.type || 'api', config: defaultConfig },
                          ],
                        })
                      }}
                    >
                      Override Config
                    </Button>
                  )}
                </div>
              )
            })}
          </div>
        )}

        <Separator />

        {/* RAG Sources (references) */}
        <div className="space-y-1.5">
          <Label className="text-xs">RAG Source References</Label>
          <TagInput
            tags={agent.rag_sources}
            onChange={(tags) => set({ rag_sources: tags })}
            placeholder="RAG ID"
            suggestions={globalRagSources.map((r) => r.rag_id)}
          />
        </div>

        {/* Per-agent RAG Configs */}
        {agent.rag_sources.length > 0 && (
          <div className="space-y-2 pl-2 border-l-2 border-primary/30">
            <Label className="text-xs text-muted-foreground">Per-Agent RAG Overrides</Label>
            {agent.rag_sources.map((ragId) => {
              const rc = agent.rag_config?.find((c) => c.rag_id === ragId)
              const globalRag = globalRagSources.find((r) => r.rag_id === ragId)
              return (
                <div key={ragId} className="p-2 rounded border border-border space-y-1.5">
                  <Label className="text-xs font-mono">{ragId}</Label>
                  {rc ? (
                    <>
                      <div className="grid grid-cols-2 gap-1.5">
                        <Input
                          className="text-xs h-7"
                          placeholder="Collection"
                          value={rc.collection_name}
                          onChange={(e) => {
                            const newConfigs = [...(agent.rag_config || [])]
                            const idx = newConfigs.findIndex((c) => c.rag_id === ragId)
                            newConfigs[idx] = { ...rc, collection_name: e.target.value }
                            set({ rag_config: newConfigs })
                          }}
                        />
                        <Input
                          className="text-xs h-7"
                          placeholder="Provider"
                          value={rc.provider}
                          onChange={(e) => {
                            const newConfigs = [...(agent.rag_config || [])]
                            const idx = newConfigs.findIndex((c) => c.rag_id === ragId)
                            newConfigs[idx] = { ...rc, provider: e.target.value }
                            set({ rag_config: newConfigs })
                          }}
                        />
                      </div>
                      <div className="grid grid-cols-3 gap-1.5">
                        <div className="space-y-0.5">
                          <Label className="text-[10px] text-muted-foreground">Model</Label>
                          <Input
                            className="text-xs h-7"
                            value={rc.embedding_model}
                            onChange={(e) => {
                              const newConfigs = [...(agent.rag_config || [])]
                              const idx = newConfigs.findIndex((c) => c.rag_id === ragId)
                              newConfigs[idx] = { ...rc, embedding_model: e.target.value }
                              set({ rag_config: newConfigs })
                            }}
                          />
                        </div>
                        <div className="space-y-0.5">
                          <Label className="text-[10px] text-muted-foreground">Top K</Label>
                          <Input
                            type="number" min={1} max={100}
                            className="text-xs h-7"
                            value={rc.top_k}
                            onChange={(e) => {
                              const newConfigs = [...(agent.rag_config || [])]
                              const idx = newConfigs.findIndex((c) => c.rag_id === ragId)
                              newConfigs[idx] = { ...rc, top_k: parseInt(e.target.value) || 3 }
                              set({ rag_config: newConfigs })
                            }}
                          />
                        </div>
                        <div className="space-y-0.5">
                          <Label className="text-[10px] text-muted-foreground">Threshold</Label>
                          <Input
                            type="number" min={0} max={1} step={0.05}
                            className="text-xs h-7"
                            value={rc.similarity_threshold}
                            onChange={(e) => {
                              const newConfigs = [...(agent.rag_config || [])]
                              const idx = newConfigs.findIndex((c) => c.rag_id === ragId)
                              newConfigs[idx] = { ...rc, similarity_threshold: parseFloat(e.target.value) || 0.7 }
                              set({ rag_config: newConfigs })
                            }}
                          />
                        </div>
                      </div>
                    </>
                  ) : (
                    <Button
                      variant="outline" size="sm" className="w-full text-xs h-7"
                      onClick={() => {
                        const defaults = globalRag || { provider: 'qdrant', collection_name: ragId, embedding_model: 'text-embedding-3-small', top_k: 3, similarity_threshold: 0.7 }
                        set({
                          rag_config: [
                            ...(agent.rag_config || []),
                            { rag_id: ragId, ...defaults },
                          ],
                        })
                      }}
                    >
                      Override Config
                    </Button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}

'use client'

import { useState } from 'react'
import {
  Settings2,
  Wrench,
  Database,
  Plus,
  Trash2,
  FileCode,
  Layout,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { ProposalCanvas } from '@/components/workflow-proposal-canvas'
import type { ProposalResponse } from '@/lib/types'

interface WorkflowBuilderProps {
  value: string
  onChange: (json: string) => void
  onStatusChange: (changed: boolean) => void
}

export function WorkflowBuilder({ value, onChange, onStatusChange }: WorkflowBuilderProps) {
  const [tab, setTab] = useState<'visual' | 'json'>('visual')

  let proposal: ProposalResponse
  let parseError: string | null = null
  try {
    proposal = JSON.parse(value)
  } catch {
    proposal = {
      workflow_id: '',
      name: '',
      description: '',
      entry_point: '',
      agents: [],
      edges: [],
      tools: [],
      rag_sources: [],
    }
    parseError = 'Invalid JSON'
  }

  const update = (updated: ProposalResponse) => {
    onChange(JSON.stringify(updated, null, 2))
    onStatusChange(true)
  }

  return (
    <div className="space-y-4">
      <Tabs value={tab} onValueChange={(v) => setTab(v as 'visual' | 'json')}>
        <TabsList className="grid w-[200px] grid-cols-2">
          <TabsTrigger value="visual" className="gap-1.5">
            <Layout className="w-3.5 h-3.5" /> Visual
          </TabsTrigger>
          <TabsTrigger value="json" className="gap-1.5">
            <FileCode className="w-3.5 h-3.5" /> JSON
          </TabsTrigger>
        </TabsList>

        <TabsContent value="visual" className="mt-4 space-y-4">
          {parseError && (
            <div className="text-sm text-destructive bg-destructive/10 rounded-lg p-3">
              {parseError} — switch to JSON tab to fix
            </div>
          )}

          <ProposalCanvas proposal={proposal} onUpdate={update} />

          <div className="space-y-4">
            <MetadataSection proposal={proposal} onUpdate={update} />

            <ToolsSection
              tools={proposal.tools}
              onUpdate={(tools) => update({ ...proposal, tools })}
            />

            <RagSection
              ragSources={proposal.rag_sources}
              onUpdate={(rag_sources) => update({ ...proposal, rag_sources })}
            />
          </div>
        </TabsContent>

        <TabsContent value="json" className="mt-4">
          <textarea
            value={value}
            onChange={(e) => {
              onChange(e.target.value)
              onStatusChange(true)
            }}
            className="w-full h-72 font-mono text-xs bg-muted border border-border rounded-lg p-3 resize-none focus:outline-none focus:ring-1 focus:ring-primary"
            spellCheck={false}
          />
        </TabsContent>
      </Tabs>
    </div>
  )
}

function MetadataSection({
  proposal,
  onUpdate,
}: {
  proposal: ProposalResponse
  onUpdate: (p: ProposalResponse) => void
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm flex items-center gap-2">
          <Settings2 className="w-4 h-4 text-primary" /> Workflow Settings
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label className="text-xs">Name</Label>
            <Input
              value={proposal.name}
              onChange={(e) => onUpdate({ ...proposal, name: e.target.value })}
              placeholder="Workflow name"
            />
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Entry Point Agent</Label>
            <Select
              value={proposal.entry_point}
              onValueChange={(v) => onUpdate({ ...proposal, entry_point: v })}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select agent" />
              </SelectTrigger>
              <SelectContent>
                {proposal.agents.map((a) => (
                  <SelectItem key={a.agent_id} value={a.agent_id}>
                    {a.role} ({a.agent_id})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">Description</Label>
          <Textarea
            value={proposal.description}
            onChange={(e) => onUpdate({ ...proposal, description: e.target.value })}
            placeholder="Workflow description"
            rows={2}
          />
        </div>
      </CardContent>
    </Card>
  )
}

function ToolsSection({
  tools,
  onUpdate,
}: {
  tools: ProposalResponse['tools']
  onUpdate: (tools: ProposalResponse['tools']) => void
}) {
  const addTool = () => {
    onUpdate([
      ...tools,
      { tool_id: `tool_${tools.length + 1}`, name: '', description: '', type: 'api', config: {} },
    ])
  }

  const updateTool = (index: number, tool: (typeof tools)[number]) => {
    const next = [...tools]
    next[index] = tool
    onUpdate(next)
  }

  const removeTool = (index: number) => {
    onUpdate(tools.filter((_, i) => i !== index))
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <Wrench className="w-4 h-4 text-primary" /> Tools ({tools.length})
        </CardTitle>
        <Button variant="outline" size="sm" onClick={addTool} className="gap-1">
          <Plus className="w-3.5 h-3.5" /> Add Tool
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        {tools.length === 0 && (
          <p className="text-sm text-muted-foreground">No tools configured.</p>
        )}
        {tools.map((tool, i) => (
          <div key={i} className="flex items-center gap-2 p-2 rounded-lg border border-border">
            <Input
              className="w-[120px] text-xs"
              placeholder="ID"
              value={tool.tool_id}
              onChange={(e) => updateTool(i, { ...tool, tool_id: e.target.value })}
            />
            <Input
              className="flex-1 text-xs"
              placeholder="Name"
              value={tool.name}
              onChange={(e) => updateTool(i, { ...tool, name: e.target.value })}
            />
            <Select value={tool.type} onValueChange={(v) => updateTool(i, { ...tool, type: v })}>
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="api">API</SelectItem>
                <SelectItem value="mcp">MCP</SelectItem>
                <SelectItem value="function">Function</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" onClick={() => removeTool(i)}>
              <Trash2 className="w-3.5 h-3.5 text-destructive" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

function RagSection({
  ragSources,
  onUpdate,
}: {
  ragSources: ProposalResponse['rag_sources']
  onUpdate: (ragSources: ProposalResponse['rag_sources']) => void
}) {
  const addRag = () => {
    onUpdate([
      ...ragSources,
      { rag_id: `rag_${ragSources.length + 1}`, provider: 'qdrant', collection_name: '', embedding_model: 'text-embedding-3-small', top_k: 3, similarity_threshold: 0.7 },
    ])
  }

  const updateRag = (index: number, rag: (typeof ragSources)[number]) => {
    const next = [...ragSources]
    next[index] = rag
    onUpdate(next)
  }

  const removeRag = (index: number) => {
    onUpdate(ragSources.filter((_, i) => i !== index))
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle className="text-sm flex items-center gap-2">
          <Database className="w-4 h-4 text-primary" /> RAG Sources ({ragSources.length})
        </CardTitle>
        <Button variant="outline" size="sm" onClick={addRag} className="gap-1">
          <Plus className="w-3.5 h-3.5" /> Add Source
        </Button>
      </CardHeader>
      <CardContent className="space-y-2">
        {ragSources.length === 0 && (
          <p className="text-sm text-muted-foreground">No RAG sources configured.</p>
        )}
        {ragSources.map((rag, i) => (
          <div key={i} className="flex items-center gap-2 p-2 rounded-lg border border-border">
            <Input
              className="w-[100px] text-xs"
              placeholder="ID"
              value={rag.rag_id}
              onChange={(e) => updateRag(i, { ...rag, rag_id: e.target.value })}
            />
            <Input
              className="flex-1 text-xs"
              placeholder="Collection name"
              value={rag.collection_name}
              onChange={(e) => updateRag(i, { ...rag, collection_name: e.target.value })}
            />
            <Select value={rag.provider} onValueChange={(v) => updateRag(i, { ...rag, provider: v })}>
              <SelectTrigger className="w-[100px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="qdrant">Qdrant</SelectItem>
                <SelectItem value="pinecone">Pinecone</SelectItem>
                <SelectItem value="chroma">Chroma</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="ghost" size="sm" onClick={() => removeRag(i)}>
              <Trash2 className="w-3.5 h-3.5 text-destructive" />
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  )
}

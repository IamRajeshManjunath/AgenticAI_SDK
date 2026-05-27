'use client'

import { useCallback, useMemo, useEffect, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  Edge,
  Node,
  BackgroundVariant,
  MarkerType,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Plus,
  Play,
  Download,
  Upload,
  Settings2,
  Layers,
  Save,
  AlertCircle,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkflowStore } from '@/lib/store'
import { useAuthStore } from '@/lib/auth-store'
import { workflowApi } from '@/lib/api'
import { AgentNode } from './agent-node'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { AgentNodeConfig, EdgeCondition } from '@/lib/types'

const nodeTypes = {
  agent: AgentNode,
}

interface WorkflowCanvasProps {
  workflowId: string
  onNodeSelect: (nodeId: string | null) => void
  onEdgeSelect: (edgeId: string | null) => void
  selectedEdgeId: string | null
}

export function WorkflowCanvas({
  workflowId,
  onNodeSelect,
  onEdgeSelect,
  selectedEdgeId,
}: WorkflowCanvasProps) {
  const {
    workflows,
    selectedNodeId,
    addAgent,
    addEdge: addWorkflowEdge,
    updateEdge,
    deleteAgent,
    deleteEdge,
    updateWorkflow,
    exportWorkflow,
    importWorkflow,
  } = useWorkflowStore()

  const workflow = workflows[workflowId]
  const [jsonDialogOpen, setJsonDialogOpen] = useState(false)
  const [jsonMode, setJsonMode] = useState<'import' | 'export'>('export')
  const [jsonText, setJsonText] = useState('')
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [runDialogOpen, setRunDialogOpen] = useState(false)
  const [runInput, setRunInput] = useState('')
  const [isRunning, setIsRunning] = useState(false)
  const [editingName, setEditingName] = useState(false)
  const [editingDescription, setEditingDescription] = useState(false)
  const [nameDraft, setNameDraft] = useState('')
  const [descDraft, setDescDraft] = useState('')
  const { toast } = useToast()

  // Convert workflow data to React Flow nodes
  const initialNodes: Node[] = useMemo(() => {
    if (!workflow) return []
    
    return workflow.agents.map((agent, index) => ({
      id: agent.agent_id,
      type: 'agent',
      position: { x: 100 + (index % 3) * 350, y: 100 + Math.floor(index / 3) * 200 },
      data: {
        ...agent,
        isEntryPoint: agent.agent_id === workflow.entry_point,
      },
    }))
  }, [workflow])

  // Convert workflow edges to React Flow edges
  const initialEdges: Edge[] = useMemo(() => {
    if (!workflow) return []
    
    return workflow.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: 'smoothstep',
      animated: true,
      label: edge.condition ? 'Conditional' : undefined,
      labelStyle: { fill: 'var(--muted-foreground)', fontSize: 10 },
      labelBgStyle: { fill: 'var(--card)', fillOpacity: 0.8 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: 'var(--primary)',
      },
      style: {
        stroke: 'var(--primary)',
        strokeWidth: 2,
      },
      data: edge,
    }))
  }, [workflow])

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges)

  // Sync nodes when workflow changes
  useEffect(() => {
    setNodes(initialNodes)
  }, [initialNodes, setNodes])

  useEffect(() => {
    setEdges(initialEdges)
  }, [initialEdges, setEdges])

  // Handle connection (edge creation)
  const onConnect = useCallback(
    (params: Connection) => {
      if (!params.source || !params.target) return
      
      addWorkflowEdge(workflowId, {
        source: params.source,
        target: params.target,
      })
    },
    [workflowId, addWorkflowEdge]
  )

  // Handle node selection
  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => {
      onNodeSelect(node.id)
    },
    [onNodeSelect]
  )

  // Handle edge selection
  const onEdgeClick = useCallback(
    (_: React.MouseEvent, edge: Edge) => {
      onEdgeSelect(edge.id)
    },
    [onEdgeSelect]
  )

  // Handle pane click (deselect)
  const onPaneClick = useCallback(() => {
    onNodeSelect(null)
    onEdgeSelect(null)
  }, [onNodeSelect, onEdgeSelect])

  // Handle node deletion
  const onNodesDelete = useCallback(
    (nodesToDelete: Node[]) => {
      nodesToDelete.forEach((node) => {
        deleteAgent(workflowId, node.id)
      })
    },
    [workflowId, deleteAgent]
  )

  // Handle edge deletion
  const onEdgesDelete = useCallback(
    (edgesToDelete: Edge[]) => {
      edgesToDelete.forEach((edge) => {
        deleteEdge(workflowId, edge.id)
      })
    },
    [workflowId, deleteEdge]
  )

  // Add new agent
  const handleAddAgent = useCallback(() => {
    addAgent(workflowId)
  }, [workflowId, addAgent])

  // Validate workflow
  const validateWorkflow = useCallback(() => {
    const errors: string[] = []
    
    if (!workflow) {
      errors.push('Workflow not found')
      return errors
    }

    if (!workflow.entry_point) {
      errors.push('Entry point is required')
    } else if (!workflow.agents.find((a) => a.agent_id === workflow.entry_point)) {
      errors.push('Entry point agent not found')
    }

    workflow.agents.forEach((agent) => {
      if (!agent.agent_id) {
        errors.push('Agent ID is required for all agents')
      }
      if (!agent.role) {
        errors.push(`Role is required for agent: ${agent.agent_id}`)
      }
    })

    return errors
  }, [workflow])

  // Handle export
  const handleExport = useCallback(() => {
    const json = exportWorkflow(workflowId)
    if (json) {
      setJsonText(json)
      setJsonMode('export')
      setJsonDialogOpen(true)
    }
  }, [workflowId, exportWorkflow])

  // Handle import dialog open
  const handleImportOpen = useCallback(() => {
    setJsonText('')
    setJsonMode('import')
    setJsonDialogOpen(true)
  }, [])

  // Handle import
  const handleImport = useCallback(() => {
    const id = importWorkflow(jsonText)
    if (id) {
      setJsonDialogOpen(false)
    }
  }, [jsonText, importWorkflow])

  // Handle run
  const handleRunOpen = useCallback(() => {
    const errors = validateWorkflow()
    setValidationErrors(errors)
    if (errors.length > 0) {
      toast({ title: 'Validation Errors', description: errors.join(', '), variant: 'destructive' })
      return
    }
    setRunInput('')
    setRunDialogOpen(true)
  }, [workflowId, validateWorkflow, toast])

  const handleRunExecute = useCallback(async () => {
    if (!runInput.trim()) {
      toast({ title: 'Input Required', description: 'Enter an input message for the workflow', variant: 'destructive' })
      return
    }
    setIsRunning(true)
    try {
      const workflowSchema = useWorkflowStore.getState().workflows[workflowId]
      const result = await workflowApi.run(workflowSchema, runInput)
      if (result.error) {
        toast({ title: 'Run Failed', description: result.error, variant: 'destructive' })
      } else {
        toast({ title: 'Workflow Started', description: `Execution status: ${result.data?.status}` })
        setRunDialogOpen(false)
      }
    } catch (err) {
      toast({ title: 'Run Failed', description: String(err), variant: 'destructive' })
    } finally {
      setIsRunning(false)
    }
  }, [workflowId, runInput, toast])

  const selectedEdge = useMemo(() => {
    if (!selectedEdgeId) return null
    return workflow.edges.find((e) => e.id === selectedEdgeId)
  }, [selectedEdgeId, workflow.edges])

  return (
    <div className="w-full h-full relative">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onEdgeClick={onEdgeClick}
        onPaneClick={onPaneClick}
        onNodesDelete={onNodesDelete}
        onEdgesDelete={onEdgesDelete}
        nodeTypes={nodeTypes}
        fitView
        proOptions={{ hideAttribution: true }}
        className="bg-background"
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="var(--border)"
        />
        <Controls className="!bg-card !border-border !rounded-lg" />
        <MiniMap
          className="!bg-card !border-border !rounded-lg"
          nodeColor="var(--primary)"
          maskColor="var(--background)"
        />

        {/* Top Panel */}
        <Panel position="top-left" className="flex items-center gap-2">
          <div className="glass-card px-4 py-2 rounded-lg min-w-[200px]">
            {editingName ? (
              <Input
                autoFocus
                value={nameDraft}
                onChange={(e) => setNameDraft(e.target.value)}
                onBlur={() => {
                  if (nameDraft.trim() && nameDraft !== workflow.name) {
                    updateWorkflow(workflowId, { name: nameDraft.trim() })
                  }
                  setEditingName(false)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    if (nameDraft.trim() && nameDraft !== workflow.name) {
                      updateWorkflow(workflowId, { name: nameDraft.trim() })
                    }
                    setEditingName(false)
                  }
                  if (e.key === 'Escape') setEditingName(false)
                }}
                className="h-7 text-lg font-semibold px-0 border-0 bg-transparent focus-visible:ring-0"
              />
            ) : (
              <h2
                className="text-lg font-semibold cursor-text hover:text-primary transition-colors"
                onDoubleClick={() => {
                  setNameDraft(workflow.name)
                  setEditingName(true)
                }}
                title="Double-click to rename"
              >
                {workflow.name}
              </h2>
            )}
            {editingDescription ? (
              <Input
                autoFocus
                value={descDraft}
                onChange={(e) => setDescDraft(e.target.value)}
                onBlur={() => {
                  if (descDraft !== workflow.description) {
                    updateWorkflow(workflowId, { description: descDraft })
                  }
                  setEditingDescription(false)
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    if (descDraft !== workflow.description) {
                      updateWorkflow(workflowId, { description: descDraft })
                    }
                    setEditingDescription(false)
                  }
                  if (e.key === 'Escape') setEditingDescription(false)
                }}
                className="h-6 text-xs px-0 border-0 bg-transparent focus-visible:ring-0"
                placeholder="Add a description..."
              />
            ) : (
              <p
                className="text-xs text-muted-foreground cursor-text hover:text-foreground transition-colors"
                onDoubleClick={() => {
                  setDescDraft(workflow.description || '')
                  setEditingDescription(true)
                }}
                title="Double-click to edit description"
              >
                {workflow.description || `${workflow.agents.length} agents | ${workflow.edges.length} edges`}
              </p>
            )}
          </div>
        </Panel>

        {/* Action Panel */}
        <Panel position="top-right" className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleAddAgent}
            className="gap-2"
          >
            <Plus className="w-4 h-4" />
            Add Agent
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleImportOpen}
            className="gap-2"
          >
            <Upload className="w-4 h-4" />
            Import
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="gap-2"
          >
            <Download className="w-4 h-4" />
            Export
          </Button>
          <Button
            size="sm"
            onClick={handleRunOpen}
            className="gap-2 glow-primary-sm"
          >
            <Play className="w-4 h-4" />
            Run Workflow
          </Button>
        </Panel>

        {/* Validation Errors */}
        <AnimatePresence>
          {validationErrors.length > 0 && (
            <Panel position="bottom-center">
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 20 }}
                className="glass-card p-4 rounded-lg border-destructive/50 max-w-md"
              >
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-5 h-5 text-destructive shrink-0" />
                  <div>
                    <p className="font-medium text-destructive">Validation Errors</p>
                    <ul className="mt-2 space-y-1 text-sm text-muted-foreground">
                      {validationErrors.map((error, i) => (
                        <li key={i}>• {error}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              </motion.div>
            </Panel>
          )}
        </AnimatePresence>
      </ReactFlow>

      {/* JSON Import/Export Dialog */}
      <Dialog open={jsonDialogOpen} onOpenChange={setJsonDialogOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              {jsonMode === 'export' ? 'Export Workflow JSON' : 'Import Workflow JSON'}
            </DialogTitle>
            <DialogDescription>
              {jsonMode === 'export'
                ? 'Copy the JSON below to save your workflow configuration'
                : 'Paste a valid workflow JSON schema to import'}
            </DialogDescription>
          </DialogHeader>
          <Textarea
            value={jsonText}
            onChange={(e) => setJsonText(e.target.value)}
            placeholder={jsonMode === 'import' ? 'Paste workflow JSON here...' : ''}
            className="font-mono text-sm h-96 resize-none"
            readOnly={jsonMode === 'export'}
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setJsonDialogOpen(false)}>
              Cancel
            </Button>
            {jsonMode === 'export' ? (
              <Button
                onClick={() => {
                  navigator.clipboard.writeText(jsonText)
                  setJsonDialogOpen(false)
                }}
              >
                Copy to Clipboard
              </Button>
            ) : (
              <Button onClick={handleImport}>Import Workflow</Button>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Run Dialog */}
      <Dialog open={runDialogOpen} onOpenChange={setRunDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Run Workflow</DialogTitle>
            <DialogDescription>
              Enter an input message to start the workflow execution.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Input Message</Label>
              <Textarea
                value={runInput}
                onChange={(e) => setRunInput(e.target.value)}
                placeholder="Enter your input for the workflow..."
                className="min-h-[100px]"
                disabled={isRunning}
              />
            </div>
          </div>
          <div className="flex justify-end gap-3">
            <Button variant="outline" onClick={() => setRunDialogOpen(false)} disabled={isRunning}>
              Cancel
            </Button>
            <Button onClick={handleRunExecute} disabled={isRunning || !runInput.trim()}>
              {isRunning ? 'Running...' : 'Run'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Edge Condition Dialog */}
      <Dialog open={!!selectedEdgeId} onOpenChange={(open) => !open && onEdgeSelect(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Edge Condition</DialogTitle>
            <DialogDescription>
              Define Python logic for this transition.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Condition (Python Expression)</label>
              <Textarea
                value={selectedEdge?.condition || ''}
                onChange={(e) => {
                  updateEdge(workflowId, selectedEdgeId!, { condition: e.target.value })
                }}
                placeholder='state["last_message"].content.lower() == "yes"'
                className="font-mono text-sm h-32"
              />
              <p className="text-xs text-muted-foreground">
                Leave empty for unconditional transition.
              </p>
            </div>
          </div>
          <div className="flex justify-end">
            <Button onClick={() => onEdgeSelect(null)}>Done</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  )
}

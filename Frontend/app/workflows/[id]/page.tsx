'use client'

import { useCallback, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Activity, Key, Loader2, CheckCircle2, Info } from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { WorkflowCanvas } from '@/components/workflow/workflow-canvas'
import { AgentConfigSidebar } from '@/components/workflow/agent-config-sidebar'
import { RegistryDrawer } from '@/components/workflow/registry-drawer'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog'
import { useToast } from '@/hooks/use-toast'
import { authApi } from '@/lib/api'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

export default function WorkflowBuilderPage() {
  const params = useParams()
  const router = useRouter()
  const { toast } = useToast()
  const workflowId = params.id as string

  const { workflows, selectedNodeId, selectedEdgeId, setSelectedNode, setSelectedEdge } =
    useWorkflowStore()
  const workflow = workflows[workflowId]

  const [keyDialogOpen, setKeyDialogOpen] = useState(false)
  const [generatedKey, setGeneratedKey] = useState('')
  const [generating, setGenerating] = useState(false)

  const handleGenerateKey = async () => {
    setGenerating(true)
    try {
      const res = await authApi.createWorkflowApiKey(workflowId)
      if (res.error) throw new Error(res.error)
      setGeneratedKey(res.data?.key || '')
      toast({ title: 'Key Generated', description: 'Workflow-scoped API key created' })
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to generate key', variant: 'destructive' })
    } finally {
      setGenerating(false)
    }
  }

  const handleCopyKey = () => {
    navigator.clipboard.writeText(generatedKey)
    toast({ title: 'Copied', description: 'API key copied to clipboard' })
  }

  const handleNodeSelect = useCallback(
    (nodeId: string | null) => {
      setSelectedNode(nodeId)
    },
    [setSelectedNode]
  )

  const handleEdgeSelect = useCallback(
    (edgeId: string | null) => {
      setSelectedEdge(edgeId)
    },
    [setSelectedEdge]
  )

  const handleCloseConfig = useCallback(() => {
    setSelectedNode(null)
  }, [setSelectedNode])

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
              <Link href="/">
                <ArrowLeft className="w-4 h-4" />
                Back
              </Link>
            </Button>
            <div className="h-6 w-px bg-border" />
            <div>
              <h1 className="text-sm font-semibold">{workflow.name}</h1>
              <p className="text-xs text-muted-foreground">
                {workflow.agents.length} agents
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setGeneratedKey('')
                setKeyDialogOpen(true)
              }}
              className="gap-2"
            >
              <Key className="w-4 h-4" />
              API Key
            </Button>
            <Button variant="outline" size="sm" asChild className="gap-2">
              <Link href={`/observability/${workflowId}`}>
                <Activity className="w-4 h-4" />
                Observability
              </Link>
            </Button>
          </div>
        </div>

        <Dialog open={keyDialogOpen} onOpenChange={setKeyDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Workflow API Key</DialogTitle>
              <DialogDescription>
                Generate a workflow-scoped API key (wfk_) for programmatic access to this workflow.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4">
              {generatedKey ? (
                <div className="space-y-3">
                  <div className="p-3 rounded-lg bg-secondary/50 border border-border">
                    <p className="text-xs font-mono break-all select-all">{generatedKey}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button onClick={handleCopyKey} className="flex-1 gap-2">
                      <CheckCircle2 className="w-4 h-4" />
                      Copy Key
                    </Button>
                    <Button variant="outline" onClick={handleGenerateKey} disabled={generating} className="gap-2">
                      {generating && <Loader2 className="w-4 h-4 animate-spin" />}
                      Regenerate
                    </Button>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Make sure to copy this key now. You won't be able to see it again.
                  </p>
                  <div className="pt-3 border-t space-y-2">
                    <p className="text-xs font-medium text-muted-foreground">Usage examples</p>
                    <pre className="bg-muted p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap break-all">
curl -H "X-API-Key: {generatedKey}" \<br/>  {API_BASE_URL}/workflow/workflows/{workflowId}/run</pre>
                    <pre className="bg-muted p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap break-all">
curl -H "X-API-Key: {generatedKey}" \<br/>  {API_BASE_URL}/observability/traces?workflow_id={workflowId}</pre>
                    <p className="text-xs text-muted-foreground flex items-start gap-1">
                      <Info className="w-3 h-3 mt-0.5 shrink-0" />
                      API keys cannot be used for admin operations (IAM, members, billing, etc.) — use JWT Bearer auth for those.
                    </p>
                  </div>
                </div>
              ) : (
                <Button onClick={handleGenerateKey} disabled={generating} className="w-full gap-2">
                  {generating ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Key className="w-4 h-4" />
                  )}
                  {generating ? 'Generating...' : 'Generate New Key'}
                </Button>
              )}
            </div>
          </DialogContent>
        </Dialog>

        {/* Canvas Area */}
        <div
          className={cn(
            'flex-1 relative transition-all duration-300',
            selectedNodeId ? 'mr-[420px]' : 'mr-0'
          )}
        >
          <WorkflowCanvas
            workflowId={workflowId}
            onNodeSelect={handleNodeSelect}
            onEdgeSelect={handleEdgeSelect}
            selectedEdgeId={selectedEdgeId}
          />
          <RegistryDrawer />
        </div>

        {/* Config Sidebar */}
        {selectedNodeId && (
          <AgentConfigSidebar
            workflowId={workflowId}
            agentId={selectedNodeId}
            onClose={handleCloseConfig}
          />
        )}
      </div>
    </DashboardLayout>
  )
}

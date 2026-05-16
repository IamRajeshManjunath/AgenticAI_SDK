'use client'

import { useCallback, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Activity, Settings2 } from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { WorkflowCanvas } from '@/components/workflow/workflow-canvas'
import { AgentConfigSidebar } from '@/components/workflow/agent-config-sidebar'
import { RegistryDrawer } from '@/components/workflow/registry-drawer'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

export default function WorkflowBuilderPage() {
  const params = useParams()
  const router = useRouter()
  const workflowId = params.id as string

  const { workflows, selectedNodeId, selectedEdgeId, setSelectedNode, setSelectedEdge } =
    useWorkflowStore()
  const workflow = workflows[workflowId]

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
            <Button variant="outline" size="sm" asChild className="gap-2">
              <Link href={`/observability/${workflowId}`}>
                <Activity className="w-4 h-4" />
                Observability
              </Link>
            </Button>
          </div>
        </div>

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

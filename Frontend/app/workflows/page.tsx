'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import useSWR from 'swr'
import { ArrowRight, Plus, Workflow } from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'
import { normalizeWorkflowConfig } from '@/lib/workflow-adapters'
import { useWorkflowStore } from '@/lib/store'

export default function WorkflowsPage() {
  const router = useRouter()
  const localWorkflows = useWorkflowStore((state) => state.workflows)
  const createWorkflow = useWorkflowStore((state) => state.createWorkflow)
  const setActiveWorkflow = useWorkflowStore((state) => state.setActiveWorkflow)
  const { data: savedWorkflows, error, isLoading } = useSWR('saved-workflows', async () => {
    const response = await api.crud.getWorkflows()
    if (response.error) throw new Error(response.error)
    const workflows = response.data ?? []
    const normalized = workflows
      .map((workflow) => normalizeWorkflowConfig(workflow.config, workflow.id))
      .filter((workflow) => workflow !== null)

    useWorkflowStore.setState((state) => ({
      workflows: {
        ...state.workflows,
        ...Object.fromEntries(normalized.map((workflow) => [workflow.id, workflow])),
      },
    }))
    return workflows
  })
  const savedIds = new Set((savedWorkflows ?? []).map((workflow) => workflow.id))
  const drafts = Object.values(localWorkflows).filter((workflow) => !savedIds.has(workflow.id))
  const createNewWorkflow = () => {
    const id = createWorkflow(`Workflow ${Object.keys(localWorkflows).length + 1}`)
    setActiveWorkflow(id)
    router.push(`/workflows/${id}`)
  }

  return (
    <DashboardLayout>
      <div className="mx-auto max-w-7xl space-y-6 p-4 md:p-8">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium text-primary">Build and manage</p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">Workflows</h1>
            <p className="mt-2 text-sm text-muted-foreground">
              Saved workflows are shared with your active workspace. Local drafts stay in this browser until saved.
            </p>
          </div>
          <Button onClick={createNewWorkflow} className="gap-2 self-start sm:self-auto">
            <Plus className="h-4 w-4" />
            New workflow
          </Button>
        </div>

        {error && (
          <div role="alert" className="rounded-lg border border-destructive/30 bg-destructive/5 px-4 py-3 text-sm text-destructive">
            Saved workflows could not be loaded: {error.message}
          </div>
        )}

        {isLoading ? (
          <Card>
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              Loading workflows…
            </CardContent>
          </Card>
        ) : savedWorkflows?.length === 0 && drafts.length === 0 ? (
          <Card>
            <CardContent className="flex flex-col items-center p-12 text-center">
              <div className="mb-4 rounded-full bg-primary/10 p-4 text-primary">
                <Workflow className="h-7 w-7" />
              </div>
              <h2 className="text-lg font-semibold">No workflows yet</h2>
              <p className="mt-2 max-w-md text-sm text-muted-foreground">
                Create a workflow to configure agents, tools, schemas, and execution paths.
              </p>
              <Button onClick={createNewWorkflow} className="mt-5 gap-2">
                <Plus className="h-4 w-4" />
                Create your first workflow
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {savedWorkflows?.map((workflow) => {
              const normalized = normalizeWorkflowConfig(workflow.config, workflow.id)
              return (
                <Link
                  key={workflow.id}
                  href={`/workflows/${workflow.id}`}
                  onClick={() => setActiveWorkflow(workflow.id)}
                  className="group"
                >
                  <Card className="h-full transition-colors group-hover:border-primary/50">
                    <CardHeader className="flex-row items-start justify-between space-y-0">
                      <div className="rounded-lg bg-primary/10 p-2 text-primary">
                        <Workflow className="h-5 w-5" />
                      </div>
                      <Badge variant="secondary">Saved</Badge>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      <CardTitle className="text-base">{workflow.name}</CardTitle>
                      <CardDescription className="line-clamp-2 min-h-10">
                        {workflow.description || 'No description provided.'}
                      </CardDescription>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{normalized?.agents.length ?? 0} agents</span>
                        <span className="inline-flex items-center gap-1 text-primary">
                          Open editor <ArrowRight className="h-3.5 w-3.5" />
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </Link>
              )
            })}
            {drafts.map((workflow) => (
              <Link
                key={workflow.id}
                href={`/workflows/${workflow.id}`}
                onClick={() => setActiveWorkflow(workflow.id)}
                className="group"
              >
                <Card className="h-full transition-colors group-hover:border-primary/50">
                  <CardHeader className="flex-row items-start justify-between space-y-0">
                    <div className="rounded-lg bg-muted p-2 text-muted-foreground">
                      <Workflow className="h-5 w-5" />
                    </div>
                    <Badge variant="outline">Local draft</Badge>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <CardTitle className="text-base">{workflow.name}</CardTitle>
                    <CardDescription className="line-clamp-2 min-h-10">
                      {workflow.description || 'Save this draft to share it with the active workspace.'}
                    </CardDescription>
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span>{workflow.agents.length} agents</span>
                      <span className="inline-flex items-center gap-1 text-primary">
                        Continue editing <ArrowRight className="h-3.5 w-3.5" />
                      </span>
                    </div>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

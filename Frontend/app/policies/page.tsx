'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Plus,
  Shield,
  Trash2,
  Loader2,
  Eye,
  FileText,
  X,
  XCircle,
  Check,
} from 'lucide-react'
import useSWR, { mutate } from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { useToast } from '@/hooks/use-toast'
import { policyApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { MultiSelect } from '@/components/ui/multi-select'
import type { Policy, PolicyDocument } from '@/lib/types'

interface StatementBuilder {
  Effect: 'Allow' | 'Deny'
  Action: string[]
  Resource: string[]
}

const DEFAULT_STATEMENT: StatementBuilder = {
  Effect: 'Allow',
  Action: ['*'],
  Resource: ['*'],
}

const statementsToDocument = (stmts: StatementBuilder[]): PolicyDocument => ({
  Version: '2025-01-01',
  Statement: stmts.map((s) => ({
    Effect: s.Effect,
    Action: s.Action,
    Resource: s.Resource,
  })),
})

const ACTION_GROUPS = [
  { group: 'Workflow', items: ['workflow:create', 'workflow:read', 'workflow:update', 'workflow:delete', 'workflow:run', 'workflow:export', 'workflow:import'] },
  { group: 'API Keys', items: ['apikey:create', 'apikey:read', 'apikey:update', 'apikey:delete', 'apikey:regenerate'] },
  { group: 'Members', items: ['member:list', 'member:read', 'member:invite', 'member:remove', 'member:update-role'] },
  { group: 'Workspace', items: ['workspace:read', 'workspace:update', 'workspace:delete', 'workspace:transfer'] },
  { group: 'Tools', items: ['tool:create', 'tool:read', 'tool:update', 'tool:delete', 'tool:test'] },
  { group: 'RAG Sources', items: ['rag:create', 'rag:read', 'rag:update', 'rag:delete', 'rag:ingest'] },
  { group: 'Billing', items: ['billing:read', 'billing:checkout', 'billing:portal', 'billing:update', 'billing:cancel'] },
  { group: 'Integrations', items: ['integration:create', 'integration:read', 'integration:update', 'integration:delete', 'integration:connect', 'integration:disconnect'] },
  { group: 'Cron / Schedules', items: ['cron:create', 'cron:read', 'cron:update', 'cron:delete', 'cron:pause', 'cron:resume'] },
  { group: 'Secrets', items: ['secret:create', 'secret:read', 'secret:read-value', 'secret:update', 'secret:delete'] },
  { group: 'Observability', items: ['observability:read', 'observability:export', 'observability:delete'] },
  { group: 'Execution History', items: ['execution:read', 'execution:cancel', 'execution:retry', 'execution:delete'] },
  { group: 'Templates', items: ['template:create', 'template:read', 'template:update', 'template:delete', 'template:use'] },
  { group: 'Notifications', items: ['notification:create', 'notification:read', 'notification:update', 'notification:delete', 'notification:test'] },
  { group: 'Approvals (HITL)', items: ['approval:read', 'approval:approve', 'approval:reject'] },
  { group: 'Audit Logs', items: ['audit:read', 'audit:export', 'audit:delete'] },
  { group: 'Invite Links', items: ['invite:create', 'invite:read', 'invite:revoke'] },
  { group: 'Roles / Policies', items: ['role:create', 'role:read', 'role:update', 'role:delete', 'role:attach', 'role:detach'] },
  { group: 'Tags', items: ['tag:create', 'tag:read', 'tag:update', 'tag:delete', 'tag:assign', 'tag:unassign'] },
  { group: 'Database', items: ['db:read', 'db:connect', 'db:reset'] },
  { group: 'Settings', items: ['settings:read', 'settings:update'] },
  { group: 'Admin', items: ['admin:superuser', 'admin:impersonate', 'admin:audit-all'] },
]

const ALL_ACTION_OPTIONS = ACTION_GROUPS.flatMap((g) =>
  g.items.map((value) => ({ label: value, value, group: g.group }))
)

const RESOURCE_OPTIONS = [
  { label: 'All resources (*)', value: '*', group: 'Wildcard' },
  { label: 'All in workspace (workspace:*)', value: 'workspace:*', group: 'Workspace' },
  { label: 'All in workspace ID (workspace:{id}/*)', value: 'workspace:{id}/*', group: 'Workspace' },
  { label: 'Workflows (workspace:{id}/workflow:*)', value: 'workspace:{id}/workflow:*', group: 'Workflow' },
  { label: 'Tools (workspace:{id}/tool:*)', value: 'workspace:{id}/tool:*', group: 'Tool' },
  { label: 'RAG sources (workspace:{id}/rag:*)', value: 'workspace:{id}/rag:*', group: 'RAG' },
  { label: 'API keys (workspace:{id}/apikey:*)', value: 'workspace:{id}/apikey:*', group: 'API Key' },
  { label: 'Secrets (workspace:{id}/secret:*)', value: 'workspace:{id}/secret:*', group: 'Secret' },
  { label: 'Integrations (workspace:{id}/integration:*)', value: 'workspace:{id}/integration:*', group: 'Integration' },
  { label: 'Cron (workspace:{id}/cron:*)', value: 'workspace:{id}/cron:*', group: 'Cron' },
  { label: 'Templates (workspace:{id}/template:*)', value: 'workspace:{id}/template:*', group: 'Template' },
  { label: 'Executions (workspace:{id}/execution:*)', value: 'workspace:{id}/execution:*', group: 'Execution' },
]

const fetcher = async (): Promise<Policy[]> => {
  const res = await policyApi.list()
  if (res.error) throw new Error(res.error)
  return res.data ?? []
}

export default function PoliciesPage() {
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)

  const { data: policies, error, isLoading } = useSWR<Policy[]>(
    token ? 'policies-list' : null,
    fetcher
  )

  const [addOpen, setAddOpen] = useState(false)
  const [viewOpen, setViewOpen] = useState(false)
  const [viewingPolicy, setViewingPolicy] = useState<Policy | null>(null)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    name: '',
    description: '',
    statements: [{ ...DEFAULT_STATEMENT }] as StatementBuilder[],
  })

  const resetForm = () => setForm({
    name: '',
    description: '',
    statements: [{ Effect: 'Allow' as const, Action: ['*'], Resource: ['*'] }],
  })

  const updateStatement = (index: number, field: keyof StatementBuilder, value: string) => {
    setForm((prev) => {
      const stmts = prev.statements.map((s, i) => (i === index ? { ...s, [field]: value } : s))
      return { ...prev, statements: stmts }
    })
  }

  const addStatement = () => {
    setForm((prev) => ({ ...prev, statements: [...prev.statements, { ...DEFAULT_STATEMENT }] }))
  }

  const removeStatement = (index: number) => {
    setForm((prev) => ({
      ...prev,
      statements: prev.statements.filter((_, i) => i !== index),
    }))
  }

  const handleCreate = async () => {
    if (!form.name) {
      toast({ title: 'Validation error', description: 'Name is required', variant: 'destructive' })
      return
    }
    const policy_document = statementsToDocument(form.statements)
    setSaving(true)
    try {
      const res = await policyApi.create({
        name: form.name,
        description: form.description || undefined,
        policy_document,
      })
      if (res.error) throw new Error(res.error)
      toast({ title: 'Created', description: `Policy "${form.name}" created` })
      setAddOpen(false)
      resetForm()
      mutate('policies-list')
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to create', variant: 'destructive' })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    const res = await policyApi.delete(id)
    if (res.error) {
      toast({ title: 'Error', description: 'Failed to delete policy', variant: 'destructive' })
      return
    }
    toast({ title: 'Deleted', description: 'Policy deleted' })
    mutate('policies-list')
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">IAM Policies</h1>
            <p className="text-muted-foreground mt-1">
              Manage access control policies for workspace resources
            </p>
          </div>
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="w-4 h-4" />
                Create Policy
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
              <DialogHeader>
                <DialogTitle>New Policy</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="workflow-admin-policy"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Description</Label>
                  <Input
                    value={form.description}
                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                    placeholder="Grants admin access to all workflows"
                  />
                </div>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label>Statements</Label>
                    <Button variant="outline" size="sm" onClick={addStatement}>
                      <Plus className="w-3 h-3 mr-1" />
                      Add Statement
                    </Button>
                  </div>
                  {form.statements.map((stmt, i) => (
                    <div key={i} className="p-4 rounded-lg border border-border space-y-3 relative">
                      {form.statements.length > 1 && (
                        <button
                          onClick={() => removeStatement(i)}
                          className="absolute top-2 right-2 text-muted-foreground hover:text-destructive"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                      <div className="flex gap-3 items-start">
                        <div className="w-28 shrink-0 space-y-1">
                          <Label className="text-xs">Effect</Label>
                          <Select
                            value={stmt.Effect}
                            onValueChange={(v) => updateStatement(i, 'Effect', v as 'Allow' | 'Deny')}
                          >
                            <SelectTrigger>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Allow">Allow</SelectItem>
                              <SelectItem value="Deny">Deny</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <div className="flex-1 space-y-1">
                          <Label className="text-xs">Actions</Label>
                          <MultiSelect
                            options={ALL_ACTION_OPTIONS}
                            selected={stmt.Action}
                            onChange={(v) => updateStatement(i, 'Action', v)}
                            placeholder="Select actions..."
                            creatable
                          />
                        </div>
                        <div className="flex-1 space-y-1">
                          <Label className="text-xs">Resources</Label>
                          <MultiSelect
                            options={RESOURCE_OPTIONS}
                            selected={stmt.Resource}
                            onChange={(v) => updateStatement(i, 'Resource', v)}
                            placeholder="Select resources..."
                            creatable
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="text-xs text-muted-foreground">
                  Compiled policy:{' '}
                  <code className="text-primary">
                    {JSON.stringify(statementsToDocument(form.statements)).length > 80
                      ? JSON.stringify(statementsToDocument(form.statements)).slice(0, 80) + '...'
                      : JSON.stringify(statementsToDocument(form.statements))}
                  </code>
                </div>
                <Button onClick={handleCreate} disabled={saving} className="w-full">
                  {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Create Policy
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <Card className="glass-card">
            <CardContent className="py-12 text-center text-muted-foreground">
              <XCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Failed to load policies</p>
            </CardContent>
          </Card>
        ) : !policies?.length ? (
          <Card className="glass-card">
            <CardContent className="py-16 text-center">
              <Shield className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
              <h3 className="text-lg font-medium mb-2">No policies yet</h3>
              <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                Create IAM policies to control access to workflows, tools, and other workspace resources.
              </p>
              <Button onClick={() => setAddOpen(true)} className="gap-2">
                <Plus className="w-4 h-4" />
                Create First Policy
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-5 h-5" />
                Access Policies
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {policies.map((policy) => (
                    <TableRow key={policy.id}>
                      <TableCell className="font-medium font-mono text-sm">{policy.name}</TableCell>
                      <TableCell className="text-muted-foreground text-sm max-w-[200px] truncate">
                        {policy.description || '-'}
                      </TableCell>
                      <TableCell>
                        <Badge variant={policy.is_system ? 'secondary' : 'default'}>
                          {policy.is_system ? 'System' : 'Custom'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              setViewingPolicy(policy)
                              setViewOpen(true)
                            }}
                          >
                            <Eye className="w-3 h-3" />
                            <span className="ml-1">View</span>
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="destructive" size="sm" disabled={policy.is_system}>
                                <Trash2 className="w-3 h-3" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete Policy</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete "{policy.name}"? This action cannot be undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={() => handleDelete(policy.id)}>
                                  Delete
                                </AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}

        <Dialog open={viewOpen} onOpenChange={setViewOpen}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                {viewingPolicy?.name}
              </DialogTitle>
            </DialogHeader>
            {viewingPolicy && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Description</Label>
                    <p className="text-sm text-muted-foreground mt-1">
                      {viewingPolicy.description || 'No description'}
                    </p>
                  </div>
                  <div>
                    <Label>Status</Label>
                    <div className="mt-1">
                      <Badge variant={viewingPolicy.is_system ? 'secondary' : 'default'}>
                        {viewingPolicy.is_system ? 'System' : 'Custom'}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div>
                  <Label>Policy Document</Label>
                  <pre className="mt-2 p-4 rounded-lg bg-secondary text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(viewingPolicy.policy_document, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  )
}

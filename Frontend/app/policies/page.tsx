'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Plus,
  Shield,
  Trash2,
  Loader2,
  Eye,
  Edit3,
  CheckCircle2,
  XCircle,
  FileText,
} from 'lucide-react'
import useSWR, { mutate } from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
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
import type { Policy, PolicyDocument } from '@/lib/types'

const DEFAULT_POLICY_DOCUMENT: PolicyDocument = {
  Version: '2025-01-01',
  Statement: [
    {
      Effect: 'Allow',
      Action: ['*'],
      Resource: ['*'],
    },
  ],
}

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
    policy_document: JSON.stringify(DEFAULT_POLICY_DOCUMENT, null, 2),
  })

  const resetForm = () => setForm({
    name: '',
    description: '',
    policy_document: JSON.stringify(DEFAULT_POLICY_DOCUMENT, null, 2),
  })

  const handleCreate = async () => {
    if (!form.name) {
      toast({ title: 'Validation error', description: 'Name is required', variant: 'destructive' })
      return
    }
    let doc: PolicyDocument
    try {
      doc = JSON.parse(form.policy_document)
    } catch {
      toast({ title: 'Invalid JSON', description: 'Policy document must be valid JSON', variant: 'destructive' })
      return
    }
    setSaving(true)
    try {
      const res = await policyApi.create({
        name: form.name,
        description: form.description || undefined,
        policy_document: doc,
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

  const handleToggleActive = async (policy: Policy) => {
    const res = await policyApi.update(policy.id, { is_active: !policy.is_active })
    if (res.error) {
      toast({ title: 'Error', description: 'Failed to update policy', variant: 'destructive' })
      return
    }
    mutate('policies-list')
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
            <DialogContent className="max-w-2xl">
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
                <div className="space-y-2">
                  <Label>Policy Document (JSON)</Label>
                  <Textarea
                    value={form.policy_document}
                    onChange={(e) => setForm({ ...form, policy_document: e.target.value })}
                    className="font-mono text-xs min-h-[200px]"
                  />
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
                        <Badge variant={policy.is_active ? 'default' : 'secondary'}>
                          {policy.is_active ? 'Active' : 'Inactive'}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {policy.updated_at ? new Date(policy.updated_at).toLocaleDateString() : '-'}
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
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleToggleActive(policy)}
                          >
                            {policy.is_active ? (
                              <XCircle className="w-3 h-3" />
                            ) : (
                              <CheckCircle2 className="w-3 h-3" />
                            )}
                            <span className="ml-1">{policy.is_active ? 'Deactivate' : 'Activate'}</span>
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="destructive" size="sm">
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
                      <Badge variant={viewingPolicy.is_active ? 'default' : 'secondary'}>
                        {viewingPolicy.is_active ? 'Active' : 'Inactive'}
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

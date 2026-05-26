'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Plus,
  Lock,
  Trash2,
  Eye,
  EyeOff,
  RotateCcw,
  Key,
  Loader2,
} from 'lucide-react'
import useSWR, { mutate } from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
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
import { useToast } from '@/hooks/use-toast'
import { secretApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'

interface SecretDTO {
  id: string
  name: string
  description: string | null
  created_at: string | null
  updated_at: string | null
}

interface SecretWithValue extends SecretDTO {
  value: string
}

const fetcher = async (): Promise<SecretDTO[]> => {
  const res = await secretApi.list()
  if (res.error) throw new Error(res.error)
  return res.data ?? []
}

export default function SecretsPage() {
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)

  const { data: secrets, error, isLoading } = useSWR<SecretDTO[]>(
    token ? 'secrets-list' : null,
    fetcher
  )

  const [addOpen, setAddOpen] = useState(false)
  const [editOpen, setEditOpen] = useState(false)
  const [viewOpen, setViewOpen] = useState(false)
  const [regenerateOpen, setRegenerateOpen] = useState(false)
  const [editingSecret, setEditingSecret] = useState<SecretDTO | null>(null)
  const [viewingSecret, setViewingSecret] = useState<SecretWithValue | null>(null)
  const [regeneratingSecret, setRegeneratingSecret] = useState<SecretDTO | null>(null)
  const [revealedIds, setRevealedIds] = useState<Set<string>>(new Set())

  const [form, setForm] = useState({ name: '', value: '', description: '' })
  const [saving, setSaving] = useState(false)

  const resetForm = () => setForm({ name: '', value: '', description: '' })

  const handleCreate = async () => {
    if (!form.name || !form.value) {
      toast({ title: 'Validation error', description: 'Name and value are required', variant: 'destructive' })
      return
    }
    setSaving(true)
    try {
      const res = await secretApi.create({
        name: form.name,
        value: form.value,
        description: form.description || undefined,
      })
      if (res.error) throw new Error(res.error)
      toast({ title: 'Secret created' })
      setAddOpen(false)
      resetForm()
      mutate('secrets-list')
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    } finally {
      setSaving(false)
    }
  }

  const handleUpdate = async () => {
    if (!editingSecret) return
    if (!form.name) {
      toast({ title: 'Validation error', description: 'Name is required', variant: 'destructive' })
      return
    }
    setSaving(true)
    try {
      const res = await secretApi.update(editingSecret.id, {
        name: form.name,
        value: form.value || undefined,
        description: form.description || undefined,
      })
      if (res.error) throw new Error(res.error)
      toast({ title: 'Secret updated' })
      setEditOpen(false)
      setEditingSecret(null)
      resetForm()
      mutate('secrets-list')
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    try {
      const res = await secretApi.delete(id)
      if (res.error) throw new Error(res.error)
      toast({ title: 'Secret deleted' })
      mutate('secrets-list')
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  const handleView = async (id: string) => {
    try {
      const res = await secretApi.get(id)
      if (res.error) throw new Error(res.error)
      setViewingSecret(res.data ?? null)
      setViewOpen(true)
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  const handleRegenerate = async () => {
    if (!regeneratingSecret || !form.value) {
      toast({ title: 'Validation error', description: 'New value is required', variant: 'destructive' })
      return
    }
    setSaving(true)
    try {
      const res = await secretApi.regenerate(regeneratingSecret.id, {
        value: form.value,
        description: form.description || undefined,
      })
      if (res.error) throw new Error(res.error)
      toast({ title: 'Secret regenerated' })
      setRegenerateOpen(false)
      setRegeneratingSecret(null)
      resetForm()
      mutate('secrets-list')
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    } finally {
      setSaving(false)
    }
  }

  const openEdit = (s: SecretDTO) => {
    setEditingSecret(s)
    setForm({ name: s.name, value: '', description: s.description ?? '' })
    setEditOpen(true)
  }

  const openRegenerate = (s: SecretDTO) => {
    setRegeneratingSecret(s)
    setForm({ name: s.name, value: '', description: s.description ?? '' })
    setRegenerateOpen(true)
  }

  const toggleReveal = (id: string) => {
    setRevealedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Secrets</h1>
            <p className="text-muted-foreground mt-1">
              Manage encrypted secrets for your workspace. Values are encrypted at rest.
            </p>
          </div>
          <Dialog open={addOpen} onOpenChange={(v) => { setAddOpen(v); if (!v) resetForm() }}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Add Secret
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New Secret</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <Label>Name</Label>
                  <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="e.g. OPENAI_API_KEY" />
                </div>
                <div>
                  <Label>Value</Label>
                  <Textarea value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder="Secret value to encrypt" />
                </div>
                <div>
                  <Label>Description (optional)</Label>
                  <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} placeholder="What is this secret used for?" />
                </div>
                <Button onClick={handleCreate} disabled={saving} className="w-full">
                  {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Key className="w-4 h-4 mr-2" />}
                  Create Secret
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>All Secrets</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
              </div>
            ) : error ? (
              <p className="text-destructive">Failed to load secrets: {error.message}</p>
            ) : !secrets || secrets.length === 0 ? (
              <p className="text-muted-foreground py-4 text-center">
                No secrets yet. Click <strong>Add Secret</strong> to create one.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {secrets.map((s) => (
                    <TableRow key={s.id}>
                      <TableCell className="font-medium">
                        <div className="flex items-center gap-2">
                          <Lock className="w-4 h-4 text-muted-foreground" />
                          {s.name}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{s.description ?? '—'}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : '—'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="sm" onClick={() => handleView(s.id)}>
                            <Eye className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => openEdit(s)}>
                            <Lock className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => openRegenerate(s)}>
                            <RotateCcw className="w-4 h-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="ghost" size="sm">
                                <Trash2 className="w-4 h-4 text-destructive" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Delete Secret</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to delete <strong>{s.name}</strong>? This cannot be undone.
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={() => handleDelete(s.id)}>Delete</AlertDialogAction>
                              </AlertDialogFooter>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* View Secret Dialog */}
        <Dialog open={viewOpen} onOpenChange={setViewOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{viewingSecret?.name ?? 'Secret'}</DialogTitle>
            </DialogHeader>
            {viewingSecret && (
              <div className="space-y-4">
                <div>
                  <Label>Value</Label>
                  <div className="flex items-center gap-2">
                    <code className="flex-1 p-2 bg-muted rounded text-sm break-all">
                      {viewingSecret.value}
                    </code>
                  </div>
                </div>
                {viewingSecret.description && (
                  <div>
                    <Label>Description</Label>
                    <p className="text-sm text-muted-foreground">{viewingSecret.description}</p>
                  </div>
                )}
                <Button variant="outline" className="w-full" onClick={() => setViewOpen(false)}>Close</Button>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Edit Secret Dialog */}
        <Dialog open={editOpen} onOpenChange={(v) => { setEditOpen(v); if (!v) { setEditingSecret(null); resetForm() } }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Edit Secret</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <Label>Name</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
              </div>
              <div>
                <Label>New Value (leave blank to keep current)</Label>
                <Textarea value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder="Leave empty to keep existing value" />
              </div>
              <div>
                <Label>Description</Label>
                <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <Button onClick={handleUpdate} disabled={saving} className="w-full">
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : null}
                Save Changes
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* Regenerate Secret Dialog */}
        <Dialog open={regenerateOpen} onOpenChange={(v) => { setRegenerateOpen(v); if (!v) { setRegeneratingSecret(null); resetForm() } }}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Regenerate Secret</DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Updating value for <strong>{regeneratingSecret?.name}</strong>
              </p>
              <div>
                <Label>New Value</Label>
                <Textarea value={form.value} onChange={(e) => setForm({ ...form, value: e.target.value })} placeholder="New secret value" />
              </div>
              <div>
                <Label>Description</Label>
                <Input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
              </div>
              <Button onClick={handleRegenerate} disabled={saving} className="w-full">
                {saving ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <RotateCcw className="w-4 h-4 mr-2" />}
                Regenerate
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  )
}

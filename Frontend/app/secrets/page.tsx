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
  Copy,
  Check,
  Code,
  Info,
} from 'lucide-react'
import useSWR, { mutate } from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Badge } from '@/components/ui/badge'
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
import { secretApi, authApi } from '@/lib/api'
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

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

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

  // API Keys
  const { data: apiKeys, mutate: mutateApiKeys } = useSWR(
    token ? 'api-keys-list' : null,
    async () => {
      const res = await authApi.listApiKeys()
      if (res.error) throw new Error(res.error)
      return res.data ?? []
    }
  )
  const [apiKeyAddOpen, setApiKeyAddOpen] = useState(false)
  const [newApiKeyName, setNewApiKeyName] = useState('')
  const [newApiKeyResult, setNewApiKeyResult] = useState<{ name: string; key: string } | null>(null)
  const [creatingKey, setCreatingKey] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)

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
        <div>
          <h1 className="text-3xl font-bold text-foreground">Secrets & Keys</h1>
          <p className="text-muted-foreground mt-1">
            Manage encrypted secrets and API keys for your workspace.
          </p>
        </div>

        <Tabs defaultValue="secrets">
          <TabsList>
            <TabsTrigger value="secrets" className="gap-2">
              <Lock className="w-4 h-4" />
              Secrets
            </TabsTrigger>
            <TabsTrigger value="api-keys" className="gap-2">
              <Key className="w-4 h-4" />
              API Keys
            </TabsTrigger>
          </TabsList>

          <TabsContent value="secrets" className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Encrypted Secrets</h2>
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
              <CardContent className="pt-6">
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
          </TabsContent>

          <TabsContent value="api-keys" className="mt-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold">Authentication API Keys</h2>
              <Dialog open={apiKeyAddOpen} onOpenChange={(v) => { setApiKeyAddOpen(v); if (!v) { setNewApiKeyName(''); setNewApiKeyResult(null) } }}>
                <DialogTrigger asChild>
                  <Button>
                    <Plus className="w-4 h-4 mr-2" />
                    Generate Key
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Generate API Key</DialogTitle>
                  </DialogHeader>
                  {newApiKeyResult ? (
                    <div className="space-y-4">
                      <p className="text-sm text-muted-foreground">
                        Copy this key now — it will not be shown again.
                      </p>
                      <div className="flex items-center gap-2">
                        <code className="flex-1 p-2 bg-muted rounded text-sm break-all">{newApiKeyResult.key}</code>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => {
                            navigator.clipboard.writeText(newApiKeyResult.key)
                            setCopiedId('new')
                            setTimeout(() => setCopiedId(null), 2000)
                          }}
                        >
                          {copiedId === 'new' ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                        </Button>
                      </div>
                      <div className="pt-3 border-t space-y-2">
                        <p className="text-xs font-medium text-muted-foreground">Usage examples</p>
                        <pre className="bg-muted p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap break-all">
curl -H "X-API-Key: {newApiKeyResult.key}" \<br/>  {API_BASE_URL}/workflow/workflows/{{id}}/run</pre>
                        <pre className="bg-muted p-2 rounded text-xs overflow-x-auto whitespace-pre-wrap break-all">
curl -H "X-API-Key: {newApiKeyResult.key}" \<br/>  {API_BASE_URL}/observability/traces</pre>
                        <p className="text-xs text-muted-foreground flex items-start gap-1">
                          <Info className="w-3 h-3 mt-0.5 shrink-0" />
                          API keys cannot be used for admin operations (IAM, members, billing, etc.) — use JWT Bearer auth for those.
                        </p>
                      </div>
                      <Button variant="outline" className="w-full" onClick={() => { setApiKeyAddOpen(false); setNewApiKeyResult(null) }}>
                        Done
                      </Button>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      <div>
                        <Label>Key Name</Label>
                        <Input
                          value={newApiKeyName}
                          onChange={(e) => setNewApiKeyName(e.target.value)}
                          placeholder="e.g. CI/CD Pipeline Key"
                        />
                      </div>
                      <Button
                        onClick={async () => {
                          if (!newApiKeyName) {
                            toast({ title: 'Error', description: 'Name is required', variant: 'destructive' })
                            return
                          }
                          setCreatingKey(true)
                          try {
                            const res = await authApi.createApiKey(newApiKeyName)
                            if (res.error) throw new Error(res.error)
                            setNewApiKeyResult(res.data!)
                            mutate('api-keys-list')
                          } catch (e) {
                            toast({ title: 'Error', description: String(e), variant: 'destructive' })
                          } finally {
                            setCreatingKey(false)
                          }
                        }}
                        disabled={creatingKey}
                        className="w-full"
                      >
                        {creatingKey ? <Loader2 className="w-4 h-4 mr-2 animate-spin" /> : <Key className="w-4 h-4 mr-2" />}
                        Generate
                      </Button>
                    </div>
                  )}
                </DialogContent>
              </Dialog>
            </div>

            <Card>
              <CardContent className="pt-6">
                {!apiKeys ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
                  </div>
                ) : apiKeys.length === 0 ? (
                  <p className="text-muted-foreground py-4 text-center">
                    No API keys yet. Click <strong>Generate Key</strong> to create one.
                  </p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Prefix</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Created</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {apiKeys.map((k) => (
                        <TableRow key={k.id}>
                          <TableCell className="font-medium">{k.name}</TableCell>
                          <TableCell className="font-mono text-sm text-muted-foreground">{k.key_prefix}...</TableCell>
                          <TableCell>
                            <Badge variant={k.is_active ? 'default' : 'secondary'}>
                              {k.is_active ? 'Active' : 'Inactive'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-muted-foreground text-sm">
                            {k.created_at ? new Date(k.created_at).toLocaleDateString() : '—'}
                          </TableCell>
                          <TableCell className="text-right">
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="destructive" size="sm">
                                  <Trash2 className="w-3 h-3" />
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Revoke API Key</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Revoke <strong>{k.name}</strong>? Any services using this key will lose access immediately.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction onClick={async () => {
                                    const res = await authApi.deleteApiKey(k.id)
                                    if (res.error) {
                                      toast({ title: 'Error', description: 'Failed to delete key', variant: 'destructive' })
                                      return
                                    }
                                    toast({ title: 'Revoked', description: `Key "${k.name}" revoked` })
                                    mutate('api-keys-list')
                                  }}>
                                    Revoke
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            {apiKeys && apiKeys.length > 0 && (
              <Card className="mt-6">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Code className="w-4 h-4" />
                    Usage Guide
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-sm">
                  <p className="text-muted-foreground">
                    Pass the key in the <code className="text-xs bg-muted px-1 rounded">X-API-Key</code> header for programmatic access:
                  </p>
                  <div className="space-y-2">
                    <p className="font-medium text-xs text-foreground">Run a workflow</p>
                    <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">curl -X POST {API_BASE_URL}/workflow/workflows/{'{id}'}/run -H "X-API-Key: agk_..."</pre>
                  </div>
                  <div className="space-y-2">
                    <p className="font-medium text-xs text-foreground">Query traces</p>
                    <pre className="bg-muted p-2 rounded text-xs overflow-x-auto">curl {API_BASE_URL}/observability/traces -H "X-API-Key: agk_..."</pre>
                  </div>
                  <p className="text-xs text-muted-foreground flex items-start gap-1">
                    <Info className="w-3 h-3 mt-0.5 shrink-0" />
                    API keys do not have a user context. They cannot be used for admin operations (IAM, members, billing, etc.).
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>
        </Tabs>

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

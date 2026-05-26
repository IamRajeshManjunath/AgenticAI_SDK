'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Plus,
  Plug,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Cable,
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
import { useToast } from '@/hooks/use-toast'
import { integrationApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import type { IntegrationConnection } from '@/lib/types'

const INTEGRATION_TYPES = [
  { value: 'slack', label: 'Slack' },
  { value: 'discord', label: 'Discord' },
  { value: 'whatsapp', label: 'WhatsApp' },
  { value: 'telegram', label: 'Telegram' },
  { value: 'email', label: 'Email (SMTP)' },
  { value: 'webhook', label: 'Webhook' },
  { value: 'jira', label: 'Jira' },
  { value: 'github', label: 'GitHub' },
  { value: 'gitlab', label: 'GitLab' },
]

const fetcher = async (): Promise<IntegrationConnection[]> => {
  const res = await integrationApi.list()
  if (res.error) throw new Error(res.error)
  return res.data ?? []
}

export default function IntegrationsPage() {
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)

  const { data: integrations, error, isLoading } = useSWR<IntegrationConnection[]>(
    token ? 'integrations-list' : null,
    fetcher,
    { refreshInterval: 10000 }
  )

  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({ integration_type: '', name: '', auth_state: '' })
  const [saving, setSaving] = useState(false)
  const [testingId, setTestingId] = useState<string | null>(null)

  const resetForm = () => setForm({ integration_type: '', name: '', auth_state: '' })

  const handleConnect = async () => {
    if (!form.integration_type || !form.name) {
      toast({ title: 'Validation error', description: 'Type and name are required', variant: 'destructive' })
      return
    }
    setSaving(true)
    try {
      const res = await integrationApi.connect({
        integration_type: form.integration_type,
        name: form.name,
        auth_state: form.auth_state ? { token: form.auth_state } : undefined,
      })
      if (res.error) throw new Error(res.error)
      toast({ title: 'Connected', description: `${form.name} integration created` })
      setAddOpen(false)
      resetForm()
      mutate('integrations-list')
    } catch (e) {
      toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to connect', variant: 'destructive' })
    } finally {
      setSaving(false)
    }
  }

  const handleDisconnect = async (type: string) => {
    const res = await integrationApi.disconnect(type)
    if (res.error) {
      toast({ title: 'Error', description: 'Failed to disconnect', variant: 'destructive' })
      return
    }
    toast({ title: 'Disconnected', description: `Integration ${type} disconnected` })
    mutate('integrations-list')
  }

  const handleTest = async (type: string) => {
    setTestingId(type)
    try {
      const res = await integrationApi.test(type)
      if (res.error) throw new Error(res.error)
      toast({ title: 'Test Succeeded', description: 'Connection is working' })
    } catch (e) {
      toast({ title: 'Test Failed', description: e instanceof Error ? e.message : 'Connection test failed', variant: 'destructive' })
    } finally {
      setTestingId(null)
    }
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Integrations</h1>
            <p className="text-muted-foreground mt-1">
              Connect external services to your workflows
            </p>
          </div>
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button className="gap-2">
                <Plus className="w-4 h-4" />
                Connect
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>New Integration</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label>Type</Label>
                  <Select
                    value={form.integration_type}
                    onValueChange={(v) => setForm({ ...form, integration_type: v })}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select integration type" />
                    </SelectTrigger>
                    <SelectContent>
                      {INTEGRATION_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value}>{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Name</Label>
                  <Input
                    value={form.name}
                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                    placeholder="My Slack Connection"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Auth Token (optional)</Label>
                  <Input
                    value={form.auth_state}
                    onChange={(e) => setForm({ ...form, auth_state: e.target.value })}
                    placeholder="Bearer token or API key"
                    type="password"
                  />
                </div>
                <Button onClick={handleConnect} disabled={saving} className="w-full">
                  {saving && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                  Connect
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
              <p>Failed to load integrations</p>
            </CardContent>
          </Card>
        ) : !integrations?.length ? (
          <Card className="glass-card">
            <CardContent className="py-16 text-center">
              <Cable className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
              <h3 className="text-lg font-medium mb-2">No integrations yet</h3>
              <p className="text-muted-foreground mb-6 max-w-md mx-auto">
                Connect external services like Slack, Discord, or GitHub to extend your workflow capabilities.
              </p>
              <Button onClick={() => setAddOpen(true)} className="gap-2">
                <Plus className="w-4 h-4" />
                Connect First Integration
              </Button>
            </CardContent>
          </Card>
        ) : (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Plug className="w-5 h-5" />
                Connected Integrations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Type</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Connected</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {integrations.map((conn) => (
                    <TableRow key={conn.id}>
                      <TableCell>
                        <Badge variant="secondary">{conn.integration_type}</Badge>
                      </TableCell>
                      <TableCell className="font-medium">{conn.name}</TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {conn.created_at ? new Date(conn.created_at).toLocaleDateString() : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleTest(conn.integration_type)}
                            disabled={testingId === conn.integration_type}
                          >
                            {testingId === conn.integration_type ? (
                              <Loader2 className="w-3 h-3 animate-spin" />
                            ) : (
                              <RefreshCw className="w-3 h-3" />
                            )}
                            <span className="ml-1">Test</span>
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="destructive" size="sm">
                                <Trash2 className="w-3 h-3" />
                                <span className="ml-1">Disconnect</span>
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogHeader>
                                <AlertDialogTitle>Disconnect Integration</AlertDialogTitle>
                                <AlertDialogDescription>
                                  Are you sure you want to disconnect {conn.name} ({conn.integration_type})?
                                </AlertDialogDescription>
                              </AlertDialogHeader>
                              <AlertDialogFooter>
                                <AlertDialogCancel>Cancel</AlertDialogCancel>
                                <AlertDialogAction onClick={() => handleDisconnect(conn.integration_type)}>
                                  Disconnect
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
      </div>
    </DashboardLayout>
  )
}

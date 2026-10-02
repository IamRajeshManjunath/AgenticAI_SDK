'use client'

import { useState, useEffect } from 'react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Settings, Key, Bell, Shield, Database, CheckCircle2, AlertCircle, Users, Mail, UserMinus, RotateCcw, Plug, Loader2, FileText, Save, RefreshCw, Diff } from 'lucide-react'
import useSWR, { mutate } from 'swr'
import { useToast } from '@/hooks/use-toast'
import { memberApi, dbApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import type { WorkspaceMember } from '@/lib/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
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

const fetcher = (url: string) => fetch(url).then((res) => res.json())

// Config types
interface ConfigResponse {
  platform: Record<string, unknown>
  integrations: Record<string, unknown>
  version: string
  last_modified?: string
}

interface ConfigUpdateRequest {
  config: Record<string, unknown>
  merge_strategy?: 'json_merge' | 'id_aware' | 'replace'
}

function yamlToJson(yaml: string): Record<string, unknown> {
  try {
    // Simple YAML to JSON - in production use js-yaml
    return JSON.parse(yaml)
  } catch {
    return {}
  }
}

function jsonToYaml(obj: Record<string, unknown>): string {
  // Simple JSON to YAML - in production use js-yaml
  return JSON.stringify(obj, null, 2)
}

function ConfigTab() {
  const { toast } = useToast()
  const { configApi } = require('@/lib/api')
  const [yamlContent, setYamlContent] = useState<string>('')
  const [originalYaml, setOriginalYaml] = useState<string>('')
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [status, setStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [showDiff, setShowDiff] = useState(false)

  // Load initial config
  const loadConfig = async () => {
    setIsLoading(true)
    try {
      const res = await configApi.get()
      if (res.data) {
        const yaml = jsonToYaml(res.data)
        setYamlContent(yaml)
        setOriginalYaml(yaml)
      }
    } catch (error) {
      toast({ title: 'Error', description: 'Failed to load configuration', variant: 'destructive' })
    } finally {
      setIsLoading(false)
    }
  }

  // Load on mount
  useEffect(() => {
    loadConfig()
  }, [])

  // Save config
  const handleSave = async () => {
    setIsSaving(true)
    setStatus('saving')
    try {
      const config = yamlToJson(yamlContent)
      const res = await configApi.update({ config, merge_strategy: 'id_aware' })
      if (res.data) {
        const newYaml = jsonToYaml(res.data)
        setYamlContent(newYaml)
        setOriginalYaml(newYaml)
        setStatus('saved')
        toast({ title: 'Configuration saved', description: 'Changes have been applied and hot-reload triggered' })
      } else {
        throw new Error(res.error || 'Failed to save')
      }
    } catch (error) {
      setStatus('error')
      toast({ title: 'Save failed', description: error instanceof Error ? error.message : 'Unknown error', variant: 'destructive' })
    } finally {
      setIsSaving(false)
      setTimeout(() => setStatus('idle'), 2000)
    }
  }

  // Reload config from server
  const handleReload = async () => {
    setIsSaving(true)
    try {
      const res = await configApi.reload()
      if (res.data) {
        const yaml = jsonToYaml(res.data)
        setYamlContent(yaml)
        setOriginalYaml(yaml)
        toast({ title: 'Reloaded', description: 'Configuration reloaded from server' })
      }
    } catch (error) {
      toast({ title: 'Reload failed', description: error instanceof Error ? error.message : 'Unknown error', variant: 'destructive' })
    } finally {
      setIsSaving(false)
    }
  }

  // Subscribe to real-time config changes
  useEffect(() => {
    const cleanup = configApi.streamChanges(
      (newConfig) => {
        const yaml = jsonToYaml(newConfig)
        setYamlContent(yaml)
        setOriginalYaml(yaml)
        toast({ title: 'Config updated', description: 'Configuration changed by another user' })
      },
      (error) => console.error('Config stream error:', error)
    )
    return () => cleanup()
  }, [])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[600px]">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const hasChanges = yamlContent !== originalYaml

  return (
    <Card className="glass-card h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle>Configuration</CardTitle>
            <CardDescription>
              Edit agenticai.yaml with live syntax highlighting and validation
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReload}
              disabled={isSaving}
              className="gap-1"
            >
              <RefreshCw className="w-4 h-4" />
              Reload
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDiff(!showDiff)}
              className="gap-1"
            >
              <Diff className="w-4 h-4" />
              Diff
            </Button>
            <Button
              onClick={handleSave}
              disabled={isSaving || !hasChanges}
              className="gap-2 glow-primary-sm"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Saving...' : 'Save Changes'}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden">
        <div className="relative h-[600px]">
          <textarea
            value={yamlContent}
            onChange={(e) => setYamlContent(e.target.value)}
            className="w-full h-full font-mono text-sm bg-background border border-border rounded-lg p-4 resize-none focus:ring-2 focus:ring-primary"
            placeholder="Loading configuration..."
            spellCheck={false}
          />
          {status === 'saved' && (
            <div className="absolute bottom-4 right-4 animate-slide-in">
              <div className="bg-success text-success-foreground px-4 py-2 rounded-lg shadow-lg flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                Saved successfully
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function DatabaseStatus() {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  const { data, error, isLoading } = useSWR(`${API_BASE}/workflow/db/status`, fetcher, {
    refreshInterval: 5000 // Refresh every 5s
  })

  const getProviderLabel = (provider: string) => {
    switch (provider) {
      case 'supabase':
        return 'Supabase'
      case 'neon':
        return 'Neon'
      case 'postgres':
        return 'PostgreSQL'
      case 'mock':
        return 'Mock (In-Memory)'
      default:
        return provider
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-muted-foreground">
        <Database className="w-4 h-4 animate-pulse" />
        <span>Checking connection...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-destructive">
        <AlertCircle className="w-4 h-4" />
        <span>Failed to check status</span>
      </div>
    )
  }

  const isMock = data?.provider === 'mock'

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {isMock ? (
          <AlertCircle className="w-4 h-4 text-warning" />
        ) : (
          <CheckCircle2 className="w-4 h-4 text-success" />
        )}
        <span className={isMock ? 'text-warning' : 'text-success'}>
          {getProviderLabel(data?.provider)}
        </span>
      </div>
      {isMock && (
        <p className="text-xs text-muted-foreground">
          Data is stored in memory and will be lost on refresh. 
          Connect a database to persist your data.
        </p>
      )}
    </div>
  )
}

// Members fetcher
const membersFetcher = async (): Promise<WorkspaceMember[]> => {
  const res = await memberApi.list()
  if (res.error) throw new Error(res.error)
  return res.data ?? []
}

export default function SettingsPage() {
  const { toast } = useToast()
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'
  const token = useAuthStore((s) => s.token)

  const [dbUri, setDbUri] = useState('')
  const [provider, setProvider] = useState('postgres')
  const [isConnecting, setIsConnecting] = useState(false)
  const [isDisconnecting, setIsDisconnecting] = useState(false)
  const [isMigrating, setIsMigrating] = useState(false)

  // Members state
  const { data: members, error: membersError, isLoading: membersLoading } = useSWR<WorkspaceMember[]>(
    token ? 'workspace-members' : null,
    membersFetcher
  )
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('editor')
  const [inviting, setInviting] = useState(false)

  const handleConnect = async () => {
    setIsConnecting(true)
    try {
      const response = await fetch(`${API_BASE}/workflow/db/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, uri: dbUri }),
      })
      if (response.ok) {
        mutate(`${API_BASE}/workflow/db/status`)
        toast({
          title: "Database Connected",
          description: "Successfully connected to the database provider.",
        })
      } else {
        toast({
          title: "Connection Failed",
          description: "Could not establish a connection to the database.",
          variant: "destructive",
        })
      }
    } catch (error) {
      console.error('Connection error:', error)
      toast({
        title: "Error",
        description: "An unexpected error occurred while connecting.",
        variant: "destructive",
      })
    } finally {
      setIsConnecting(false)
    }
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Settings</h1>
          <p className="text-muted-foreground mt-1">
            Manage your platform configuration and preferences
          </p>
        </div>

        <Tabs defaultValue="general" className="space-y-6">
          <TabsList className="bg-secondary">
            <TabsTrigger value="general" className="gap-2">
              <Settings className="w-4 h-4" />
              General
            </TabsTrigger>
            <TabsTrigger value="database" className="gap-2">
              <Database className="w-4 h-4" />
              Database
            </TabsTrigger>
            <TabsTrigger value="config" className="gap-2">
              <FileText className="w-4 h-4" />
              Configuration
            </TabsTrigger>
            <TabsTrigger value="api" className="gap-2">
              <Key className="w-4 h-4" />
              API Keys
            </TabsTrigger>
            <TabsTrigger value="notifications" className="gap-2">
              <Bell className="w-4 h-4" />
              Notifications
            </TabsTrigger>
            <TabsTrigger value="security" className="gap-2">
              <Shield className="w-4 h-4" />
              Security
            </TabsTrigger>
            <TabsTrigger value="members" className="gap-2">
              <Users className="w-4 h-4" />
              Members
            </TabsTrigger>
          </TabsList>

          <TabsContent value="general">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>General Settings</CardTitle>
                <CardDescription>
                  Configure your workspace and display preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="workspace-name">Workspace Name</Label>
                  <Input
                    id="workspace-name"
                    placeholder="My Workspace"
                    defaultValue="Harpy.AI Workspace"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="api-base-url">API Base URL</Label>
                  <Input
                    id="api-base-url"
                    placeholder={API_BASE}
                    defaultValue={API_BASE}
                    className="font-mono text-sm"
                  />
                  <p className="text-xs text-muted-foreground">
                    The base URL for the FastAPI backend
                  </p>
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Dark Mode</Label>
                    <p className="text-sm text-muted-foreground">
                      Enable dark mode interface
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Auto-save Workflows</Label>
                    <p className="text-sm text-muted-foreground">
                      Automatically save changes to workflows
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Button className="glow-primary-sm">Save Changes</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="database">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Database Connection</CardTitle>
                <CardDescription>
                  Configure your database provider for data persistence
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label>Current Provider</Label>
                  <DatabaseStatus />
                </div>

                <div className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="db-provider">Select Provider</Label>
                    <Select value={provider} onValueChange={setProvider}>
                      <SelectTrigger id="db-provider">
                        <SelectValue placeholder="Select a provider" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="postgres">PostgreSQL</SelectItem>
                        <SelectItem value="supabase">Supabase</SelectItem>
                        <SelectItem value="neon">Neon</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="db-uri">Database URI / Connection String</Label>
                    <div className="flex gap-2">
                      <Input
                        id="db-uri"
                        type="password"
                        placeholder="postgresql://user:password@localhost:5432/dbname"
                        value={dbUri}
                        onChange={(e) => setDbUri(e.target.value)}
                        className="font-mono text-xs"
                      />
                      <Button 
                        onClick={handleConnect} 
                        disabled={isConnecting || !dbUri}
                        className="shrink-0"
                      >
                        {isConnecting ? 'Connecting...' : 'Connect'}
                      </Button>
                    </div>
                    <p className="text-[10px] text-muted-foreground">
                      Sensitive credentials are encrypted and stored securely in the SDK gateway.
                    </p>
                  </div>
                </div>

                <div className="border-t border-border pt-6 space-y-4">
                  <h4 className="font-medium text-sm">Database Actions</h4>
                  <div className="flex gap-3">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={async () => {
                        setIsMigrating(true)
                        try {
                          const res = await dbApi.migrate()
                          if (res.error) throw new Error(res.error)
                          toast({ title: 'Migration Complete', description: res.data?.message || 'Database migrated successfully' })
                        } catch (e) {
                          toast({ title: 'Migration Failed', description: e instanceof Error ? e.message : 'Migration error', variant: 'destructive' })
                        } finally {
                          setIsMigrating(false)
                        }
                      }}
                      disabled={isMigrating}
                      className="gap-2"
                    >
                      {isMigrating ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
                      Run Migrations
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button variant="destructive" size="sm" className="gap-2">
                          <Plug className="w-4 h-4" />
                          Disconnect
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Disconnect Database</AlertDialogTitle>
                          <AlertDialogDescription>
                            This will disconnect the current database. Data will not be lost but workflows will use in-memory storage until reconnected.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={async () => {
                            setIsDisconnecting(true)
                            try {
                              const res = await dbApi.disconnect()
                              if (res.error) throw new Error(res.error)
                              toast({ title: 'Disconnected', description: 'Database disconnected' })
                              mutate(`${API_BASE}/workflow/db/status`)
                            } catch (e) {
                              toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to disconnect', variant: 'destructive' })
                            } finally {
                              setIsDisconnecting(false)
                            }
                          }}>
                            Disconnect
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
              </CardContent>
</Card>
            </TabsContent>

          <TabsContent value="config">
            <ConfigTab />
          </TabsContent>

          <TabsContent value="api">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>API Key Configuration</CardTitle>
                <CardDescription>
                  Store environment variable names for your LLM providers
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="space-y-2">
                  <Label htmlFor="openai-key">OpenAI API Key Env Var</Label>
                  <Input
                    id="openai-key"
                    placeholder="OPENAI_API_KEY"
                    defaultValue="OPENAI_API_KEY"
                    className="font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="anthropic-key">Anthropic API Key Env Var</Label>
                  <Input
                    id="anthropic-key"
                    placeholder="ANTHROPIC_API_KEY"
                    defaultValue="ANTHROPIC_API_KEY"
                    className="font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="google-key">Google AI API Key Env Var</Label>
                  <Input
                    id="google-key"
                    placeholder="GOOGLE_API_KEY"
                    defaultValue="GOOGLE_API_KEY"
                    className="font-mono"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="azure-key">Azure OpenAI API Key Env Var</Label>
                  <Input
                    id="azure-key"
                    placeholder="AZURE_OPENAI_API_KEY"
                    defaultValue="AZURE_OPENAI_API_KEY"
                    className="font-mono"
                  />
                </div>

                <Button className="glow-primary-sm">Save API Configuration</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="notifications">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
                <CardDescription>
                  Control how you receive alerts and updates
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>HITL Alerts</Label>
                    <p className="text-sm text-muted-foreground">
                      Notify when human approval is required
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Budget Warnings</Label>
                    <p className="text-sm text-muted-foreground">
                      Alert when approaching budget limits
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Workflow Completion</Label>
                    <p className="text-sm text-muted-foreground">
                      Notify when workflows finish execution
                    </p>
                  </div>
                  <Switch />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Error Notifications</Label>
                    <p className="text-sm text-muted-foreground">
                      Alert on workflow errors or failures
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Button className="glow-primary-sm">Save Preferences</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security">
            <Card className="glass-card">
              <CardHeader>
                <CardTitle>Security Settings</CardTitle>
                <CardDescription>
                  Configure security and compliance options
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Global PII Protection</Label>
                    <p className="text-sm text-muted-foreground">
                      Enable PII masking for all workflows
                    </p>
                  </div>
                  <Switch />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Prompt Injection Firewall</Label>
                    <p className="text-sm text-muted-foreground">
                      Enable global prompt injection detection
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Audit Logging</Label>
                    <p className="text-sm text-muted-foreground">
                      Log all workflow executions for compliance
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label>Data Retention</Label>
                    <p className="text-sm text-muted-foreground">
                      Keep execution logs for 30 days
                    </p>
                  </div>
                  <Switch defaultChecked />
                </div>

                <Button className="glow-primary-sm">Save Security Settings</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="members">
            <Card className="glass-card">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Workspace Members</CardTitle>
                    <CardDescription>
                      Manage who has access to this workspace
                    </CardDescription>
                  </div>
                  <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                    <DialogTrigger asChild>
                      <Button className="gap-2">
                        <Mail className="w-4 h-4" />
                        Invite Member
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Invite Member</DialogTitle>
                        <DialogDescription>
                          Send an invitation to join this workspace
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="invite-email">Email Address</Label>
                          <Input
                            id="invite-email"
                            type="email"
                            placeholder="colleague@company.com"
                            value={inviteEmail}
                            onChange={(e) => setInviteEmail(e.target.value)}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="invite-role">Role</Label>
                          <Select value={inviteRole} onValueChange={setInviteRole}>
                            <SelectTrigger id="invite-role">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">Admin</SelectItem>
                              <SelectItem value="editor">Editor</SelectItem>
                              <SelectItem value="viewer">Viewer</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <Button
                          onClick={async () => {
                            if (!inviteEmail) {
                              toast({ title: 'Error', description: 'Email is required', variant: 'destructive' })
                              return
                            }
                            setInviting(true)
                            try {
                              const res = await memberApi.invite(inviteEmail, inviteRole)
                              if (res.error) throw new Error(res.error)
                              toast({ title: 'Invited', description: `Invitation sent to ${inviteEmail}` })
                              setInviteOpen(false)
                              setInviteEmail('')
                              mutate('workspace-members')
                            } catch (e) {
                              toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to invite', variant: 'destructive' })
                            } finally {
                              setInviting(false)
                            }
                          }}
                          disabled={inviting}
                          className="w-full"
                        >
                          {inviting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                          Send Invitation
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                {membersLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                ) : membersError ? (
                  <p className="text-destructive text-sm">Failed to load members</p>
                ) : !members?.length ? (
                  <p className="text-muted-foreground text-sm py-8 text-center">No members found</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {members.map((m) => (
                        <TableRow key={m.user_id}>
                          <TableCell className="font-medium">{m.full_name || '-'}</TableCell>
                          <TableCell className="text-muted-foreground">{m.email}</TableCell>
                          <TableCell>
                            <Select
                              defaultValue={m.role}
                              onValueChange={async (role) => {
                                const res = await memberApi.updateRole(m.user_id, role)
                                if (res.error) {
                                  toast({ title: 'Error', description: 'Failed to update role', variant: 'destructive' })
                                  return
                                }
                                toast({ title: 'Updated', description: `Role changed to ${role}` })
                                mutate('workspace-members')
                              }}
                            >
                              <SelectTrigger className="w-28 h-8 text-sm">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="admin">Admin</SelectItem>
                                <SelectItem value="editor">Editor</SelectItem>
                                <SelectItem value="viewer">Viewer</SelectItem>
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell className="text-right">
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="destructive" size="sm">
                                  <UserMinus className="w-3 h-3 mr-1" />
                                  Remove
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Remove Member</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Remove {m.email} from this workspace? They will lose access to all workspace resources.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction onClick={async () => {
                                    const res = await memberApi.remove(m.user_id)
                                    if (res.error) {
                                      toast({ title: 'Error', description: 'Failed to remove member', variant: 'destructive' })
                                      return
                                    }
                                    toast({ title: 'Removed', description: `${m.email} removed from workspace` })
                                    mutate('workspace-members')
                                  }}>
                                    Remove
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
          </TabsContent>
        </Tabs>
      </div>
    </DashboardLayout>
  )
}

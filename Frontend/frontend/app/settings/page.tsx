'use client'

import { useState } from 'react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Settings, Key, Bell, Shield, Database, CheckCircle2, AlertCircle } from 'lucide-react'
import useSWR, { mutate } from 'swr'
import { useToast } from '@/hooks/use-toast'

const fetcher = (url: string) => fetch(url).then((res) => res.json())

function DatabaseStatus() {
  const { data, error, isLoading } = useSWR('http://localhost:8000/api/v1/workflow/db/status', fetcher, {
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

export default function SettingsPage() {
  const { toast } = useToast()
  const [dbUri, setDbUri] = useState('')
  const [provider, setProvider] = useState('postgres')
  const [isConnecting, setIsConnecting] = useState(false)

  const handleConnect = async () => {
    setIsConnecting(true)
    try {
      const response = await fetch('http://localhost:8000/api/v1/workflow/db/connect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, uri: dbUri }),
      })
      if (response.ok) {
        mutate('http://localhost:8000/api/v1/workflow/db/status')
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
                    placeholder="http://localhost:8000/api/v1"
                    defaultValue="http://localhost:8000/api/v1"
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

                <div className="border-t border-border pt-6 space-y-4 opacity-50 pointer-events-none">
                  <h4 className="font-medium text-sm text-muted-foreground">Quick Setup (Enterprise)</h4>
                  <div className="grid gap-4">
                    <div className="p-4 rounded-lg border border-border bg-secondary/30 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-emerald-500/20 flex items-center justify-center">
                          <span className="text-emerald-500 font-bold text-sm">S</span>
                        </div>
                        <div>
                          <p className="font-medium text-sm">Supabase One-Click</p>
                          <p className="text-[10px] text-muted-foreground">
                            Connect via OAuth
                          </p>
                        </div>
                      </div>
                      <Button variant="outline" size="sm" disabled>Connect</Button>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
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
        </Tabs>
      </div>
    </DashboardLayout>
  )
}

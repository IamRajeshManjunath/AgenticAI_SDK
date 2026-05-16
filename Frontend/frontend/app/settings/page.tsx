'use client'

import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Settings, Key, Bell, Shield, Database, CheckCircle2, AlertCircle } from 'lucide-react'
import useSWR from 'swr'

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

                <div className="border-t border-border pt-6 space-y-4">
                  <h4 className="font-medium text-sm">Supported Providers</h4>
                  <div className="grid gap-4">
                    <div className="p-4 rounded-lg border border-border bg-secondary/30">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-emerald-500/20 flex items-center justify-center">
                          <span className="text-emerald-500 font-bold text-sm">S</span>
                        </div>
                        <div>
                          <p className="font-medium">Supabase</p>
                          <p className="text-xs text-muted-foreground">
                            Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="p-4 rounded-lg border border-border bg-secondary/30">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-cyan-500/20 flex items-center justify-center">
                          <span className="text-cyan-500 font-bold text-sm">N</span>
                        </div>
                        <div>
                          <p className="font-medium">Neon</p>
                          <p className="text-xs text-muted-foreground">
                            Set NEON_DATABASE_URL or DATABASE_URL
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="p-4 rounded-lg border border-border bg-secondary/30">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded bg-blue-500/20 flex items-center justify-center">
                          <span className="text-blue-500 font-bold text-sm">P</span>
                        </div>
                        <div>
                          <p className="font-medium">PostgreSQL</p>
                          <p className="text-xs text-muted-foreground">
                            Set POSTGRES_URL or DATABASE_URL
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <p className="text-xs text-muted-foreground">
                  The database adapter is selected automatically based on available environment variables. 
                  Add your connection credentials in Vercel project settings or your .env.local file.
                </p>
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

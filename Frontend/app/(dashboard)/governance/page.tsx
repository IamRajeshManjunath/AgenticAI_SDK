import { Shield, AlertTriangle, CheckCircle, XCircle, Search, Filter, Download, RefreshCw, FileText, User, Key, Database, Settings } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Input } from "@/components/ui/input";

const MOCK_EVENTS = [
  { id: "evt_1", type: "COMPLIANCE_CHECK", severity: "info", message: "Data retention policy validated for workspace 'prod'", timestamp: "2024-01-15 10:25:00", workspace: "prod", user: "system" },
  { id: "evt_2", type: "ACCESS_GRANTED", severity: "info", message: "API key created for integration: tavily", timestamp: "2024-01-15 10:20:00", workspace: "prod", user: "admin@agenticai.dev" },
  { id: "evt_3", type: "RATE_LIMIT_EXCEEDED", severity: "warning", message: "Workspace 'dev' exceeded rate limit for openai (1000 req/min)", timestamp: "2024-01-15 10:15:00", workspace: "dev", user: "system" },
  { id: "evt_4", type: "SCHEMA_DRIFT_DETECTED", severity: "critical", message: "Vector store schema mismatch: dimension 1536 vs 3072 in collection 'documents'", timestamp: "2024-01-15 10:10:00", workspace: "staging", user: "system" },
  { id: "evt_5", type: "COST_THRESHOLD", severity: "warning", message: "Monthly cost threshold 80% reached ($450/$500)", timestamp: "2024-01-15 10:05:00", workspace: "prod", user: "system" },
  { id: "evt_6", type: "INTEGRATION_INSTALLED", severity: "info", message: "Plugin 'langchain-groq' installed by user", timestamp: "2024-01-15 09:45:00", workspace: "dev", user: "dev@agenticai.dev" },
  { id: "evt_7", type: "DB_ROUTE_MODIFIED", severity: "info", message: "Database route 'primary-vector' updated: changed provider to pinecone", timestamp: "2024-01-15 09:30:00", workspace: "prod", user: "admin@agenticai.dev" },
  { id: "evt_8", type: "PERMISSION_DENIED", severity: "warning", message: "User attempted to access admin-only endpoint /api/v1/admin/users", timestamp: "2024-01-15 09:15:00", workspace: "dev", user: "user@agenticai.dev" },
];

const MOCK_POLICIES = [
  { id: "pol_1", name: "Data Retention", type: "RETENTION", status: "active", description: "Delete user data after 90 days of inactivity", workspaces: ["prod", "staging"], created: "2024-01-01" },
  { id: "pol_2", name: "Cost Governance", type: "COST_LIMIT", status: "active", description: "Alert at 80% budget, block at 100% ($500/month)", workspaces: ["prod"], created: "2024-01-01" },
  { id: "pol_3", name: "API Key Rotation", type: "SECURITY", status: "active", description: "Rotate API keys every 90 days", workspaces: ["prod", "staging", "dev"], created: "2024-01-10" },
  { id: "pol_4", name: "Schema Validation", type: "DATA_QUALITY", status: "active", description: "Enforce strict schema validation on all DB routes", workspaces: ["prod", "staging"], created: "2024-01-15" },
];

const MOCK_API_KEYS = [
  { id: "key_1", name: "Production OpenAI", provider: "openai", scopes: ["chat", "embeddings", "tools"], lastUsed: "2 min ago", expires: "2024-04-15", status: "active" },
  { id: "key_2", name: "Staging Anthropic", provider: "anthropic", scopes: ["chat", "tools"], lastUsed: "1 hour ago", expires: "2024-03-20", status: "active" },
  { id: "key_3", name: "Dev Tavily", provider: "tavily", scopes: ["search"], lastUsed: "3 days ago", expires: "2024-02-28", status: "expiring" },
  { id: "key_4", name: "Legacy Key", provider: "openai", scopes: ["chat"], lastUsed: "Never", expires: "2023-12-01", status: "expired" },
];

function getSeverityBadge(severity: string) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    info: "default",
    warning: "secondary",
    critical: "destructive",
  };
  return <Badge variant={variants[severity] || "outline"}>{severity}</Badge>;
}

function getStatusBadge(status: string) {
  const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
    active: "default",
    expiring: "secondary",
    expired: "destructive",
  };
  return <Badge variant={variants[status] || "outline"}>{status}</Badge>;
}

export default function GovernancePage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Governance & Compliance</h1>
          <p className="text-muted-foreground">Audit logs, compliance policies, and security management</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm"><Download className="h-4 w-4 mr-1" />Export Report</Button>
          <Button variant="outline" size="sm"><RefreshCw className="h-4 w-4 mr-1" />Refresh</Button>
        </div>
      </div>

      <Tabs defaultValue="events" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="events"><Shield className="h-4 w-4 mr-2" />Audit Events</TabsTrigger>
          <TabsTrigger value="policies"><FileText className="h-4 w-4 mr-2" />Policies</TabsTrigger>
          <TabsTrigger value="api-keys"><Key className="h-4 w-4 mr-2" />API Keys</TabsTrigger>
          <TabsTrigger value="access"><User className="h-4 w-4 mr-2" />Access Control</TabsTrigger>
        </TabsList>

        {/* Audit Events */}
        <TabsContent value="events">
          <Card>
            <CardHeader>
              <div className="flex flex-wrap items-center justify-between gap-4">
                <CardTitle>Governance Event Log</CardTitle>
                <div className="flex items-center gap-2">
                  <Input placeholder="Search events..." className="w-64" />
                  <Select>
                    <SelectTrigger className="w-[160px]">
                      <SelectValue placeholder="All Severities" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Severities</SelectItem>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="warning">Warning</SelectItem>
                      <SelectItem value="info">Info</SelectItem>
                    </SelectContent>
                  </Select>
                  <Select>
                    <SelectTrigger className="w-[160px]">
                      <SelectValue placeholder="All Types" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">All Types</SelectItem>
                      <SelectItem value="COMPLIANCE_CHECK">Compliance Check</SelectItem>
                      <SelectItem value="ACCESS_GRANTED">Access Granted</SelectItem>
                      <SelectItem value="RATE_LIMIT_EXCEEDED">Rate Limit</SelectItem>
                      <SelectItem value="SCHEMA_DRIFT_DETECTED">Schema Drift</SelectItem>
                      <SelectItem value="COST_THRESHOLD">Cost Threshold</SelectItem>
                      <SelectItem value="INTEGRATION_INSTALLED">Integration Installed</SelectItem>
                      <SelectItem value="DB_ROUTE_MODIFIED">DB Route Modified</SelectItem>
                      <SelectItem value="PERMISSION_DENIED">Permission Denied</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Event</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>Message</TableHead>
                      <TableHead>Workspace</TableHead>
                      <TableHead>User</TableHead>
                      <TableHead>Timestamp</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {MOCK_EVENTS.map(event => (
                      <TableRow key={event.id}>
                        <TableCell><Badge variant="outline">{event.type}</Badge></TableCell>
                        <TableCell>{getSeverityBadge(event.severity)}</TableCell>
                        <TableCell className="max-w-md truncate">{event.message}</TableCell>
                        <TableCell><Badge variant="secondary">{event.workspace}</Badge></TableCell>
                        <TableCell>{event.user}</TableCell>
                        <TableCell className="font-mono text-xs">{event.timestamp}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Policies */}
        <TabsContent value="policies">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Compliance Policies</CardTitle>
                <Button><Settings className="h-4 w-4 mr-1" />Create Policy</Button>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Policy</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Description</TableHead>
                      <TableHead>Workspaces</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {MOCK_POLICIES.map(policy => (
                      <TableRow key={policy.id}>
                        <TableCell className="font-medium">{policy.name}</TableCell>
                        <TableCell><Badge variant="outline">{policy.type}</Badge></TableCell>
                        <TableCell>{getStatusBadge(policy.status)}</TableCell>
                        <TableCell className="max-w-md">{policy.description}</TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {policy.workspaces.map(w => (
                              <Badge key={w} variant="secondary" className="text-xs">{w}</Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{policy.created}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* API Keys */}
        <TabsContent value="api-keys">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>API Keys</CardTitle>
                <Button><Key className="h-4 w-4 mr-1" />Create Key</Button>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[500px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Provider</TableHead>
                      <TableHead>Scopes</TableHead>
                      <TableHead>Last Used</TableHead>
                      <TableHead>Expires</TableHead>
                      <TableHead>Status</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {MOCK_API_KEYS.map(key => (
                      <TableRow key={key.id}>
                        <TableCell className="font-medium">{key.name}</TableCell>
                        <TableCell><Badge variant="outline">{key.provider}</Badge></TableCell>
                        <TableCell>
                          <div className="flex flex-wrap gap-1">
                            {key.scopes.map(s => (
                              <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell className="font-mono text-xs">{key.lastUsed}</TableCell>
                        <TableCell className="font-mono text-xs">{key.expires}</TableCell>
                        <TableCell>{getStatusBadge(key.status)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Access Control */}
        <TabsContent value="access">
          <Card>
            <CardHeader>
              <CardTitle>Role-Based Access Control</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-4">
                  <h4 className="font-semibold">Admin</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• Full system access</li>
                    <li>• Manage users & roles</li>
                    <li>• Configure all integrations</li>
                    <li>• View all governance events</li>
                    <li>• Manage compliance policies</li>
                    <li>• Database route admin</li>
                  </ul>
                </div>
                <div className="space-y-4">
                  <h4 className="font-semibold">Editor</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• Create/edit agents</li>
                    <li>• Configure integrations</li>
                    <li>• View traces & costs</li>
                    <li>• Manage own API keys</li>
                    <li>• Read-only governance</li>
                  </ul>
                </div>
                <div className="space-y-4">
                  <h4 className="font-semibold">Viewer</h4>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li>• View dashboards</li>
                    <li>• Read-only traces</li>
                    <li>• View costs (own workspace)</li>
                    <li>• No configuration access</li>
                  </ul>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
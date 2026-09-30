"use client";

import { useState, useEffect } from "react";
import { Activity, DollarSign, Zap, AlertTriangle, CheckCircle, XCircle, TrendingUp, TrendingDown, Brain, Database, Server, Clock, Search, Filter, Download, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  title: string;
  value: string;
  change?: string;
  changeType?: "up" | "down" | "neutral";
  icon: React.ReactNode;
  description?: string;
}

function MetricCard({ title, value, change, changeType, icon, description }: MetricCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <div className="p-2 bg-primary/10 rounded-lg">{icon}</div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {change && (
          <p className={cn("text-xs mt-1", changeType === "up" ? "text-green-600" : changeType === "down" ? "text-red-600" : "text-muted-foreground")}>
            {changeType === "up" && <TrendingUp className="h-3 w-3 inline mr-1" />}
            {changeType === "down" && <TrendingDown className="h-3 w-3 inline mr-1" />}
            {change}
          </p>
        )}
        {description && <p className="text-xs text-muted-foreground">{description}</p>}
      </CardContent>
    </Card>
  );
}

interface TraceData {
  id: string;
  name: string;
  type: string;
  status: "success" | "error" | "running";
  duration: number;
  tokens: number;
  cost: number;
  timestamp: string;
}

interface CostData {
  provider: string;
  model: string;
  requests: number;
  tokens: number;
  cost: number;
  change: number;
}

interface HealthData {
  component: string;
  status: "healthy" | "degraded" | "error";
  latency: number;
  lastCheck: string;
}

interface GovernanceEvent {
  id: string;
  type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  timestamp: string;
  workspace: string;
}

const MOCK_TRACES: TraceData[] = [
  { id: "tr_1", name: "rag-query", type: "RAG Pipeline", status: "success", duration: 1245, tokens: 2340, cost: 0.0034, timestamp: "2024-01-15 10:30:45" },
  { id: "tr_2", name: "chat-completion", type: "Chat", status: "success", duration: 892, tokens: 1156, cost: 0.0012, timestamp: "2024-01-15 10:30:12" },
  { id: "tr_3", name: "tool-execution", type: "Tool", status: "error", duration: 3400, tokens: 0, cost: 0, timestamp: "2024-01-15 10:29:55" },
  { id: "tr_4", name: "embedding", type: "Embedding", status: "success", duration: 567, tokens: 892, cost: 0.0008, timestamp: "2024-01-15 10:29:30" },
  { id: "tr_5", name: "agent-workflow", type: "LangGraph", status: "running", duration: 4500, tokens: 4521, cost: 0.0089, timestamp: "2024-01-15 10:28:45" },
];

const MOCK_COSTS: CostData[] = [
  { provider: "openai", model: "gpt-4o", requests: 12450, tokens: 4500000, cost: 124.50, change: 12.3 },
  { provider: "openai", model: "gpt-4o-mini", requests: 8920, tokens: 2100000, cost: 12.40, change: -5.2 },
  { provider: "anthropic", model: "claude-3.5-sonnet", requests: 5600, tokens: 3200000, cost: 89.60, change: 8.7 },
  { provider: "groq", model: "llama-3.1-70b", requests: 23400, tokens: 8900000, cost: 0, change: 0 },
  { provider: "google", model: "gemini-1.5-pro", requests: 1200, tokens: 890000, cost: 18.90, change: -2.1 },
];

const MOCK_HEALTH: HealthData[] = [
  { component: "PostgreSQL (Checkpointer)", status: "healthy", latency: 12, lastCheck: "2s ago" },
  { component: "Qdrant (Vector Store)", status: "healthy", latency: 45, lastCheck: "3s ago" },
  { component: "Redis (Cache)", status: "healthy", latency: 3, lastCheck: "1s ago" },
  { component: "OpenAI API", status: "degraded", latency: 1200, lastCheck: "5s ago" },
  { component: "Anthropic API", status: "healthy", latency: 890, lastCheck: "4s ago" },
  { component: "LangGraph Server", status: "healthy", latency: 56, lastCheck: "2s ago" },
  { component: "E2B Sandbox", status: "error", latency: 0, lastCheck: "30s ago" },
];

const MOCK_EVENTS: GovernanceEvent[] = [
  { id: "evt_1", type: "COMPLIANCE_CHECK", severity: "info", message: "Data retention policy validated", timestamp: "2024-01-15 10:25:00", workspace: "prod" },
  { id: "evt_2", type: "ACCESS_GRANTED", severity: "info", message: "API key created for integration: tavily", timestamp: "2024-01-15 10:20:00", workspace: "prod" },
  { id: "evt_3", type: "RATE_LIMIT_EXCEEDED", severity: "warning", message: "Workspace 'dev' exceeded rate limit for openai", timestamp: "2024-01-15 10:15:00", workspace: "dev" },
  { id: "evt_4", type: "SCHEMA_DRIFT_DETECTED", severity: "critical", message: "Vector store schema mismatch: dimension 1536 vs 3072", timestamp: "2024-01-15 10:10:00", workspace: "staging" },
  { id: "evt_5", type: "COST_THRESHOLD", severity: "warning", message: "Monthly cost threshold 80% reached ($450/$500)", timestamp: "2024-01-15 10:05:00", workspace: "prod" },
];

export function ObservabilityDashboard() {
  const [timeRange, setTimeRange] = useState("1h");
  const [refreshInterval, setRefreshInterval] = useState(30000);
  const [autoRefresh, setAutoRefresh] = useState(true);

  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      // Refresh data
    }, refreshInterval);
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval]);

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      success: "default",
      error: "destructive",
      running: "secondary",
      healthy: "default",
      degraded: "secondary",
    };
    return <Badge variant={variants[status] || "outline"}>{status}</Badge>;
  };

  const getSeverityBadge = (severity: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      info: "default",
      warning: "secondary",
      critical: "destructive",
    };
    return <Badge variant={variants[severity] || "outline"}>{severity}</Badge>;
  };

  const formatCost = (cost: number) => `$${cost.toFixed(2)}`;
  const formatDuration = (ms: number) => `${ms}ms`;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Observability & Governance</h1>
          <p className="text-muted-foreground">Real-time monitoring, cost tracking, and compliance governance</p>
        </div>
        <div className="flex items-center gap-2">
          <Select value={timeRange} onValueChange={setTimeRange}>
            <SelectTrigger className="w-[140px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="5m">Last 5 minutes</SelectItem>
              <SelectItem value="15m">Last 15 minutes</SelectItem>
              <SelectItem value="1h">Last hour</SelectItem>
              <SelectItem value="24h">Last 24 hours</SelectItem>
              <SelectItem value="7d">Last 7 days</SelectItem>
              <SelectItem value="30d">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="auto-refresh"
              checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
              className="rounded border-input"
            />
            <label htmlFor="auto-refresh" className="text-sm">Auto-refresh</label>
            <Button variant="outline" size="icon" onClick={() => { /* manual refresh */ }}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Requests"
          value="28,452"
          change="+12.3%"
          changeType="up"
          icon={<Activity className="h-5 w-5 text-blue-600" />}
          description="vs previous hour"
        />
        <MetricCard
          title="Total Cost"
          value="$245.40"
          change="+8.7%"
          changeType="up"
          icon={<DollarSign className="h-5 w-5 text-green-600" />}
          description="Monthly spend"
        />
        <MetricCard
          title="Avg Latency"
          value="892ms"
          change="-5.2%"
          changeType="down"
          icon={<Zap className="h-5 w-5 text-yellow-600" />}
          description="p95 across all providers"
        />
        <MetricCard
          title="Error Rate"
          value="1.2%"
          change="+0.3%"
          changeType="up"
          icon={<AlertTriangle className="h-5 w-5 text-red-600" />}
          description="Requires attention"
        />
      </div>

      {/* Tabs */}
      <Tabs defaultValue="traces" className="space-y-4">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="traces"><Activity className="h-4 w-4 mr-2" />Traces</TabsTrigger>
          <TabsTrigger value="costs"><DollarSign className="h-4 w-4 mr-2" />Costs</TabsTrigger>
          <TabsTrigger value="health"><Server className="h-4 w-4 mr-2" />Health</TabsTrigger>
          <TabsTrigger value="governance"><Shield className="h-4 w-4 mr-2" />Governance</TabsTrigger>
        </TabsList>

        {/* Traces Tab */}
        <TabsContent value="traces">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Request Traces</CardTitle>
                <div className="flex items-center gap-2">
                  <Input placeholder="Search traces..." className="w-64" />
                  <Button variant="outline" size="sm"><Download className="h-4 w-4 mr-1" />Export</Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Trace ID</TableHead>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Tokens</TableHead>
                      <TableHead>Cost</TableHead>
                      <TableHead>Timestamp</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {MOCK_TRACES.map(trace => (
                      <TableRow key={trace.id}>
                        <TableCell className="font-mono text-xs">{trace.id}</TableCell>
                        <TableCell>{trace.name}</TableCell>
                        <TableCell>{trace.type}</TableCell>
                        <TableCell>{getStatusBadge(trace.status)}</TableCell>
                        <TableCell className="font-mono">{formatDuration(trace.duration)}</TableCell>
                        <TableCell className="font-mono">{trace.tokens.toLocaleString()}</TableCell>
                        <TableCell className="font-mono">{formatCost(trace.cost)}</TableCell>
                        <TableCell className="font-mono text-xs">{trace.timestamp}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Costs Tab */}
        <TabsContent value="costs">
          <Card>
            <CardHeader>
              <CardTitle>Cost Breakdown by Provider/Model</CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Provider</TableHead>
                      <TableHead>Model</TableHead>
                      <TableHead className="text-right">Requests</TableHead>
                      <TableHead className="text-right">Tokens</TableHead>
                      <TableHead className="text-right">Cost</TableHead>
                      <TableHead className="text-right">Change</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {MOCK_COSTS.map(cost => (
                      <TableRow key={`${cost.provider}-${cost.model}`}>
                        <TableCell><Badge variant="outline">{cost.provider}</Badge></TableCell>
                        <TableCell>{cost.model}</TableCell>
                        <TableCell className="text-right font-mono">{cost.requests.toLocaleString()}</TableCell>
                        <TableCell className="text-right font-mono">{(cost.tokens / 1000000).toFixed(1)}M</TableCell>
                        <TableCell className="text-right font-mono font-medium">{formatCost(cost.cost)}</TableCell>
                        <TableCell className="text-right">
                          <span className={cost.change > 0 ? "text-red-600" : "text-green-600"}>
                            {cost.change > 0 ? "+" : ""}{cost.change.toFixed(1)}%
                          </span>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Health Tab */}
        <TabsContent value="health">
          <Card>
            <CardHeader>
              <CardTitle>Component Health</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {MOCK_HEALTH.map(comp => (
                  <Card key={comp.component} className="border-l-4 border-l-primary">
                    <CardContent className="pt-4">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium">{comp.component}</h4>
                        {getStatusBadge(comp.status)}
                      </div>
                      <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Zap className="h-3 w-3" />
                          {comp.latency}ms
                        </span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {comp.lastCheck}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Governance Tab */}
        <TabsContent value="governance">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>Governance Events</CardTitle>
                <Badge variant="secondary">5 events in last hour</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Event</TableHead>
                      <TableHead>Severity</TableHead>
                      <TableHead>Message</TableHead>
                      <TableHead>Workspace</TableHead>
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
                        <TableCell className="font-mono text-xs">{event.timestamp}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </ScrollArea>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// Need to import Shield icon
import { Shield } from "lucide-react";
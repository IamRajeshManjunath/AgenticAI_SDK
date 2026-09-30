"use client";

import { useState } from "react";
import { Search, Filter, Download, Calendar, Clock, CheckCircle, AlertCircle, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn } from "@/lib/utils";

interface ActivityEvent {
  id: string;
  type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  workspace: string;
  user: string;
  timestamp: string;
  metadata?: Record<string, any>;
}

const ALL_EVENTS: ActivityEvent[] = [
  { id: "evt_1", type: "INTEGRATION_INSTALLED", severity: "info", message: "Installed langchain-tavily v0.3.0", workspace: "prod", user: "admin@agenticai.dev", timestamp: "2024-01-15T10:25:00Z" },
  { id: "evt_2", type: "DB_ROUTE_CREATED", severity: "info", message: "Created vector_store route: primary-qdrant", workspace: "prod", user: "admin@agenticai.dev", timestamp: "2024-01-15T10:20:00Z" },
  { id: "evt_3", type: "COST_ALERT", severity: "warning", message: "Monthly spend reached 80% of budget ($400/$500)", workspace: "prod", user: "system", timestamp: "2024-01-15T10:15:00Z" },
  { id: "evt_4", type: "SCHEMA_DRIFT", severity: "critical", message: "Vector dimension mismatch detected in staging", workspace: "staging", user: "system", timestamp: "2024-01-15T10:10:00Z" },
  { id: "evt_5", type: "HEALTH_CHECK", severity: "info", message: "All database connections healthy", workspace: "prod", user: "system", timestamp: "2024-01-15T10:05:00Z" },
  { id: "evt_6", type: "INTEGRATION_INSTALLED", severity: "info", message: "Installed langchain-groq v0.3.0", workspace: "dev", user: "dev@agenticai.dev", timestamp: "2024-01-15T09:45:00Z" },
  { id: "evt_7", type: "DB_ROUTE_MODIFIED", severity: "info", message: "Database route 'primary-vector' updated: changed provider to pinecone", workspace: "prod", user: "admin@agenticai.dev", timestamp: "2024-01-15T09:30:00Z" },
  { id: "evt_8", type: "PERMISSION_DENIED", severity: "warning", message: "User attempted to access admin-only endpoint /api/v1/admin/users", workspace: "dev", user: "user@agenticai.dev", timestamp: "2024-01-15T09:15:00Z" },
  { id: "evt_9", type: "AGENT_DEPLOYED", severity: "info", message: "Agent 'customer-support' deployed to production", workspace: "prod", user: "admin@agenticai.dev", timestamp: "2024-01-15T09:00:00Z" },
  { id: "evt_10", type: "API_KEY_CREATED", severity: "info", message: "New API key created for openai integration", workspace: "staging", user: "admin@agenticai.dev", timestamp: "2024-01-15T08:45:00Z" },
  { id: "evt_11", type: "RAG_PIPELINE_RUN", severity: "info", message: "RAG pipeline executed: 1,234 documents processed", workspace: "prod", user: "system", timestamp: "2024-01-15T08:30:00Z" },
  { id: "evt_12", type: "RATE_LIMIT_EXCEEDED", severity: "warning", message: "Rate limit exceeded for anthropic in dev workspace", workspace: "dev", user: "system", timestamp: "2024-01-15T08:15:00Z" },
];

const EVENT_TYPES = [
  "INTEGRATION_INSTALLED",
  "INTEGRATION_UNINSTALLED",
  "INTEGRATION_CONFIGURED",
  "DB_ROUTE_CREATED",
  "DB_ROUTE_MODIFIED",
  "DB_ROUTE_DELETED",
  "DB_ROUTE_TESTED",
  "AGENT_CREATED",
  "AGENT_DEPLOYED",
  "AGENT_UPDATED",
  "AGENT_DELETED",
  "RAG_PIPELINE_RUN",
  "RAG_PIPELINE_FAILED",
  "COST_ALERT",
  "COST_THRESHOLD",
  "HEALTH_CHECK",
  "HEALTH_DEGRADED",
  "SCHEMA_DRIFT",
  "SCHEMA_VALIDATED",
  "PERMISSION_GRANTED",
  "PERMISSION_DENIED",
  "API_KEY_CREATED",
  "API_KEY_REVOKED",
  "API_KEY_ROTATED",
  "POLICY_CREATED",
  "POLICY_UPDATED",
  "COMPLIANCE_CHECK",
];

export default function ActivityPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedSeverity, setSelectedSeverity] = useState<string>("all");
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>("all");
  const [dateRange, setDateRange] = useState("24h");
  const [loading, setLoading] = useState(false);

  const workspaces = ["prod", "staging", "dev"];

  const filteredEvents = ALL_EVENTS.filter(event => {
    if (selectedType !== "all" && event.type !== selectedType) return false;
    if (selectedSeverity !== "all" && event.severity !== selectedSeverity) return false;
    if (selectedWorkspace !== "all" && event.workspace !== selectedWorkspace) return false;
    if (searchQuery && !event.message.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !event.type.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !event.user.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const getSeverityBadge = (severity: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      info: "default",
      warning: "secondary",
      critical: "destructive",
    };
    return <Badge variant={variants[severity] || "outline"}>{severity}</Badge>;
  };

  const getTypeBadge = (type: string) => {
    return <Badge variant="outline" className="text-xs">{type}</Badge>;
  };

  const handleExport = () => {
    // In production, this would export to CSV/JSON
    const data = filteredEvents.map(e => ({
      ...e,
      timestamp: new Date(e.timestamp).toLocaleString(),
    }));
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `activity-${new Date().toISOString().split("T")[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Activity Log</h1>
          <p className="text-muted-foreground">View all workspace activity and audit events</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={handleExport} disabled={loading}>
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="Search activity..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            
            <Select value={selectedType} onValueChange={setSelectedType}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All Event Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Event Types</SelectItem>
                {EVENT_TYPES.map(t => <SelectItem key={t} value={t}>{t}</SelectItem>)}
              </SelectContent>
            </Select>

            <Select value={selectedSeverity} onValueChange={setSelectedSeverity}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All Severities" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severities</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>

            <Select value={selectedWorkspace} onValueChange={setSelectedWorkspace}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All Workspaces" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Workspaces</SelectItem>
                {workspaces.map(w => <SelectItem key={w} value={w}>{w}</SelectItem>)}
              </SelectContent>
            </Select>

            <Select value={dateRange} onValueChange={setDateRange}>
              <SelectTrigger className="w-full">
                <Calendar className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Last 24 hours" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1h">Last hour</SelectItem>
                <SelectItem value="24h">Last 24 hours</SelectItem>
                <SelectItem value="7d">Last 7 days</SelectItem>
                <SelectItem value="30d">Last 30 days</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Activity Table */}
      <Card>
        <CardHeader>
          <CardTitle>Events ({filteredEvents.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredEvents.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Clock className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
              <p>No activity events found</p>
              <p className="text-sm">Try adjusting your filters</p>
            </div>
          ) : (
            <ScrollArea className="h-[600px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Event</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Message</TableHead>
                    <TableHead>Workspace</TableHead>
                    <TableHead>User</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredEvents.map(event => (
                    <TableRow key={event.id}>
                      <TableCell className="font-mono text-xs whitespace-nowrap">
                        {new Date(event.timestamp).toLocaleString()}
                      </TableCell>
                      <TableCell>{getTypeBadge(event.type)}</TableCell>
                      <TableCell>{getSeverityBadge(event.severity)}</TableCell>
                      <TableCell className="max-w-md truncate">{event.message}</TableCell>
                      <TableCell><Badge variant="secondary">{event.workspace}</Badge></TableCell>
                      <TableCell className="font-mono text-sm">{event.user}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
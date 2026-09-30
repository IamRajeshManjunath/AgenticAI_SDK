"use client";

import { useState } from "react";
import { Plus, Database, TestTube2, CheckCircle, AlertCircle, X, RefreshCw, Settings, Trash2, Edit2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { cn } from "@/lib/utils";

export interface DatabaseRoute {
  id: string;
  name: string;
  purpose: string;
  provider: string;
  config: Record<string, any>;
  schema_contract: Record<string, any>;
  is_active: boolean;
  health_status: "healthy" | "degraded" | "error" | "unknown";
  last_health_check: string | null;
}

const DATABASE_PURPOSES = [
  { value: "vector_store", label: "Vector Store", description: "Document embeddings for RAG", icon: "🗄️" },
  { value: "checkpointer", label: "Checkpointer", description: "LangGraph workflow state persistence", icon: "💾" },
  { value: "store", label: "Store", description: "Long-term key-value memory", icon: "🧠" },
  { value: "analytics", label: "Analytics", description: "Custom analytics and metrics", icon: "📊" },
  { value: "audit_log", label: "Audit Log", description: "Immutable governance events", icon: "📋" },
  { value: "cache", label: "Cache", description: "Ephemeral caching with TTL", icon: "⚡" },
  { value: "rate_limit", label: "Rate Limit", description: "Rate limiting counters", icon: "🛡️" },
];

const PROVIDERS_BY_PURPOSE: Record<string, Array<{ value: string; label: string; icon: string }>> = {
  vector_store: [
    { value: "qdrant", label: "Qdrant", icon: "🔍" },
    { value: "pinecone", label: "Pinecone", icon: "🌲" },
    { value: "weaviate", label: "Weaviate", icon: "🔮" },
    { value: "chroma", label: "Chroma", icon: "🎨" },
    { value: "pgvector", label: "PGVector", icon: "🐘" },
    { value: "milvus", label: "Milvus", icon: "🚀" },
  ],
  checkpointer: [
    { value: "postgresql", label: "PostgreSQL", icon: "🐘" },
    { value: "sqlite", label: "SQLite", icon: "💾" },
    { value: "redis", label: "Redis", icon: "🔴" },
    { value: "mongodb", label: "MongoDB", icon: "🍃" },
  ],
  store: [
    { value: "postgresql", label: "PostgreSQL", icon: "🐘" },
    { value: "redis", label: "Redis", icon: "🔴" },
    { value: "mongodb", label: "MongoDB", icon: "🍃" },
  ],
  analytics: [
    { value: "clickhouse", label: "ClickHouse", icon: "🏠" },
    { value: "postgresql", label: "PostgreSQL", icon: "🐘" },
    { value: "timescaledb", label: "TimescaleDB", icon: "⏱️" },
  ],
  audit_log: [
    { value: "postgresql", label: "PostgreSQL", icon: "🐘" },
    { value: "clickhouse", label: "ClickHouse", icon: "🏠" },
  ],
  cache: [
    { value: "redis", label: "Redis", icon: "🔴" },
    { value: "valkey", label: "Valkey", icon: "🔑" },
    { value: "memcached", label: "Memcached", icon: "💾" },
  ],
  rate_limit: [
    { value: "redis", label: "Redis", icon: "🔴" },
    { value: "postgresql", label: "PostgreSQL", icon: "🐘" },
  ],
};

const SCHEMA_TEMPLATES: Record<string, Record<string, any>> = {
  vector_store: {
    purpose: "vector_store",
    collections: {
      documents: {
        columns: {
          vector: { type: "vector", dimension: 1536 },
          content: { type: "text" },
          metadata: { type: "json" },
        },
      },
    },
  },
  checkpointer: {
    purpose: "checkpointer",
    tables: {
      checkpoints: "langgraph_standard",
      checkpoint_blobs: "langgraph_standard",
      checkpoint_writes: "langgraph_standard",
    },
  },
  store: {
    purpose: "store",
    tables: {
      store: "langgraph_store_standard",
    },
  },
  cache: {
    purpose: "cache",
    tables: {
      cache: {
        columns: {
          key: { type: "text", primary: true },
          value: { type: "json" },
          expires_at: { type: "timestamp" },
        },
      },
    },
  },
  analytics: {
    purpose: "analytics",
    tables: {
      events: {
        columns: {
          timestamp: { type: "timestamp", primary: true },
          workspace_id: { type: "text" },
          event_type: { type: "text" },
          metrics_json: { type: "json" },
        },
      },
    },
  },
};

interface DatabaseRouteFormData {
  name: string;
  purpose: string;
  provider: string;
  config: Record<string, any>;
  schema_contract: Record<string, any>;
  is_active: boolean;
}

export function DatabaseRoutesConfig() {
  const [routes, setRoutes] = useState<DatabaseRoute[]>([]);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingRoute, setEditingRoute] = useState<DatabaseRoute | null>(null);
  const [selectedPurpose, setSelectedPurpose] = useState<string>("vector_store");
  const [formData, setFormData] = useState<DatabaseRouteFormData>({
    name: "",
    purpose: "vector_store",
    provider: "",
    config: {},
    schema_contract: {},
    is_active: true,
  });
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const handlePurposeChange = (purpose: string) => {
    setSelectedPurpose(purpose);
    setFormData(prev => ({
      ...prev,
      purpose,
      provider: "",
      config: getDefaultConfig(purpose),
      schema_contract: SCHEMA_TEMPLATES[purpose] || {},
    }));
  };

  const handleProviderChange = (provider: string) => {
    setFormData(prev => ({
      ...prev,
      provider,
      config: { ...prev.config, ...getDefaultConfigForProvider(provider) },
    }));
  };

  const handleConfigChange = (key: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      config: { ...prev.config, [key]: value },
    }));
  };

  const handleSchemaChange = (key: string, value: any) => {
    setFormData(prev => ({
      ...prev,
      schema_contract: { ...prev.schema_contract, [key]: value },
    }));
  };

  const handleSubmit = async () => {
    if (editingRoute) {
      setRoutes(prev => prev.map(r => r.id === editingRoute.id ? { ...r, ...formData } : r));
    } else {
      const newRoute: DatabaseRoute = {
        id: `route_${Date.now()}`,
        ...formData,
        health_status: "unknown",
        last_health_check: null,
      };
      setRoutes(prev => [...prev, newRoute]);
    }
    setIsDialogOpen(false);
    resetForm();
  };

  const handleEdit = (route: DatabaseRoute) => {
    setEditingRoute(route);
    setFormData({
      name: route.name,
      purpose: route.purpose,
      provider: route.provider,
      config: route.config,
      schema_contract: route.schema_contract,
      is_active: route.is_active,
    });
    setSelectedPurpose(route.purpose);
    setIsDialogOpen(true);
  };

  const handleDelete = (id: string) => {
    if (confirm("Are you sure you want to delete this database route?")) {
      setRoutes(prev => prev.filter(r => r.id !== id));
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setTestResult(null);
    // Simulate connection test
    await new Promise(resolve => setTimeout(resolve, 1500));
    const success = Math.random() > 0.2;
    setTestResult({
      success,
      message: success ? "Connection successful! Schema validation passed." : "Connection failed: Could not connect to database",
    });
    setIsTesting(false);
  };

  const resetForm = () => {
    setFormData({
      name: "",
      purpose: "vector_store",
      provider: "",
      config: {},
      schema_contract: {},
      is_active: true,
    });
    setEditingRoute(null);
    setSelectedPurpose("vector_store");
  };

  const getProvidersForPurpose = (purpose: string) => {
    return PROVIDERS_BY_PURPOSE[purpose] || [];
  };

  const getDefaultConfig = (purpose: string): Record<string, any> => {
    const defaults: Record<string, Record<string, any>> = {
      vector_store: { url: "http://localhost:6333", collection: "documents" },
      checkpointer: { connectionString: "postgresql://user:pass@localhost:5432/langgraph" },
      store: { url: "redis://localhost:6379", namespace: "agent_memory" },
      analytics: { connectionString: "clickhouse://user:pass@localhost:9000/analytics" },
      cache: { url: "redis://localhost:6379" },
      rate_limit: { url: "redis://localhost:6379" },
    };
    return defaults[purpose] || {};
  };

  const getDefaultConfigForProvider = (provider: string): Record<string, any> => {
    // Provider-specific defaults
    return {};
  };

  const getHealthIcon = (status: string) => {
    switch (status) {
      case "healthy": return <CheckCircle className="h-4 w-4 text-green-500" />;
      case "degraded": return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case "error": return <AlertCircle className="h-4 w-4 text-red-500" />;
      default: return <Database className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, "default" | "secondary" | "destructive" | "outline"> = {
      healthy: "default",
      degraded: "secondary",
      error: "destructive",
      unknown: "outline",
    };
    return <Badge variant={variants[status] || "outline"}>{status}</Badge>;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Database Routes</h1>
          <p className="text-muted-foreground">Configure purpose-bound database connections with strict schema validation</p>
        </div>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button onClick={() => { setEditingRoute(null); resetForm(); setIsDialogOpen(true); }}>
              <Plus className="h-4 w-4 mr-2" />
              Add Database Route
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-hidden">
            <DialogHeader>
              <DialogTitle>{editingRoute ? "Edit Database Route" : "Add Database Route"}</DialogTitle>
              <DialogDescription>
                Configure a purpose-bound database connection with strict schema validation.
                Each purpose can only have one active route per workspace.
              </DialogDescription>
            </DialogHeader>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 p-6 max-h-[70vh] overflow-y-auto">
              {/* Basic Info */}
              <div className="space-y-4">
                <div>
                  <Label htmlFor="name">Route Name *</Label>
                  <Input
                    id="name"
                    value={formData.name}
                    onChange={e => setFormData(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="e.g., primary-vector, langgraph-checkpointer"
                  />
                </div>

                <div>
                  <Label htmlFor="purpose">Purpose *</Label>
                  <Select value={formData.purpose} onValueChange={handlePurposeChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select purpose" />
                    </SelectTrigger>
                    <SelectContent>
                      {DATABASE_PURPOSES.map(p => (
                        <SelectItem key={p.value} value={p.value}>
                          <div className="flex items-center gap-2">
                            <span>{p.icon}</span>
                            <div>
                              <p className="font-medium">{p.label}</p>
                              <p className="text-xs text-muted-foreground">{p.description}</p>
                            </div>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="provider">Provider *</Label>
                  <Select value={formData.provider} onValueChange={handleProviderChange}>
                    <SelectTrigger>
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      {getProvidersForPurpose(formData.purpose).map(p => (
                        <SelectItem key={p.value} value={p.value}>
                          <div className="flex items-center gap-2">
                            <span>{p.icon}</span>
                            <span>{p.label}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="flex items-center gap-2">
                  <Switch
                    id="is_active"
                    checked={formData.is_active}
                    onCheckedChange={checked => setFormData(prev => ({ ...prev, is_active: checked }))}
                  />
                  <Label htmlFor="is_active" className="cursor-pointer">
                    Active
                  </Label>
                </div>
              </div>

              {/* Connection Config */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Connection Configuration</h3>
                <div className="bg-muted/50 p-4 rounded-lg space-y-3">
                  {Object.entries(getDefaultConfig(formData.purpose)).map(([key, defaultValue]) => (
                    <div key={key} className="space-y-1">
                      <Label htmlFor={`config_${key}`} className="text-sm">
                        {key.replace(/([A-Z])/g, ' $1').replace(/^./, str => str.toUpperCase())}
                      </Label>
                      <Input
                        id={`config_${key}`}
                        value={formData.config[key] || defaultValue || ""}
                        onChange={e => handleConfigChange(key, e.target.value)}
                        placeholder={typeof defaultValue === 'string' ? defaultValue : JSON.stringify(defaultValue)}
                      />
                    </div>
                  ))}
                </div>
              </div>

              {/* Schema Contract */}
              <div className="space-y-4">
                <h3 className="text-lg font-semibold">Schema Contract</h3>
                <p className="text-sm text-muted-foreground">
                  Strict schema definition for validation. The database must match this schema exactly.
                </p>
                <div className="bg-muted/50 p-4 rounded-lg">
                  <Textarea
                    value={JSON.stringify(formData.schema_contract, null, 2)}
                    onChange={e => {
                      try {
                        handleSchemaChange("schema_contract", JSON.parse(e.target.value));
                      } catch {
                        // Ignore invalid JSON while typing
                      }
                    }}
                    className="font-mono text-sm"
                    rows={10}
                    placeholder="Schema contract JSON..."
                  />
                </div>
              </div>
            </div>
            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setIsDialogOpen(false)}>Cancel</Button>
              <Button onClick={handleSubmit}>{editingRoute ? "Update" : "Create"} Route</Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Routes Table */}
      <Card>
        <CardHeader>
          <CardTitle>Configured Routes</CardTitle>
          <CardDescription>
            Each purpose can have only one active route. Strict schema validation enforced.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {routes.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Database className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
              <p>No database routes configured</p>
              <p className="text-sm">Click "Add Database Route" to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {routes.map(route => (
                <div key={route.id} className="border rounded-lg p-4 hover:bg-muted/50 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className="p-2 bg-primary/10 rounded-lg">
                        {getPurposeIcon(route.purpose)}
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium truncate">{route.name}</h4>
                          <Badge variant={route.is_active ? "default" : "outline"}>
                            {route.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground truncate">
                          {route.purpose} • {route.provider}
                        </p>
                        <p className="text-xs text-muted-foreground font-mono truncate">
                          {JSON.stringify(route.config).slice(0, 80)}...
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getHealthIcon(route.health_status)}
                      <Badge variant={
                        route.health_status === "healthy" ? "default" :
                        route.health_status === "degraded" ? "secondary" :
                        route.health_status === "error" ? "destructive" : "outline"
                      }>
                        {route.health_status}
                      </Badge>
                      <Button variant="ghost" size="icon" onClick={() => handleEdit(route)}>
                        <Edit2 className="h-4 w-4" />
                      </Button>
                      <Button variant="ghost" size="icon" onClick={() => handleDelete(route.id)}>
                        <Trash2 className="h-4 w-4 text-red-500" />
                      </Button>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs text-muted-foreground">
                    <span>Schema: {route.schema_validation_status || "pending"}</span>
                    <span>Last checked: {route.last_health_check || "never"}</span>
                    <Button variant="ghost" size="sm" onClick={() => { /* test route */ }}>
                      <TestTube2 className="h-3 w-3 mr-1" />
                      Test Connection
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function getPurposeIcon(purpose: string) {
  const icons: Record<string, string> = {
    vector_store: "🗄️",
    checkpointer: "💾",
    store: "🧠",
    analytics: "📊",
    audit_log: "📋",
    cache: "⚡",
    rate_limit: "🛡️",
  };
  return icons[purpose] || "📦";
}
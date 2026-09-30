"use client";

import { useState } from "react";
import { Search, Download, Check, ExternalLink, Filter, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";

export interface IntegrationPlugin {
  type: string;
  provider: string;
  name: string;
  description: string;
  package_name: string;
  version: string;
  features: {
    stream: boolean;
    tools: boolean;
    structured_output: boolean;
    multimodal: boolean;
  };
  docs_url: string;
  downloads_per_month: number;
  tags: string[];
  installed: boolean;
}

const INTEGRATION_TYPES = [
  { value: "chat_model", label: "Chat Models", icon: "💬" },
  { value: "tool", label: "Tools", icon: "🔧" },
  { value: "vector_store", label: "Vector Stores", icon: "🗄️" },
  { value: "embedding", label: "Embeddings", icon: "🔢" },
  { type: "retriever", label: "Retrievers", icon: "🔍" },
  { value: "sandbox", label: "Sandboxes", icon: "🏖️" },
  { value: "checkpointer", label: "Checkpointers", icon: "💾" },
  { value: "store", label: "Stores", icon: "🧠" },
  { value: "middleware", label: "Middleware", icon: "⚙️" },
  { value: "backend", label: "Backends", icon: "🔄" },
];

// Mock data - in production this would come from API
const MOCK_PLUGINS: IntegrationPlugin[] = [
  {
    type: "chat_model",
    provider: "openai",
    name: "OpenAI",
    description: "OpenAI chat models (GPT-4o, GPT-4, GPT-3.5)",
    package_name: "langchain-openai",
    version: "0.3.0",
    features: { stream: true, tools: true, structured_output: true, multimodal: true },
    docs_url: "https://docs.langchain.com/oss/python/integrations/chat/openai",
    downloads_per_month: 64000000,
    tags: ["openai", "gpt", "chat", "multimodal"],
    installed: true,
  },
  {
    type: "chat_model",
    provider: "anthropic",
    name: "Anthropic",
    description: "Anthropic chat models (Claude 3.5 Sonnet, Claude 3 Opus)",
    package_name: "langchain-anthropic",
    version: "0.3.0",
    features: { stream: true, tools: true, structured_output: true, multimodal: true },
    docs_url: "https://docs.langchain.com/oss/python/integrations/chat/anthropic",
    downloads_per_month: 22000000,
    tags: ["anthropic", "claude", "chat", "multimodal"],
    installed: true,
  },
  {
    type: "chat_model",
    provider: "groq",
    name: "Groq",
    description: "Groq fast inference (Llama, Mixtral, Gemma)",
    package_name: "langchain-groq",
    version: "0.3.0",
    features: { stream: true, tools: true, structured_output: true, multimodal: false },
    docs_url: "https://docs.langchain.com/oss/python/integrations/chat/groq",
    downloads_per_month: 2000000,
    tags: ["groq", "llama", "mixtral", "fast", "inference"],
    installed: false,
  },
  {
    type: "tool",
    provider: "tavily",
    name: "Tavily Search",
    description: "Tavily AI-powered search API",
    package_name: "langchain-tavily",
    version: "0.3.0",
    features: { stream: false, tools: true, structured_output: true, multimodal: false },
    docs_url: "https://docs.langchain.com/oss/python/integrations/tools/tavily_search",
    downloads_per_month: 645000,
    tags: ["tavily", "search", "web", "research"],
    installed: true,
  },
  {
    type: "tool",
    provider: "composio",
    name: "Composio",
    description: "Composio integration platform (500+ tools: GitHub, Slack, Jira, Notion, Salesforce, etc.)",
    package_name: "langchain-composio",
    version: "0.3.0",
    features: { stream: false, tools: true, structured_output: true, multimodal: false },
    docs_url: "https://docs.langchain.com/oss/python/integrations/tools/composio",
    downloads_per_month: 301000,
    tags: ["composio", "integration-platform", "github", "slack", "jira", "500+"],
    installed: false,
  },
  {
    type: "vector_store",
    provider: "qdrant",
    name: "Qdrant",
    description: "Qdrant vector database for similarity search",
    package_name: "langchain-qdrant",
    version: "0.3.0",
    features: { stream: false, tools: false, structured_output: false, multimodal: false },
    docs_url: "https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant",
    downloads_per_month: 765000,
    tags: ["qdrant", "vector", "database", "search", "rag"],
    installed: true,
  },
  {
    type: "sandbox",
    provider: "e2b",
    name: "E2B",
    description: "E2B secure code interpreter sandbox",
    package_name: "langchain-e2b",
    version: "0.3.0",
    features: { stream: false, tools: true, structured_output: false, multimodal: false },
    docs_url: "https://docs.langchain.com/oss/python/integrations/sandboxes/e2b",
    downloads_per_month: 13000,
    tags: ["e2b", "sandbox", "code-interpreter", "secure"],
    installed: false,
  },
];

export function IntegrationMarketplace() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedTags, setSelectedTags] = useState<string[]>([]);
  const [showOnlyInstalled, setShowOnlyInstalled] = useState(false);
  const [selectedPlugin, setSelectedPlugin] = useState<IntegrationPlugin | null>(null);

  const allTags = Array.from(
    new Set(MOCK_PLUGINS.flatMap(p => p.tags))
  ).sort();

  const filteredPlugins = MOCK_PLUGINS.filter(plugin => {
    if (selectedType !== "all" && plugin.type !== selectedType) return false;
    if (showOnlyInstalled && !plugin.installed) return false;
    if (selectedTags.length > 0 && !selectedTags.some(tag => plugin.tags.includes(tag))) return false;
    if (searchQuery && !plugin.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !plugin.description.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleInstall = async (plugin: IntegrationPlugin) => {
    // In production, this would call the API to install the plugin
    console.log(`Installing ${plugin.name}...`);
    // Simulate install
    plugin.installed = true;
  };

  const handleUninstall = async (plugin: IntegrationPlugin) => {
    console.log(`Uninstalling ${plugin.name}...`);
    plugin.installed = false;
  };

  const handleConfigure = (plugin: IntegrationPlugin) => {
    setSelectedPlugin(plugin);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Integration Marketplace</h1>
          <p className="text-muted-foreground">Discover, install, and configure integrations for your agents</p>
        </div>
        <Button className="gap-2" onClick={() => setShowOnlyInstalled(!showOnlyInstalled)}>
          {showOnlyInstalled ? "Show All" : "Installed Only"}
        </Button>
      </div>

      {/* Filters */}
      <Card className="border-border">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="Search integrations..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            
            <Select value={selectedType} onValueChange={setSelectedType}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="All Types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Types</SelectItem>
                {INTEGRATION_TYPES.map(t => (
                  <SelectItem key={t.value} value={t.value}>
                    {t.icon} {t.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select multiple value={selectedTags} onValueChange={setSelectedTags}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Filter by tags" />
              </SelectTrigger>
              <SelectContent>
                {allTags.map(tag => (
                  <SelectItem key={tag} value={tag}>
                    {tag}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <label className="flex items-center gap-2">
              <Checkbox
                checked={showOnlyInstalled}
                onCheckedChange={setShowOnlyInstalled}
              />
              <span className="text-sm font-medium">Installed only</span>
            </label>
          </div>
        </CardContent>
      </Card>

      {/* Plugin Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredPlugins.map(plugin => (
          <IntegrationCard
            key={`${plugin.type}:${plugin.provider}`}
            plugin={plugin}
            onInstall={handleInstall}
            onUninstall={handleUninstall}
            onConfigure={handleConfigure}
          />
        ))}
      </div>

      {filteredPlugins.length === 0 && (
        <div className="text-center py-12 text-muted-foreground">
          <p>No integrations found matching your filters</p>
        </div>
      )}

      {/* Configuration Modal */}
      {selectedPlugin && (
        <IntegrationConfigModal
          plugin={selectedPlugin}
          onClose={() => setSelectedPlugin(null)}
        />
      )}
    </div>
  );
}

function IntegrationCard({
  plugin,
  onInstall,
  onUninstall,
  onConfigure,
}: {
  plugin: IntegrationPlugin;
  onInstall: (p: IntegrationPlugin) => void;
  onUninstall: (p: IntegrationPlugin) => void;
  onConfigure: (p: IntegrationPlugin) => void;
}) {
  const features = Object.entries(plugin.features)
    .filter(([, v]) => v)
    .map(([k]) => k);

  return (
    <Card className="border-border hover:border-primary/50 transition-colors">
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg">
              {getTypeIcon(plugin.type)}
            </div>
            <div>
              <CardTitle className="text-lg">{plugin.name}</CardTitle>
              <p className="text-sm text-muted-foreground">{plugin.provider}</p>
            </div>
          </div>
          {plugin.installed ? (
            <Badge variant="secondary" className="gap-1">
              <Check className="h-3 w-3" />
              Installed
            </Badge>
          ) : (
            <Badge variant="outline">Available</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground line-clamp-2">{plugin.description}</p>
        
        <div className="flex flex-wrap gap-1">
          {plugin.tags.slice(0, 4).map(tag => (
            <Badge key={tag} variant="outline" className="text-xs">
              {tag}
            </Badge>
          ))}
          {plugin.tags.length > 4 && (
            <Badge variant="outline" className="text-xs">
              +{plugin.tags.length - 4} more
            </Badge>
          )}
        </div>

        <div className="flex flex-wrap gap-1">
          {features.map(feature => (
            <Badge key={feature} variant="secondary" className="text-xs gap-1">
              {getFeatureIcon(feature)}
              {feature.replace("_", " ")}
            </Badge>
          ))}
        </div>

        <div className="flex items-center justify-between pt-2 border-t">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>{plugin.package_name}@v{plugin.version}</span>
            <Separator orientation="vertical" className="h-3" />
            <span>{formatDownloads(plugin.downloads_per_month)}/mo</span>
          </div>
          
          <div className="flex items-center gap-2">
            {plugin.installed ? (
              <>
                <Button variant="outline" size="sm" onClick={() => onConfigure(plugin)}>
                  Configure
                </Button>
                <Button variant="ghost" size="sm" onClick={() => onUninstall(plugin)}>
                  Uninstall
                </Button>
              </>
            ) : (
              <Button size="sm" onClick={() => onInstall(plugin)}>
                <Download className="h-3 w-3 mr-1" />
                Install
              </Button>
            )}
            <Button variant="ghost" size="icon" onClick={() => window.open(plugin.docs_url, "_blank")}>
              <ExternalLink className="h-3 w-3" />
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function IntegrationConfigModal({
  plugin,
  onClose,
}: {
  plugin: IntegrationPlugin;
  onClose: () => void;
}) {
  // In production, this would show a dynamic form based on plugin's config_schema
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-background rounded-lg shadow-xl max-w-2xl w-full mx-4 max-h-[90vh] overflow-hidden">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-xl font-semibold">Configure {plugin.name}</h2>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        <div className="p-6 space-y-4 max-h-[60vh] overflow-y-auto">
          <p className="text-muted-foreground">
            Configuration form for {plugin.name} would be generated here based on the plugin's config schema.
            This would include fields for API keys, model selection, feature toggles, etc.
          </p>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">API Key</label>
              <Input type="password" placeholder="Enter API key" />
              <p className="text-xs text-muted-foreground">Stored securely in encrypted secrets store</p>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium mb-1">Model</label>
                <Select>
                  <SelectTrigger>
                    <SelectValue placeholder="Select model" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                    <SelectItem value="gpt-4o-mini">GPT-4o Mini</SelectItem>
                    <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Temperature</label>
                <Input type="number" step="0.1" min="0" max="2" defaultValue="0.7" />
              </div>
            </div>
            
            <div className="flex items-center gap-2">
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" defaultChecked />
                <span className="text-sm">Enable Streaming</span>
              </label>
              <label className="flex items-center gap-2">
                <input type="checkbox" className="rounded" defaultChecked />
                <span className="text-sm">Enable Tools</span>
              </label>
            </div>
          </div>
        </div>
        <div className="flex justify-end gap-2 p-4 border-t">
          <Button variant="outline" onClick={onClose}>Cancel</Button>
          <Button onClick={onClose}>Save Configuration</Button>
        </div>
      </div>
    </div>
  );
}

function getTypeIcon(type: string) {
  const icons: Record<string, string> = {
    chat_model: "💬",
    tool: "🔧",
    vector_store: "🗄️",
    embedding: "🔢",
    retriever: "🔍",
    sandbox: "🏖️",
    checkpointer: "💾",
    store: "🧠",
    middleware: "⚙️",
    backend: "🔄",
  };
  return icons[type] || "📦";
}

function getFeatureIcon(feature: string) {
  const icons: Record<string, string> = {
    stream: "🌊",
    tools: "🔧",
    structured_output: "📋",
    multimodal: "🖼️",
  };
  return icons[feature] || "✨";
}

function formatDownloads(num: number): string {
  if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
  return num.toString();
}
'use client'

import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Slider } from '@/components/ui/slider'
import {
  ChevronUp,
  ChevronDown,
  Plus,
  Trash2,
  Wrench,
  Database,
  Globe,
  Server,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkflowStore } from '@/lib/store'
import type { ToolConfig, RAGSourceConfig } from '@/lib/types'

export function RegistryDrawer() {
  const {
    globalTools,
    globalRAGSources,
    registryDrawerOpen,
    toggleRegistryDrawer,
    addGlobalTool,
    updateGlobalTool,
    deleteGlobalTool,
    addGlobalRAGSource,
    updateGlobalRAGSource,
    deleteGlobalRAGSource,
  } = useWorkflowStore()

  const [activeTab, setActiveTab] = useState('tools')
  const [editingTool, setEditingTool] = useState<ToolConfig | null>(null)
  const [editingRAG, setEditingRAG] = useState<RAGSourceConfig | null>(null)

  const handleAddTool = () => {
    const newTool: Omit<ToolConfig, 'id'> = {
      name: 'New Tool',
      description: '',
      type: 'api',
      api_endpoint: '',
      method: 'GET',
      api_key_env_var: '',
    }
    addGlobalTool(newTool)
  }

  const handleAddRAGSource = () => {
    const newSource: Omit<RAGSourceConfig, 'id'> = {
      provider: 'pinecone',
      uri: '',
      api_key_env_var: '',
      embedding_model: 'text-embedding-3-small',
      top_k: 5,
      similarity_threshold: 0.7,
      hybrid_search: false,
    }
    addGlobalRAGSource(newSource)
  }

  return (
    <div className="fixed bottom-0 left-64 right-0 z-30">
      {/* Toggle Button */}
      <button
        onClick={toggleRegistryDrawer}
        className={cn(
          'absolute left-1/2 -translate-x-1/2 px-4 py-2 rounded-t-lg transition-all',
          'bg-card border border-b-0 border-border flex items-center gap-2',
          'hover:bg-secondary',
          registryDrawerOpen ? '-top-12' : '-top-10'
        )}
      >
        {registryDrawerOpen ? (
          <ChevronDown className="w-4 h-4" />
        ) : (
          <ChevronUp className="w-4 h-4" />
        )}
        <span className="text-sm font-medium">Global Registry</span>
      </button>

      {/* Drawer Content */}
      <AnimatePresence>
        {registryDrawerOpen && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 320 }}
            exit={{ height: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="bg-card border-t border-border overflow-hidden"
          >
            <div className="h-full p-4">
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <div className="flex items-center justify-between mb-4">
                  <TabsList className="bg-secondary">
                    <TabsTrigger value="tools" className="gap-2">
                      <Wrench className="w-4 h-4" />
                      Tools
                    </TabsTrigger>
                    <TabsTrigger value="rag" className="gap-2">
                      <Database className="w-4 h-4" />
                      RAG Sources
                    </TabsTrigger>
                  </TabsList>
                  <Button
                    size="sm"
                    onClick={activeTab === 'tools' ? handleAddTool : handleAddRAGSource}
                    className="gap-2"
                  >
                    <Plus className="w-4 h-4" />
                    Add {activeTab === 'tools' ? 'Tool' : 'RAG Source'}
                  </Button>
                </div>

                <TabsContent value="tools" className="mt-0">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-56 overflow-y-auto scrollbar-thin pr-2">
                    {globalTools.length === 0 ? (
                      <div className="col-span-full text-center py-8 text-muted-foreground">
                        No tools configured. Add a tool to get started.
                      </div>
                    ) : (
                      globalTools.map((tool) => (
                        <ToolCard
                          key={tool.id}
                          tool={tool}
                          onUpdate={(updates) => updateGlobalTool(tool.id, updates)}
                          onDelete={() => deleteGlobalTool(tool.id)}
                        />
                      ))
                    )}
                  </div>
                </TabsContent>

                <TabsContent value="rag" className="mt-0">
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 max-h-56 overflow-y-auto scrollbar-thin pr-2">
                    {globalRAGSources.length === 0 ? (
                      <div className="col-span-full text-center py-8 text-muted-foreground">
                        No RAG sources configured. Add a source to get started.
                      </div>
                    ) : (
                      globalRAGSources.map((source) => (
                        <RAGSourceCard
                          key={source.id}
                          source={source}
                          onUpdate={(updates) => updateGlobalRAGSource(source.id, updates)}
                          onDelete={() => deleteGlobalRAGSource(source.id)}
                        />
                      ))
                    )}
                  </div>
                </TabsContent>
              </Tabs>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

interface ToolCardProps {
  tool: ToolConfig
  onUpdate: (updates: Partial<ToolConfig>) => void
  onDelete: () => void
}

function ToolCard({ tool, onUpdate, onDelete }: ToolCardProps) {
  const [expanded, setExpanded] = useState(false)

  const getTypeIcon = () => {
    switch (tool.type) {
      case 'api':
        return <Globe className="w-4 h-4" />
      case 'function':
        return <Server className="w-4 h-4" />
      case 'mcp':
        return <Wrench className="w-4 h-4" />
    }
  }

  return (
    <div className="glass-card p-4 rounded-lg">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-primary/20">{getTypeIcon()}</div>
          <div>
            <Input
              value={tool.name}
              onChange={(e) => onUpdate({ name: e.target.value })}
              className="h-auto p-0 border-0 bg-transparent font-medium text-sm focus-visible:ring-0"
              placeholder="Tool Name"
            />
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          className="h-8 w-8 p-0 text-destructive hover:text-destructive"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      <div className="mt-3 space-y-3">
        <div>
          <Label className="text-xs text-muted-foreground">Type</Label>
          <Select
            value={tool.type}
            onValueChange={(value) => onUpdate({ type: value as ToolConfig['type'] })}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="api">API</SelectItem>
              <SelectItem value="function">Function</SelectItem>
              <SelectItem value="mcp">MCP</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div>
          <Label className="text-xs text-muted-foreground">Description</Label>
          <Textarea
            value={tool.description}
            onChange={(e) => onUpdate({ description: e.target.value })}
            className="h-16 text-xs resize-none"
            placeholder="What does this tool do?"
          />
        </div>

        {tool.type === 'api' && (
          <>
            <div className="grid grid-cols-3 gap-2">
              <div className="col-span-2">
                <Label className="text-xs text-muted-foreground">Endpoint</Label>
                <Input
                  value={tool.api_endpoint || ''}
                  onChange={(e) => onUpdate({ api_endpoint: e.target.value })}
                  className="h-8 text-xs"
                  placeholder="https://api.example.com"
                />
              </div>
              <div>
                <Label className="text-xs text-muted-foreground">Method</Label>
                <Select
                  value={tool.method || 'GET'}
                  onValueChange={(value) =>
                    onUpdate({ method: value as ToolConfig['method'] })
                  }
                >
                  <SelectTrigger className="h-8 text-xs">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GET">GET</SelectItem>
                    <SelectItem value="POST">POST</SelectItem>
                    <SelectItem value="PUT">PUT</SelectItem>
                    <SelectItem value="DELETE">DELETE</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div>
              <Label className="text-xs text-muted-foreground">API Key Env Var</Label>
              <Input
                value={tool.api_key_env_var || ''}
                onChange={(e) => onUpdate({ api_key_env_var: e.target.value })}
                className="h-8 text-xs"
                placeholder="TOOL_API_KEY"
              />
            </div>
          </>
        )}
        {tool.type === 'mcp' && (
          <div>
            <Label className="text-xs text-muted-foreground">MCP Endpoint</Label>
            <Input
              value={tool.mcp_endpoint || ''}
              onChange={(e) => onUpdate({ mcp_endpoint: e.target.value })}
              className="h-8 text-xs"
              placeholder="http://localhost:8080/mcp"
            />
          </div>
        )}
        {tool.type === 'function' && (
          <div>
            <Label className="text-xs text-muted-foreground">Code Snippet</Label>
            <Textarea
              value={tool.code_snippet || ''}
              onChange={(e) => onUpdate({ code_snippet: e.target.value })}
              className="h-20 text-xs font-mono resize-none"
              placeholder="def my_tool(input: str) -> str:&#10;    return input.upper()"
            />
          </div>
        )}
      </div>
    </div>
  )
}

interface RAGSourceCardProps {
  source: RAGSourceConfig
  onUpdate: (updates: Partial<RAGSourceConfig>) => void
  onDelete: () => void
}

function RAGSourceCard({ source, onUpdate, onDelete }: RAGSourceCardProps) {
  return (
    <div className="glass-card p-4 rounded-lg">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded bg-chart-2/20">
            <Database className="w-4 h-4 text-chart-2" />
          </div>
          <div>
            <Select
              value={source.provider}
              onValueChange={(value) =>
                onUpdate({ provider: value as RAGSourceConfig['provider'] })
              }
            >
              <SelectTrigger className="h-auto p-0 border-0 bg-transparent font-medium text-sm focus:ring-0">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="pinecone">Pinecone</SelectItem>
                <SelectItem value="weaviate">Weaviate</SelectItem>
                <SelectItem value="qdrant">Qdrant</SelectItem>
                <SelectItem value="chroma">Chroma</SelectItem>
                <SelectItem value="milvus">Milvus</SelectItem>
                <SelectItem value="file">File</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={onDelete}
          className="h-8 w-8 p-0 text-destructive hover:text-destructive"
        >
          <Trash2 className="w-4 h-4" />
        </Button>
      </div>

      <div className="mt-3 space-y-3">
        <div>
          <Label className="text-xs text-muted-foreground">Name</Label>
          <Input
            value={source.name || ''}
            onChange={(e) => onUpdate({ name: e.target.value })}
            className="h-8 text-xs"
            placeholder="My Vector Store"
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">URI</Label>
          <Input
            value={source.uri}
            onChange={(e) => onUpdate({ uri: e.target.value })}
            className="h-8 text-xs"
            placeholder="https://..."
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">API Key Env Var</Label>
          <Input
            value={source.api_key_env_var || ''}
            onChange={(e) => onUpdate({ api_key_env_var: e.target.value })}
            className="h-8 text-xs font-mono"
            placeholder="VECTOR_DB_API_KEY"
          />
        </div>
        {source.provider === 'file' && (
          <div>
            <Label className="text-xs text-muted-foreground">File Path</Label>
            <Input
              value={source.file_path || ''}
              onChange={(e) => onUpdate({ file_path: e.target.value })}
              className="h-8 text-xs font-mono"
              placeholder="/path/to/embeddings.json"
            />
          </div>
        )}

        <div>
          <Label className="text-xs text-muted-foreground">Embedding Model</Label>
          <Input
            value={source.embedding_model}
            onChange={(e) => onUpdate({ embedding_model: e.target.value })}
            className="h-8 text-xs"
            placeholder="text-embedding-3-small"
          />
        </div>

        <div className="grid grid-cols-2 gap-2">
          <div>
            <Label className="text-xs text-muted-foreground">
              Top-K: {source.top_k}
            </Label>
            <Slider
              value={[source.top_k]}
              onValueChange={([value]) => onUpdate({ top_k: value })}
              min={1}
              max={20}
              step={1}
              className="mt-2"
            />
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">
              Threshold: {source.similarity_threshold.toFixed(2)}
            </Label>
            <Slider
              value={[source.similarity_threshold * 100]}
              onValueChange={([value]) =>
                onUpdate({ similarity_threshold: value / 100 })
              }
              min={10}
              max={100}
              step={5}
              className="mt-2"
            />
          </div>
        </div>

        <div className="flex items-center justify-between">
          <Label className="text-xs text-muted-foreground">Hybrid Search</Label>
          <Switch
            checked={source.hybrid_search}
            onCheckedChange={(checked) => onUpdate({ hybrid_search: checked })}
          />
        </div>
      </div>
    </div>
  )
}

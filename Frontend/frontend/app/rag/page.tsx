'use client'

import { motion } from 'framer-motion'
import {
  Plus,
  Database,
  Trash2,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Slider } from '@/components/ui/slider'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { RAGSourceConfig } from '@/lib/types'

export default function RAGPage() {
  const { globalRAGSources, addGlobalRAGSource, updateGlobalRAGSource, deleteGlobalRAGSource } =
    useWorkflowStore()

  const handleAddSource = () => {
    addGlobalRAGSource({
      provider: 'pinecone',
      uri: '',
      api_key_env_var: '',
      embedding_model: 'text-embedding-3-small',
      top_k: 5,
      similarity_threshold: 0.7,
      hybrid_search: false,
    })
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">RAG Sources</h1>
            <p className="text-muted-foreground mt-1">
              Configure vector database connections for retrieval-augmented generation
            </p>
          </div>
          <Button onClick={handleAddSource} className="gap-2 glow-primary-sm">
            <Plus className="w-4 h-4" />
            Add RAG Source
          </Button>
        </div>

        {/* Sources Grid */}
        {globalRAGSources.length === 0 ? (
          <Card className="glass-card">
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-chart-2/10 flex items-center justify-center">
                <Database className="w-8 h-8 text-chart-2" />
              </div>
              <h3 className="text-lg font-medium mb-2">No RAG sources configured</h3>
              <p className="text-muted-foreground mb-4">
                Connect a vector database to enable knowledge retrieval
              </p>
              <Button onClick={handleAddSource} className="gap-2">
                <Plus className="w-4 h-4" />
                Add RAG Source
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {globalRAGSources.map((source, index) => (
              <motion.div
                key={source.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <RAGSourceCard
                  source={source}
                  onUpdate={(updates) => updateGlobalRAGSource(source.id, updates)}
                  onDelete={() => deleteGlobalRAGSource(source.id)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

interface RAGSourceCardProps {
  source: RAGSourceConfig
  onUpdate: (updates: Partial<RAGSourceConfig>) => void
  onDelete: () => void
}

function RAGSourceCard({ source, onUpdate, onDelete }: RAGSourceCardProps) {
  const providerColors: Record<string, string> = {
    pinecone: 'text-success',
    weaviate: 'text-chart-2',
    qdrant: 'text-warning',
    chroma: 'text-primary',
    milvus: 'text-chart-4',
  }

  return (
    <Card className="glass-card">
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-card">
              <Database className={`w-5 h-5 ${providerColors[source.provider] || 'text-primary'}`} />
            </div>
            <div className="flex-1 min-w-0">
              <Select
                value={source.provider}
                onValueChange={(value) =>
                  onUpdate({ provider: value as RAGSourceConfig['provider'] })
                }
              >
                <SelectTrigger className="h-auto p-0 border-0 bg-transparent font-semibold text-base focus:ring-0">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="pinecone">Pinecone</SelectItem>
                  <SelectItem value="weaviate">Weaviate</SelectItem>
                  <SelectItem value="qdrant">Qdrant</SelectItem>
                  <SelectItem value="chroma">Chroma</SelectItem>
                  <SelectItem value="milvus">Milvus</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={onDelete}
            className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <Label className="text-xs text-muted-foreground">Connection URI</Label>
          <Input
            value={source.uri}
            onChange={(e) => onUpdate({ uri: e.target.value })}
            className="mt-1 font-mono text-sm"
            placeholder="https://..."
          />
        </div>

        <div>
          <Label className="text-xs text-muted-foreground">API Key Env Var</Label>
          <Input
            value={source.api_key_env_var || ''}
            onChange={(e) => onUpdate({ api_key_env_var: e.target.value })}
            className="mt-1 font-mono text-sm"
            placeholder="PINECONE_API_KEY"
          />
        </div>

        <div>
          <Label className="text-xs text-muted-foreground">Embedding Model</Label>
          <Input
            value={source.embedding_model}
            onChange={(e) => onUpdate({ embedding_model: e.target.value })}
            className="mt-1"
            placeholder="text-embedding-3-small"
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
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
              Threshold: {(source.similarity_threshold * 100).toFixed(0)}%
            </Label>
            <Slider
              value={[source.similarity_threshold * 100]}
              onValueChange={([value]) => onUpdate({ similarity_threshold: value / 100 })}
              min={10}
              max={100}
              step={5}
              className="mt-2"
            />
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div className="space-y-0.5">
            <Label className="text-sm">Hybrid Search</Label>
            <p className="text-xs text-muted-foreground">Dense + Sparse retrieval</p>
          </div>
          <Switch
            checked={source.hybrid_search}
            onCheckedChange={(checked) => onUpdate({ hybrid_search: checked })}
          />
        </div>
      </CardContent>
    </Card>
  )
}

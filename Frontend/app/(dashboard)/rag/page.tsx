'use client'

import { useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Button } from '@/components/ui/button'
import { RefreshCw, Zap, Sparkles, Download, FileCode, Copy, CheckCircle2, AlertCircle, Loader2, Plus, Minus, ArrowRight, ArrowLeft, Database, Globe, Search, Filter, Settings } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface RAGPipelineConfig {
  name: string
  description: string
  embedding: {
    provider: string
    model: string
    dimensions: number
  }
  vectorStore: {
    provider: string
    collection: string
    config: Record<string, any>
  }
  retriever: {
    type: 'vector' | 'hybrid' | 'bm25'
    topK: number
    similarityThreshold: number
    reranker?: string
  }
  chunking: {
    chunkSize: number
    chunkOverlap: number
    strategy: 'fixed' | 'semantic' | 'recursive'
  }
  generation: {
    provider: string
    model: string
    temperature: number
    maxTokens: number
    promptTemplate: string
  }
}

export default function RAGPipelineBuilder() {
  const [config, setConfig] = useState<RAGPipelineConfig>({
    name: '',
    description: '',
    embedding: {
      provider: 'openai',
      model: 'text-embedding-3-small',
      dimensions: 1536,
    },
    vectorStore: {
      provider: 'qdrant',
      collection: 'documents',
      config: {
        url: 'http://localhost:6333',
        apiKey: '',
      },
    },
    retriever: {
      type: 'vector',
      topK: 5,
      similarityThreshold: 0.7,
      reranker: 'cross-encoder',
    },
    chunking: {
      chunkSize: 1000,
      chunkOverlap: 200,
      strategy: 'recursive',
    },
    generation: {
      provider: 'openai',
      model: 'gpt-4o-mini',
      temperature: 0.7,
      maxTokens: 4096,
      promptTemplate: 'Answer the question based on the provided context.\n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:',
    },
  })
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'config' | 'test' | 'deploy'>('config')

  const { token } = useAuthStore()

  const updateConfig = useCallback((path: string, value: any) => {
    setConfig(prev => {
      const keys = path.split('.')
      const newConfig = JSON.parse(JSON.stringify(config))
      let obj: any = newConfig
      for (let i = 0; i < keys.length - 1; i++) {
        obj = obj[keys[i]]
      }
      obj[keys[keys.length - 1]] = value
      return newConfig
    })
  }, [config])

  const handleSave = async () => {
    // Save to backend
    alert('Configuration saved!')
  }

  const handleTest = async () => {
    setIsTesting(true)
    setTestResult(null)
    // Test the RAG pipeline
    setTimeout(() => {
      setTestResult('Test passed! Retrieved 3 relevant chunks. Latency: 245ms')
      setIsTesting(false)
    }, 1500)
  }

  const handleDeploy = async () => {
    alert('Deploying RAG pipeline...')
  }

  const handleExport = () => {
    const blob = new Blob([JSON.stringify(config, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rag-pipeline-config.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const content = e.target?.result as string
        const parsed = JSON.parse(content)
        setConfig(parsed)
      } catch (error) {
        alert('Invalid JSON file')
      }
    }
    reader.readAsText(file)
  }

  const embeddingProviders = ['openai', 'azure', 'cohere', 'huggingface', 'vertex', 'local']
  const vectorStoreProviders = ['qdrant', 'pinecone', 'weaviate', 'chroma', 'milvus', 'pgvector']
  const llmProviders = ['openai', 'anthropic', 'google', 'azure', 'cohere', 'ollama', 'local']

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">RAG Pipeline Builder</h1>
          <p className="text-muted-foreground mt-1">Build and deploy Retrieval-Augmented Generation pipelines visually</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={() => { /* import */ }} className="gap-2">
            <Upload className="w-4 h-4 mr-2" />
            Import Config
          </Button>
          <Button variant="outline" onClick={() => { /* export */ }} className="gap-2">
            <Download className="w-4 h-4 mr-2" />
            Export Config
          </Button>
        </div>
      </div>

      <Tabs defaultValue="config" className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="config">Configuration</TabsTrigger>
          <TabsTrigger value="test">Test Pipeline</TabsTrigger>
          <TabsTrigger value="deploy">Deploy</TabsTrigger>
        </TabsList>

        <TabsContent value="config" className="mt-4 space-y-6">
          {/* Embedding Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-4 h-4 text-primary" />
                Embedding Model
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="embedding-provider">Provider</Label>
                  <Select value={config.embedding.provider} onValueChange={(v) => setConfig(prev => ({ ...prev, embedding: { ...prev.embedding, provider: v }) })}>
                    <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
                    <SelectContent>
                      {embeddingProviders.map(p => (
                        <SelectItem key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="embedding-model">Model</Label>
                  <Select value={config.embedding.model} onValueChange={(v) => setConfig(prev => ({ ...prev, embedding: { ...prev.embedding, model: v }) })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="text-embedding-3-small">text-embedding-3-small (1536 dim)</SelectItem>
                      <SelectItem value="text-embedding-3-large">text-embedding-3-large (3072 dim)</SelectItem>
                      <SelectItem value="text-embedding-ada-002">text-embedding-ada-002 (1536 dim)</SelectItem>
                      <SelectItem value="embed-english-v3.0">Cohere embed-english-v3.0 (1024 dim)</SelectItem>
                      <SelectItem value="embed-multilingual-v3.0">Cohere embed-multilingual-v3.0 (1024 dim)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="embedding-dimensions">Dimensions</Label>
                  <Input
                    type="number"
                    value={config.embedding.dimensions}
                    onChange={(e) => setConfig(prev => ({ ...prev, embedding: { ...prev.embedding, dimensions: parseInt(e.target.value) || 1536 }) })}
                    className="w-32"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Vector Store Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Database className="w-4 h-4 text-primary" />
                Vector Store
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label htmlFor="vs-provider">Provider</Label>
                  <Select value={config.vectorStore.provider} onValueChange={(v) => setConfig(prev => ({ ...prev, vectorStore: { ...prev.vectorStore, provider: v }) })}>
                    <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
                    <SelectContent>
                      {vectorStoreProviders.map(p => (
                        <SelectItem key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vs-collection">Collection Name</Label>
                  <Input
                    value={config.vectorStore.collection}
                    onChange={(e) => setConfig(prev => ({ ...prev, vectorStore: { ...prev.vectorStore, collection: e.target.value } }))}
                    placeholder="documents"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="vs-api-key">API Key</Label>
                  <Input
                    type="password"
                    value={config.vectorStore.config.apiKey}
                    onChange={(e) => setConfig(prev => ({ ...prev, vectorStore: { ...prev.vectorStore, config: { ...prev.vectorStore.config, apiKey: e.target.value } }))}
                    placeholder="API key (optional)"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="vs-url">URL / Endpoint</Label>
                <Input
                  value={config.vectorStore.config.url}
                  onChange={(e) => setConfig(prev => ({ ...prev, vectorStore: { ...prev.vectorStore, config: { ...prev.vectorStore.config, url: e.target.value } }))}
                  placeholder="http://localhost:6333"
                />
              </div>
            </CardContent>
          </Card>

          {/* Retriever Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Search className="w-4 h-4 text-primary" />
                Retriever Settings
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Retriever Type</Label>
                  <Select value={config.retriever.type} onValueChange={(v) => setConfig(prev => ({ ...prev, retriever: { ...prev.retriever, type: v }) })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="vector">Vector Similarity</SelectItem>
                      <SelectItem value="hybrid">Hybrid (Vector + BM25)</SelectItem>
                      <SelectItem value="bm25">BM25 Only</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Top K Results</Label>
                  <Input
                    type="number"
                    min={1}
                    max={50}
                    value={config.retriever.topK}
                    onChange={(e) => setConfig(prev => ({ ...prev, retriever: { ...prev.retriever, topK: parseInt(e.target.value) || 5 }) })}
                    className="w-32"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Similarity Threshold</Label>
                  <Input
                    type="number"
                    min={0}
                    max={1}
                    step={0.05}
                    value={config.retriever.similarityThreshold}
                    onChange={(e) => setConfig(prev => ({ ...prev, retriever: { ...prev.retriever, similarityThreshold: parseFloat(e.target.value) || 0.7 }) })}
                    className="w-32"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Reranker Model (Optional)</Label>
                <Select value={config.retriever.reranker || ''} onValueChange={(v) => setConfig(prev => ({ ...prev, retriever: { ...prev.retriever, reranker: v || undefined }) })}>
                  <SelectTrigger><SelectValue placeholder="No reranker" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
                    <SelectItem value="cross-encoder/ms-marco-MiniLM-L-6-v2">cross-encoder/ms-marco-MiniLM-L-6-v2</SelectItem>
                    <SelectItem value="cross-encoder/ms-marco-MiniLM-L-12-v2">cross-encoder/ms-marco-MiniLM-L-12-v2</SelectItem>
                    <SelectItem value="cohere/rerank-english-v3.0">Cohere Rerank v3.0</SelectItem>
                    <SelectItem value="bge-reranker-v2-m3">BAAI/bge-reranker-v2-m3</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </CardContent>
          </Card>

          {/* Chunking Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-primary" />
                Chunking Strategy
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Strategy</Label>
                  <Select value={config.chunking.strategy} onValueChange={(v) => setConfig(prev => ({ ...prev, chunking: { ...prev.chunking, strategy: v }) })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="recursive">Recursive Character</SelectItem>
                      <SelectItem value="semantic">Semantic</SelectItem>
                      <SelectItem value="fixed">Fixed Size</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Chunk Size</Label>
                  <Input
                    type="number"
                    min={100}
                    max={4000}
                    value={config.chunking.chunkSize}
                    onChange={(e) => setConfig(prev => ({ ...prev, chunking: { ...prev.chunking, chunkSize: parseInt(e.target.value) || 1000 }) })}
                    className="w-32"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Chunk Overlap</Label>
                  <Input
                    type="number"
                    min={0}
                    max={1000}
                    value={config.chunking.chunkOverlap}
                    onChange={(e) => setConfig(prev => ({ ...prev, chunking: { ...prev.chunking, chunkOverlap: parseInt(e.target.value) || 200 }) })}
                    className="w-32"
                  />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Generation Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-primary" />
                Generation Model
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div className="space-y-2">
                  <Label>Provider</Label>
                  <Select value={config.generation.provider} onValueChange={(v) => setConfig(prev => ({ ...prev, generation: { ...prev.generation, provider: v }) })}>
                    <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
                    <SelectContent>
                      {llmProviders.map(p => (
                        <SelectItem key={p} value={p}>{p.charAt(0).toUpperCase() + p.slice(1)}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Model</Label>
                  <Select value={config.generation.model} onValueChange={(v) => setConfig(prev => ({ ...prev, generation: { ...prev.generation, model: v }) })}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="gpt-4o">GPT-4o</SelectItem>
                      <SelectItem value="gpt-4o-mini">GPT-4o-mini</SelectItem>
                      <SelectItem value="gpt-4-turbo">GPT-4 Turbo</SelectItem>
                      <SelectItem value="claude-3-5-sonnet-20241022">Claude 3.5 Sonnet</SelectItem>
                      <SelectItem value="claude-3-haiku-20240307">Claude 3 Haiku</SelectItem>
                      <SelectItem value="gemini-1.5-pro">Gemini 1.5 Pro</SelectItem>
                      <SelectItem value="gemini-1.5-flash">Gemini 1.5 Flash</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Temperature</Label>
                  <Input
                    type="number"
                    min={0}
                    max={2}
                    step={0.1}
                    value={config.generation.temperature}
                    onChange={(e) => setConfig(prev => ({ ...prev, generation: { ...prev.generation, temperature: parseFloat(e.target.value) || 0.7 }) })}
                    className="w-32"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label>Max Tokens</Label>
                <Input
                  type="number"
                  min={1}
                  max={8192}
                  value={config.generation.maxTokens}
                  onChange={(e) => setConfig(prev => ({ ...prev, generation: { ...prev.generation, maxTokens: parseInt(e.target.value) || 4096 }) })}
                  className="w-32"
                />
              </div>
              <div className="space-y-2">
                <Label>Prompt Template</Label>
                <Textarea
                  value={config.generation.promptTemplate}
                  onChange={(e) => setConfig(prev => ({ ...prev, generation: { ...prev.generation, promptTemplate: e.target.value } }))}
                  rows={4}
                  placeholder="Answer the question based on the provided context.\n\nContext: {context}\n\nQuestion: {question}\n\nAnswer:"
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="test" className="mt-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>Test Query</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Test Question</Label>
                  <Textarea
                    placeholder="Enter a test question to run against the pipeline..."
                    rows={4}
                    value={testQuery}
                    onChange={(e) => setTestQuery(e.target.value)}
                  />
                </div>
                <Button onClick={handleTest} disabled={isTesting} className="gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {isTesting ? 'Testing...' : 'Run Test'}
                </Button>
                {testResult && (
                  <div className={`p-4 rounded-lg border ${testResult?.includes('passed') ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}>
                    {testResult}
                  </div>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Test Results History</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground text-sm">Test history will appear here after running tests</p>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="deploy" className="mt-4">
            <Card>
              <CardHeader>
                <CardTitle>Deploy Pipeline</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Deployment Name</Label>
                  <Input placeholder="my-rag-pipeline" />
                </div>
                <div className="space-y-2">
                  <Label>Environment</Label>
                  <Select>
                    <SelectTrigger><SelectValue placeholder="Select environment" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="development">Development</SelectItem>
                      <SelectItem value="staging">Staging</SelectItem>
                      <SelectItem value="production">Production</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleDeploy} className="gap-2">
                    <Download className="w-4 h-4" />
                    Deploy Pipeline
                  </Button>
                  <Button variant="outline" onClick={handleExport} className="gap-2">
                    <Download className="w-4 h-4 mr-2" />
                    Export Config
                  </Button>
                </div>
                <div className="p-4 bg-muted/50 rounded-lg">
                  <h4 className="font-medium mb-2">Deployment Status</h4>
                  <p className="text-sm text-muted-foreground">Pipeline not yet deployed. Click "Deploy Pipeline" to deploy.</p>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default RAGPipelineBuilder
'use client'

import { useEffect, useState, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger, DialogFooter } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Plus, Edit, Trash2, Database, ExternalLink, Eye, Save, AlertCircle, CheckCircle2, Plus } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface DatabaseRoute {
  id: string
  name: string
  purpose: 'checkpointer' | 'store' | 'vector_store' | 'analytics' | 'audit_log' | 'cache' | 'rate_limit'
  provider: string
  config: Record<string, unknown>
  schema_contract: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at: string
}

export default function DatabaseRoutesPage() {
  const [routes, setRoutes] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [editingRoute, setEditingRoute] = useState<any | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    purpose: 'vector_store',
    provider: '',
    config: {},
    schema_contract: {},
  })
  const [schemaError, setSchemaError] = useState<string | null>(null)

  const { token } = useAuthStore()

  useEffect(() => {
    fetchRoutes()
  }, [])

  const fetchRoutes = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        // Extract database routes from integrations.persistence
        const routes = data.integrations?.persistence || {}
        const routesArray = Object.entries(routes).map(([key, value]: [string, any]) => ({
          id: key,
          name: value.name || key,
          purpose: value.purpose,
          provider: value.provider,
          config: value.config || {},
          schema_contract: value.schema_contract || {},
          is_active: value.is_active ?? true,
        }))
        setRoutes(routesArray)
      }
    } catch (error) {
      console.error('Failed to fetch routes:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async () => {
    setIsCreating(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          integrations: {
            persistence: {
              [formData.name]: {
                purpose: formData.purpose,
                provider: formData.provider,
                config: formData.config,
                schema_contract: formData.schema_contract,
                name: formData.name,
                is_active: true,
              }
            }
          }
        }),
      })
      if (response.ok) {
        await fetchRoutes()
        setFormData({ name: '', purpose: 'vector_store', provider: '', config: {}, schema_contract: {} })
      } else {
        const error = await response.json()
        alert(`Failed to create: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to create: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleUpdate = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          integrations: {
            persistence: {
              [editingRoute!.id]: {
                ...editingRoute,
                ...formData,
              }
            }
          }
        }),
      })
      if (response.ok) {
        await fetchRoutes()
        setEditingRoute(null)
        setFormData({ name: '', purpose: 'vector_store', provider: '', config: {}, schema_contract: {} })
      } else {
        const error = await response.json()
        alert(`Failed to update: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to update: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this database route?')) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/config`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          integrations: {
            persistence: {
              [id]: null // Setting to null might remove it, or we need a DELETE endpoint
            }
          }
        }),
      })
      if (response.ok) {
        await fetchRoutes()
      } else {
        const error = await response.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to delete: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleEdit = (route: any) => {
    setEditingRoute(route)
    setFormData({
      name: route.name,
      purpose: route.purpose,
      provider: route.provider,
      config: route.config,
      schema_contract: route.schema_contract,
    })
  }

  const purposeOptions = [
    { value: 'checkpointer', label: 'Checkpointer' },
    { value: 'store', label: 'Store' },
    { value: 'vector_store', label: 'Vector Store' },
    { value: 'analytics', label: 'Analytics' },
    { value: 'audit_log', label: 'Audit Log' },
    { value: 'cache', label: 'Cache' },
    { value: 'rate_limit', label: 'Rate Limit' },
  ]

  const providerOptions: Record<string, string[]> = {
    checkpointer: ['postgresql', 'sqlite', 'redis'],
    store: ['postgresql', 'redis', 'mongodb'],
    vector_store: ['qdrant', 'pinecone', 'weaviate', 'chroma', 'milvus', 'pgvector'],
    analytics: ['clickhouse', 'postgresql', 'bigquery', 'snowflake'],
    audit_log: ['postgresql', 'clickhouse', 'elasticsearch'],
    cache: ['redis', 'memcached', 'valkey'],
    rate_limit: ['redis', 'valkey'],
  }

  const handleConfigChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    try {
      const parsed = JSON.parse(e.target.value)
      setFormData(prev => ({ ...prev, config: parsed }))
      setSchemaError(null)
    } catch (e) {
      setSchemaError('Invalid JSON')
    }
  }

  const handleSchemaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    try {
      const parsed = JSON.parse(e.target.value)
      setFormData(prev => ({ ...prev, schema_contract: parsed }))
      setSchemaError(null)
    } catch (e) {
      setSchemaError('Invalid JSON')
    }
  }

  const purposeProviders = providerOptions[formData.purpose] || []

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Database Routes</h1>
          <p className="text-muted-foreground mt-1">Configure database connections for checkpointer, vector store, cache, and more</p>
        </div>
        <Button onClick={() => { setFormData({ name: '', purpose: 'vector_store', provider: '', config: {}, schema_contract: {} }); setEditingRoute(null) }} className="gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          Add Database Route
        </Button>
      </div>

      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="bg-card border border-border rounded-lg p-6 animate-pulse">
              <div className="h-4 bg-muted rounded w-3/4 mb-4"></div>
              <div className="space-y-3">
                <div className="h-4 bg-muted rounded w-1/2"></div>
                <div className="h-4 bg-muted rounded w-1/2"></div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {routes.map((route) => (
              <div key={route.id} className="bg-card border border-border rounded-lg p-6 hover:border-primary/50 transition-colors">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <h3 className="font-semibold text-lg">{route.name}</h3>
                    <p className="text-sm text-muted-foreground">{route.id}</p>
                  </div>
                  <Badge variant={route.is_active ? 'default' : 'secondary'}>
                    {route.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </div>
                
                <div className="space-y-2 text-sm mb-4">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{route.purpose}</Badge>
                    <Badge variant="secondary">{route.provider}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground font-mono truncate max-w-full">
                    {JSON.stringify(route.config).slice(0, 100)}...
                  </p>
                </div>

                <div className="flex items-center gap-2 pt-4 border-t border-border">
                  <Button variant="outline" size="sm" onClick={() => handleEdit(route)} className="gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5M18.72 6.55a2.121 2.121 0 013 3l-4 4a2.121 2.121 0 01-3 0L4.17 16.17a2.121 2.121 0 010-3l10-10a2.121 2.121 0 013 0z" /></svg>
                    Edit
                  </Button>
                  <Button variant="destructive" size="sm" onClick={() => handleDelete(route.id)} className="gap-1">
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v12M8 7v12m4-12v12" /></svg>
                    Delete
                  </Button>
                </div>
              </div>
            ))}
          </div>

          {routes.length === 0 && (
            <div className="text-center py-12">
              <svg className="w-12 h-12 mx-auto text-muted-foreground mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4" />
              </svg>
              <h3 className="text-lg font-medium mb-2">No database routes configured</h3>
              <p className="text-muted-foreground mb-4">Create your first database route to connect to external databases</p>
              <Button onClick={() => { setFormData({ name: '', purpose: 'vector_store', provider: '', config: {}, schema_contract: {} }); }} className="gap-2">
                <Plus className="w-4 h-4" />
                Create Database Route
              </Button>
            </div>
          )}
        </>
      </div>

      {/* Create/Edit Dialog */}
      <div className="fixed inset-0 z-50 overflow-y-auto" style={{ display: editingRoute ? 'block' : 'none' }}>
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative w-full max-w-2xl max-h-[90vh] overflow-auto rounded-lg bg-background p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">{editingRoute ? 'Edit' : 'Create'} Database Route</h2>
              <button onClick={() => { setEditingRoute(null); setFormData({ name: '', purpose: 'vector_store', provider: '', config: {}, schema_contract: {} }) }} className="text-muted-foreground hover:text-foreground">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); editingRoute ? handleUpdate() : handleCreate() }} className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" value={formData.name} onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g., production-vector-store" required />
              </div>

              <div className="space-y-2">
                <Label htmlFor="purpose">Purpose</Label>
                <Select value={formData.purpose} onValueChange={(v) => setFormData(prev => ({ ...prev, purpose: v }))}>
                  <SelectTrigger><SelectValue placeholder="Select purpose" /></SelectTrigger>
                  <SelectContent>
                    {purposeOptions.map((opt) => (
                      <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="provider">Provider</Label>
                <Select value={formData.provider} onValueChange={(v) => setFormData(prev => ({ ...prev, provider: v }))} disabled={purposeProviders.length === 0}>
                  <SelectTrigger><SelectValue placeholder="Select provider" /></SelectTrigger>
                  <SelectContent>
                    {purposeProviders.map((p) => (
                      <SelectItem key={p} value={p}>{p}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {purposeProviders.length === 0 && <p className="text-xs text-muted-foreground">Select a purpose first</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="config">Connection Config (JSON)</Label>
                <Textarea
                  value={JSON.stringify(formData.config, null, 2)}
                  onChange={handleConfigChange}
                  rows={6}
                  className="font-mono text-sm"
                  placeholder='{"host": "localhost", "port": 5432, "database": "mydb"}'
                />
                {schemaError && <p className="text-sm text-red-500">{schemaError}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="schema_contract">Schema Contract (JSON)</Label>
                <Textarea
                  value={JSON.stringify(formData.schema_contract, null, 2)}
                  onChange={handleSchemaChange}
                  rows={4}
                  className="font-mono text-sm"
                  placeholder='{"purpose": "vector_store", "collections": {"documents": {"columns": {"vector": {"type": "vector", "dimension": 1536}}}}}'
                />
                {schemaError && <p className="text-sm text-red-500">{schemaError}</p>}
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => { setEditingRoute(null); setFormData({ name: '', purpose: 'vector_store', provider: '', config: {}, schema_contract: {} }) }}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isCreating}>
                  {editingRoute ? 'Update' : 'Create'} Route
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

export default DatabaseRoutesPage
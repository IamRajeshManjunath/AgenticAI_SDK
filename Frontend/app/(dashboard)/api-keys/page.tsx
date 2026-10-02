'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Plus, Edit, Trash2, Key, Copy, Eye, EyeOff, Shield, AlertCircle, CheckCircle2, Loader2, Calendar, Clock, Filter, Search, MoreHorizontal } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Textarea } from '@/components/ui/textarea'

interface ApiKey {
  id: string
  name: string
  key_prefix: string
  is_active: boolean
  last_used_at: string | null
  created_at: string
  expires_at: string | null
  workflow_id: string | null
}

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [editingKey, setEditingKey] = useState<any | null>(null)
  const [showValue, setShowValue] = useState<string | null>(null)
  const [selectedKey, setSelectedKey] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    workflow_id: '',
    expires_at: '',
  })
  const [editingKey, setEditingKey] = useState<any | null>(null)

  const { token } = useAuthStore()

  useEffect(() => {
    fetchKeys()
  }, [])

  const fetchKeys = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/api-keys`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setKeys(data)
      }
    } catch (error) {
      console.error('Failed to fetch API keys:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async () => {
    setIsCreating(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/api-keys`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(formData),
      })
      if (response.ok) {
        const data = await response.json()
        setShowValue(data.key)
        await fetchKeys()
        setFormData({ name: '', workflow_id: '', expires_at: '' })
      } else {
        const error = await response.json()
        alert(`Failed to create: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to create: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsCreating(false)
    }
  }

  const handleUpdate = async () => {
    if (!editingKey) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/api-keys/${editingKey.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(formData),
      })
      if (response.ok) {
        await fetchKeys()
        setEditingKey(null)
        setFormData({ name: '', workflow_id: '', expires_at: '' })
      } else {
        const error = await response.json()
        alert(`Failed to update: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to update: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this API key? This cannot be undone.')) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/api-keys/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        await fetchKeys()
      } else {
        const error = await response.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to delete: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleRegenerate = async (id: string) => {
    if (!window.confirm('Regenerate this API key? The old key will be invalidated.')) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/api-keys/${id}/regenerate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setShowValue(data.key)
        await fetchKeys()
      } else {
        const error = await response.json()
        alert(`Failed to regenerate: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to regenerate: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleViewValue = async (key: any) => {
    if (showValue === key.id) {
      setShowValue(null)
      return
    }
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/secrets/${key.id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setShowValue(data.value)
        setSelectedKey(key.id)
      }
    } catch (error) {
      console.error('Failed to fetch secret value:', error)
    }
  }

  const handleCopyValue = (value: string) => {
    navigator.clipboard.writeText(value)
    alert('Copied to clipboard!')
  }

  const handleEdit = (key: any) => {
    setEditingKey(key)
    setFormData({
      name: key.name,
      workflow_id: key.workflow_id || '',
      expires_at: key.expires_at || '',
    })
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">API Key Management</h1>
          <p className="text-muted-foreground mt-1">Manage API keys for programmatic access to the API</p>
        </div>
        <Button onClick={() => { setFormData({ name: '', workflow_id: '', expires_at: '' }); setEditingKey(null) }} className="gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          Create API Key
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
            {keys.map((key) => (
              <Card key={key.id} className="hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <h3 className="font-semibold text-lg">{key.name}</h3>
                      <Badge variant={key.is_active ? 'default' : 'secondary'}>
                        {key.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline">{key.key_prefix}</Badge>
                      {key.workflow_id && (
                        <Badge variant="secondary">Workflow: {key.workflow_id.slice(0, 8)}...</Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="space-y-2 text-sm">
                      <div className="flex items-center gap-2">
                        <Label className="text-xs text-muted-foreground">Prefix</Label>
                        <code className="px-2 py-1 bg-muted rounded text-xs font-mono">{key.key_prefix}********</code>
                        {showValue === key.id && (
                          <>
                            <code className="px-2 py-1 bg-muted rounded text-xs font-mono break-all">{showValue}</code>
                            <Button variant="ghost" size="sm" onClick={() => handleCopyValue(secrets.find(s => s.id === showValue)?.value || '')} className="gap-1">
                              <Copy className="w-3 h-3" />
                              Copy
                            </Button>
                          </>
                        )}
                        <div className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span>Created: {new Date(key.created_at).toLocaleDateString()}</span>
                          {key.expires_at && <span>Expires: {new Date(key.expires_at).toLocaleDateString()}</span>}
                          {key.last_used_at && <span>Last used: {new Date(key.last_used_at).toLocaleDateString()}</span>}
                        </div>
                      </div>

                      <div className="flex items-center gap-2 pt-3 border-t border-border">
                        <Button variant="ghost" size="sm" onClick={() => handleViewValue(key)} className="gap-1">
                          {showValue === key.id ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                          {showValue === key.id ? 'Hide' : 'Show'}
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleCopyValue(secrets.find(s => s.id === showValue)?.value || '')} disabled={showValue !== key.id} className="gap-1">
                          <Copy className="w-4 h-4" />
                          Copy
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => { setEditingKey(key); setFormData({ name: key.name, workflow_id: key.workflow_id || '', expires_at: key.expires_at || '' }) }} className="gap-1">
                          <Edit className="w-4 h-4" />
                          Edit
                        </Button>
                        <Button variant="ghost" size="sm" onClick={() => handleRegenerate(key.id)} className="gap-1 text-orange-600 hover:text-orange-700">
                          <RefreshCw className="w-4 h-4" />
                          Regenerate
                        </Button>
                        <Button variant="ghost" size="sm" variant="destructive" onClick={() => handleDelete(key.id)} className="gap-1">
                          <Trash2 className="w-4 h-4" />
                          Delete
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {keys.length === 0 && (
                <div className="text-center py-12">
                  <Key className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="text-lg font-medium mb-2">No API keys configured</h3>
                  <p className="text-muted-foreground mb-4">Create your first API key to start integrating with the API</p>
                  <Button onClick={() => { setFormData({ name: '', workflow_id: '', expires_at: '' }); setEditingKey(null) }} className="gap-2">
                    <Plus className="w-4 h-4" />
                    Create API Key
                  </Button>
                </div>
              )}
            </div>
          </>
        )}
      </div>

      {/* Create/Edit Dialog */}
      <div className="fixed inset-0 z-50 overflow-y-auto" style={{ display: editingKey ? 'block' : 'none' }}>
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative w-full max-w-md max-h-[90vh] overflow-auto rounded-lg bg-background p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">{editingKey ? 'Edit' : 'Create'} API Key</h2>
              <button onClick={() => { setEditingKey(null); setFormData({ name: '', workflow_id: '', expires_at: '' }) }} className="text-muted-foreground hover:text-foreground">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); editingKey ? handleUpdate() : handleCreate() }} className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" value={formData.name} onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g., Production API Key" required />
              </div>

              <div className="space-y-2">
                <Label htmlFor="workflow_id">Workflow ID (Optional)</Label>
                <Input
                  id="workflow_id"
                  value={formData.workflow_id}
                  onChange={(e) => setFormData(prev => ({ ...prev, workflow_id: e.target.value }))}
                  placeholder="Workflow ID (optional)"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="expires_at">Expires At (Optional)</Label>
                <Input
                  id="expires_at"
                  type="datetime-local"
                  value={formData.expires_at}
                  onChange={(e) => setFormData(prev => ({ ...prev, expires_at: e.target.value }))}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => { setEditingKey(null); setFormData({ name: '', workflow_id: '', expires_at: '' }) }}>
                  Cancel
                </Button>
                <Button type="submit" disabled={isCreating}>
                  {editingKey ? 'Update' : 'Create'} API Key
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

export default ApiKeysPage
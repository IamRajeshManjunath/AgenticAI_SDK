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
import { RefreshCw, Plus, Edit, Trash2, Eye, Lock, Key, Copy, AlertCircle, CheckCircle2, Shield } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface Secret {
  id: string
  name: string
  description: string | null
  value: string
  created_at: string
  updated_at: string
}

export default function SecretsPage() {
  const [secrets, setSecrets] = useState<Secret[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isCreating, setIsCreating] = useState(false)
  const [editingSecret, setEditingSecret] = useState<Secret | null>(null)
  const [showValue, setShowValue] = useState<string | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    value: '',
    description: '',
  })

  const { token } = useAuthStore()

  useEffect(() => {
    fetchSecrets()
  }, [])

  const fetchSecrets = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/secrets`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setSecrets(data)
      }
    } catch (error) {
      console.error('Failed to fetch secrets:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreate = async () => {
    setIsCreating(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/secrets`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(formData),
      })
      if (response.ok) {
        await fetchSecrets()
        setFormData({ name: '', value: '', description: '' })
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
    if (!editingSecret) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/secrets/${editingSecret.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify({
          name: formData.name,
          value: formData.value,
          description: formData.description,
        }),
      })
      if (response.ok) {
        await fetchSecrets()
        setEditingSecret(null)
        setFormData({ name: '', value: '', description: '' })
      } else {
        const error = await response.json()
        alert(`Failed to update: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to update: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this secret? This cannot be undone.')) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/secrets/${id}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        await fetchSecrets()
      } else {
        const error = await response.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to delete: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleEdit = (secret: Secret) => {
    setEditingSecret(secret)
    setFormData({
      name: secret.name,
      value: '',
      description: secret.description || '',
    })
  }

  const handleViewValue = async (secret: Secret) => {
    if (showValue === secret.id) {
      setShowValue(null)
      return
    }
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/secrets/${secret.id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setShowValue(data.value)
      }
    } catch (error) {
      console.error('Failed to fetch secret value:', error)
    }
  }

  const handleCopyValue = (value: string) => {
    navigator.clipboard.writeText(value)
    alert('Copied to clipboard!')
  }

  const handleCreate = () => {
    setFormData({ name: '', value: '', description: '' })
    // In a real app, you'd open a dialog here
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Secrets Management</h1>
          <p className="text-muted-foreground mt-1">Manage encrypted secrets and API keys securely</p>
        </div>
        <Button onClick={() => { setFormData({ name: '', value: '', description: '' }) }} className="gap-2">
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
          Add Secret
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
            {secrets.map((secret) => (
              <div key={secret.id} className="bg-card border border-border rounded-lg p-6 hover:border-primary/50 transition-colors">
                <div className="flex items-start justify-between mb-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1">
                      <h3 className="font-semibold text-lg">{secret.name}</h3>
                      <Badge variant="secondary">{secret.id.slice(0, 8)}...</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground line-clamp-2">{secret.description || 'No description'}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="ghost" size="sm" onClick={() => setShowValue(showValue === secret.id ? null : secret.id)} className="gap-1">
                      {showValue === secret.id ? <Eye className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                      {showValue === secret.id ? 'Hide' : 'Show'}
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleCopyValue(secrets.find(s => s.id === showValue)?.value || '')} disabled={showValue !== secret.id} className="gap-1">
                      <Copy className="w-4 h-4" />
                      Copy
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => { setFormData({ name: '', value: '', description: '' }) }} className="gap-1">
                      <Edit className="w-4 h-4" />
                      Edit
                    </Button>
                    <Button variant="ghost" size="sm" variant="destructive" onClick={() => handleDelete(secret.id)} className="gap-1">
                      <Trash2 className="w-4 h-4" />
                      Delete
                    </Button>
                  </div>

                  {showValue === secret.id && (
                    <div className="mt-4 p-3 bg-muted/50 rounded-lg border border-border">
                      <div className="flex items-center justify-between mb-2">
                        <Label className="text-sm font-medium">Secret Value</Label>
                        <Button variant="ghost" size="sm" onClick={() => handleCopyValue(secrets.find(s => s.id === showValue)?.value || '')} className="gap-1">
                          <Copy className="w-4 h-4" />
                          Copy
                        </Button>
                      </div>
                      <div className="p-3 bg-background border border-border rounded-lg font-mono text-sm break-all">
                        {secrets.find(s => s.id === showValue)?.value || 'Loading...'}
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>

            {secrets.length === 0 && (
              <div className="text-center py-12">
                <svg className="w-12 h-12 mx-auto text-muted-foreground mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 11h.01" />
                </svg>
                <h3 className="text-lg font-medium mb-2">No secrets configured</h3>
                <p className="text-muted-foreground mb-4">Create your first secret to store API keys, passwords, and other sensitive data</p>
                <Button onClick={() => { /* would open create dialog */ }} className="gap-2">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>
                  Create Secret
                </Button>
              </div>
            )}
          </div>
        </>
      </div>

      {/* Create/Edit Dialog */}
      <div className="fixed inset-0 z-50 overflow-y-auto" style={{ display: 'block' }}>
        <div className="flex min-h-full items-center justify-center p-4">
          <div className="relative w-full max-w-md max-h-[90vh] overflow-auto rounded-lg bg-background p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold">Secret</h2>
              <button onClick={() => { setEditingSecret(null); setFormData({ name: '', value: '', description: '' }) }} className="text-muted-foreground hover:text-foreground">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" /></svg>
              </button>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); }} className="space-y-4 max-h-[70vh] overflow-y-auto">
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" value={formData.name} onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))} placeholder="e.g., OPENAI_API_KEY" required />
              </div>

              <div className="space-y-2">
                <Label htmlFor="value">Value</Label>
                <Input
                  id="value"
                  type="password"
                  value={formData.value}
                  onChange={(e) => setFormData(prev => ({ ...prev, value: e.target.value }))}
                  placeholder="Enter secret value"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                  placeholder="Optional description"
                  rows={3}
                />
              </div>

              <div className="flex justify-end gap-2 pt-4 border-t">
                <Button type="button" variant="outline" onClick={() => { setFormData({ name: '', value: '', description: '' }) }}>
                  Cancel
                </Button>
                <Button type="submit">
                  Create
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  )
}

export default SecretsPage
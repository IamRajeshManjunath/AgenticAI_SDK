'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Plus,
  Database,
  Trash2,
  Loader2,
} from 'lucide-react'
import useSWR from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useToast } from '@/hooks/use-toast'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/lib/auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface RAGSourceDTO {
  id: string
  name: string
  provider: string
  config: Record<string, unknown>
}

const fetcher = (url: string) => fetch(url, {
  headers: { 'Authorization': `Bearer ${useAuthStore.getState().token}` },
}).then((r) => { if (!r.ok) throw new Error('Failed to fetch'); return r.json() })

export default function RAGPage() {
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)
  const authHeaders = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }

  const { data: sources, error, isLoading, mutate } = useSWR<RAGSourceDTO[]>(
    token ? `${API_BASE_URL}/workflow/rag-sources` : null,
    fetcher
  )

  const [localSources, setLocalSources] = useState<RAGSourceDTO[]>([])
  const displaySources = sources || localSources

  const handleAdd = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/workflow/rag-sources`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ name: 'New RAG Source', provider: 'qdrant', config: {} }),
      })
      if (!res.ok) throw new Error('Failed to create')
      const data = await res.json()
      setLocalSources((prev) => [...prev, { id: data.id, name: data.name, provider: 'qdrant', config: {} }])
      mutate()
      toast({ title: 'RAG source created' })
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  const handleUpdate = async (id: string, updates: Partial<RAGSourceDTO>) => {
    try {
      const res = await fetch(`${API_BASE_URL}/workflow/rag-sources/${id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify(updates),
      })
      if (!res.ok) throw new Error('Failed to update')
      setLocalSources((prev) => prev.map((s) => (s.id === id ? { ...s, ...updates } : s)))
      mutate()
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/workflow/rag-sources/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to delete')
      setLocalSources((prev) => prev.filter((s) => s.id !== id))
      mutate()
      toast({ title: 'RAG source deleted' })
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  if (!token) {
    return (
      <DashboardLayout>
        <div className="p-8"><p className="text-muted-foreground">Sign in to manage RAG sources.</p></div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">RAG Sources</h1>
            <p className="text-muted-foreground mt-1">Configure knowledge bases for your agents</p>
          </div>
          <Button onClick={handleAdd} className="gap-2" disabled={isLoading}>
            <Plus className="w-4 h-4" />
            Add RAG Source
          </Button>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="p-6 text-center text-destructive">
              Failed to load RAG sources. Make sure the backend is running.
            </CardContent>
          </Card>
        )}

        {!isLoading && !error && displaySources.length === 0 && (
          <Card>
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                <Database className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-lg font-medium mb-2">No RAG sources configured</h3>
              <p className="text-muted-foreground mb-4">Add a knowledge base to give your agents context</p>
              <Button onClick={handleAdd} className="gap-2">
                <Plus className="w-4 h-4" />
                Add RAG Source
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displaySources.map((source, index) => (
            <motion.div
              key={source.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card>
                <CardContent className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="p-2 rounded-lg bg-primary/10">
                        <Database className="w-5 h-5 text-primary" />
                      </div>
                      <Input
                        value={source.name}
                        onChange={(e) => handleUpdate(source.id, { name: e.target.value })}
                        className="font-semibold text-base h-auto p-0 border-0 bg-transparent focus-visible:ring-0"
                      />
                    </div>
                    <AlertDialog>
                      <AlertDialogTrigger asChild>
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-8 w-8 p-0 text-destructive"
                        >
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>Delete RAG Source</AlertDialogTitle>
                          <AlertDialogDescription>
                            Delete "{source.name}"? This cannot be undone.
                          </AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>Cancel</AlertDialogCancel>
                          <AlertDialogAction onClick={() => handleDelete(source.id)}>Delete</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">Vector DB Provider</Label>
                    <Select
                      value={source.provider}
                      onValueChange={(v) => handleUpdate(source.id, { provider: v })}
                    >
                      <SelectTrigger className="mt-1">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="qdrant">Qdrant</SelectItem>
                        <SelectItem value="pinecone">Pinecone</SelectItem>
                        <SelectItem value="chroma">Chroma</SelectItem>
                        <SelectItem value="weaviate">Weaviate</SelectItem>
                        <SelectItem value="milvus">Milvus</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  )
}

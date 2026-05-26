'use client'

import { useState, useCallback } from 'react'
import { motion } from 'framer-motion'
import {
  Plus,
  Wrench,
  Trash2,
  Globe,
  Server,
  Loader2,
} from 'lucide-react'
import useSWR from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { useToast } from '@/hooks/use-toast'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useAuthStore } from '@/lib/auth-store'
import type { ToolConfig } from '@/lib/types'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface ToolDTO {
  id: string
  name: string
  description: string
  type: string
}

const fetcher = (url: string) => fetch(url, {
  headers: { 'Authorization': `Bearer ${useAuthStore.getState().token}` },
}).then((r) => { if (!r.ok) throw new Error('Failed to fetch'); return r.json() })

export default function ToolsPage() {
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)
  const authHeaders = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }

  const { data: tools, error, isLoading, mutate } = useSWR<ToolDTO[]>(
    token ? `${API_BASE_URL}/workflow/tools` : null,
    fetcher
  )

  const [localTools, setLocalTools] = useState<ToolDTO[]>([])

  const displayTools = tools || localTools

  const handleAdd = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/workflow/tools`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ name: 'New Tool', description: '', type: 'api' }),
      })
      if (!res.ok) throw new Error('Failed to create tool')
      const data = await res.json()
      const newTool: ToolDTO = { id: data.id, name: data.name, description: '', type: 'api' }
      setLocalTools((prev) => [...prev, newTool])
      mutate()
      toast({ title: 'Tool created' })
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  const handleUpdate = async (id: string, updates: Partial<ToolDTO>) => {
    try {
      const res = await fetch(`${API_BASE_URL}/workflow/tools/${id}`, {
        method: 'PATCH',
        headers: authHeaders,
        body: JSON.stringify(updates),
      })
      if (!res.ok) throw new Error('Failed to update')
      setLocalTools((prev) => prev.map((t) => (t.id === id ? { ...t, ...updates } : t)))
      mutate()
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  const handleDelete = async (id: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/workflow/tools/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to delete')
      setLocalTools((prev) => prev.filter((t) => t.id !== id))
      mutate()
      toast({ title: 'Tool deleted' })
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

  if (!token) {
    return (
      <DashboardLayout>
        <div className="p-8"><p className="text-muted-foreground">Sign in to manage tools.</p></div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Global Tools</h1>
            <p className="text-muted-foreground mt-1">Configure external tools and APIs for your agents</p>
          </div>
          <Button onClick={handleAdd} className="gap-2" disabled={isLoading}>
            <Plus className="w-4 h-4" />
            Add Tool
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
              Failed to load tools. Make sure the backend is running.
            </CardContent>
          </Card>
        )}

        {!isLoading && !error && displayTools.length === 0 && (
          <Card>
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                <Wrench className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-lg font-medium mb-2">No tools configured</h3>
              <p className="text-muted-foreground mb-4">Add your first tool to enable agent capabilities</p>
              <Button onClick={handleAdd} className="gap-2">
                <Plus className="w-4 h-4" />
                Add Tool
              </Button>
            </CardContent>
          </Card>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {displayTools.map((tool, index) => (
            <motion.div
              key={tool.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <ToolCard
                tool={tool}
                onUpdate={(updates) => handleUpdate(tool.id, updates)}
                onDelete={() => handleDelete(tool.id)}
              />
            </motion.div>
          ))}
        </div>
      </div>
    </DashboardLayout>
  )
}

interface ToolCardProps {
  tool: ToolDTO
  onUpdate: (updates: Partial<ToolDTO>) => void
  onDelete: () => void
}

function ToolCard({ tool, onUpdate, onDelete }: ToolCardProps) {
  const getTypeIcon = () => {
    switch (tool.type) {
      case 'api': return <Globe className="w-5 h-5 text-primary" />
      case 'function': return <Server className="w-5 h-5 text-success" />
      case 'mcp': return <Wrench className="w-5 h-5 text-warning" />
      default: return <Wrench className="w-5 h-5" />
    }
  }

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-card">{getTypeIcon()}</div>
            <div className="flex-1 min-w-0">
              <Input
                value={tool.name}
                onChange={(e) => onUpdate({ name: e.target.value })}
                className="font-semibold text-base h-auto p-0 border-0 bg-transparent focus-visible:ring-0"
                placeholder="Tool Name"
              />
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
          <Label className="text-xs text-muted-foreground">Type</Label>
          <Select
            value={tool.type}
            onValueChange={(value) => onUpdate({ type: value })}
          >
            <SelectTrigger className="mt-1">
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
            className="mt-1 h-20 resize-none"
            placeholder="Describe what this tool does..."
          />
        </div>
      </CardContent>
    </Card>
  )
}

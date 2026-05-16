'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  Plus,
  Wrench,
  Trash2,
  Globe,
  Server,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { ToolConfig } from '@/lib/types'

export default function ToolsPage() {
  const { globalTools, addGlobalTool, updateGlobalTool, deleteGlobalTool } =
    useWorkflowStore()

  const handleAddTool = () => {
    addGlobalTool({
      name: 'New Tool',
      description: '',
      type: 'api',
      api_endpoint: '',
      method: 'GET',
      api_key_env_var: '',
    })
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Global Tools</h1>
            <p className="text-muted-foreground mt-1">
              Configure external tools and APIs for your agents to use
            </p>
          </div>
          <Button onClick={handleAddTool} className="gap-2 glow-primary-sm">
            <Plus className="w-4 h-4" />
            Add Tool
          </Button>
        </div>

        {/* Tools Grid */}
        {globalTools.length === 0 ? (
          <Card className="glass-card">
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                <Wrench className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-lg font-medium mb-2">No tools configured</h3>
              <p className="text-muted-foreground mb-4">
                Add your first tool to enable agent capabilities
              </p>
              <Button onClick={handleAddTool} className="gap-2">
                <Plus className="w-4 h-4" />
                Add Tool
              </Button>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {globalTools.map((tool, index) => (
              <motion.div
                key={tool.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.1 }}
              >
                <ToolCard
                  tool={tool}
                  onUpdate={(updates) => updateGlobalTool(tool.id, updates)}
                  onDelete={() => deleteGlobalTool(tool.id)}
                />
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </DashboardLayout>
  )
}

interface ToolCardProps {
  tool: ToolConfig
  onUpdate: (updates: Partial<ToolConfig>) => void
  onDelete: () => void
}

function ToolCard({ tool, onUpdate, onDelete }: ToolCardProps) {
  const getTypeIcon = () => {
    switch (tool.type) {
      case 'api':
        return <Globe className="w-5 h-5 text-primary" />
      case 'function':
        return <Server className="w-5 h-5 text-success" />
      case 'mcp':
        return <Wrench className="w-5 h-5 text-warning" />
    }
  }

  return (
    <Card className="glass-card">
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
            onValueChange={(value) => onUpdate({ type: value as ToolConfig['type'] })}
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

        {tool.type === 'api' && (
          <>
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <Label className="text-xs text-muted-foreground">Endpoint</Label>
                <Input
                  value={tool.api_endpoint || ''}
                  onChange={(e) => onUpdate({ api_endpoint: e.target.value })}
                  className="mt-1"
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
                  <SelectTrigger className="mt-1">
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
                className="mt-1 font-mono text-sm"
                placeholder="TOOL_API_KEY"
              />
            </div>
          </>
        )}
      </CardContent>
    </Card>
  )
}

'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  Play,
  CheckCircle,
  XCircle,
  AlertTriangle,
  Clock,
  Filter,
  Search,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { useWorkflowStore } from '@/lib/store'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

interface ActivityItem {
  id: string
  type: 'run' | 'hitl' | 'error' | 'config'
  status: 'completed' | 'failed' | 'pending' | 'running'
  workflowName: string
  workflowId: string
  message: string
  timestamp: number
  duration?: number
  cost?: number
}

// Mock activity data
const mockActivity: ActivityItem[] = [
  {
    id: '1',
    type: 'run',
    status: 'completed',
    workflowName: 'Customer Support Bot',
    workflowId: 'w1',
    message: 'Workflow completed successfully',
    timestamp: Date.now() - 1000 * 60 * 5,
    duration: 2340,
    cost: 0.023,
  },
  {
    id: '2',
    type: 'hitl',
    status: 'pending',
    workflowName: 'Email Automation',
    workflowId: 'w2',
    message: 'Human approval requested for send_email action',
    timestamp: Date.now() - 1000 * 60 * 15,
  },
  {
    id: '3',
    type: 'error',
    status: 'failed',
    workflowName: 'Data Analysis Pipeline',
    workflowId: 'w3',
    message: 'API rate limit exceeded',
    timestamp: Date.now() - 1000 * 60 * 30,
    duration: 15000,
  },
  {
    id: '4',
    type: 'run',
    status: 'completed',
    workflowName: 'Research Assistant',
    workflowId: 'w4',
    message: 'Workflow completed with 3 agents',
    timestamp: Date.now() - 1000 * 60 * 60,
    duration: 8500,
    cost: 0.089,
  },
  {
    id: '5',
    type: 'config',
    status: 'completed',
    workflowName: 'Customer Support Bot',
    workflowId: 'w1',
    message: 'Workflow configuration updated',
    timestamp: Date.now() - 1000 * 60 * 90,
  },
  {
    id: '6',
    type: 'run',
    status: 'running',
    workflowName: 'Content Generator',
    workflowId: 'w5',
    message: 'Workflow in progress',
    timestamp: Date.now() - 1000 * 60 * 2,
  },
]

export default function ActivityPage() {
  const [filter, setFilter] = useState<string>('all')
  const [search, setSearch] = useState('')

  const filteredActivity = mockActivity.filter((item) => {
    const matchesFilter = filter === 'all' || item.status === filter
    const matchesSearch =
      search === '' ||
      item.workflowName.toLowerCase().includes(search.toLowerCase()) ||
      item.message.toLowerCase().includes(search.toLowerCase())
    return matchesFilter && matchesSearch
  })

  const getStatusIcon = (status: ActivityItem['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-success" />
      case 'failed':
        return <XCircle className="w-4 h-4 text-destructive" />
      case 'pending':
        return <AlertTriangle className="w-4 h-4 text-warning" />
      case 'running':
        return <Play className="w-4 h-4 text-primary animate-pulse" />
    }
  }

  const getTypeColor = (type: ActivityItem['type']) => {
    switch (type) {
      case 'run':
        return 'bg-primary/20 text-primary'
      case 'hitl':
        return 'bg-warning/20 text-warning'
      case 'error':
        return 'bg-destructive/20 text-destructive'
      case 'config':
        return 'bg-chart-2/20 text-chart-2'
    }
  }

  const formatTime = (timestamp: number) => {
    const diff = Date.now() - timestamp
    if (diff < 1000 * 60) return 'Just now'
    if (diff < 1000 * 60 * 60) return `${Math.floor(diff / (1000 * 60))}m ago`
    if (diff < 1000 * 60 * 60 * 24) return `${Math.floor(diff / (1000 * 60 * 60))}h ago`
    return new Date(timestamp).toLocaleDateString()
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Activity Log</h1>
            <p className="text-muted-foreground mt-1">
              Track workflow executions and events
            </p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search activity..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
          <Select value={filter} onValueChange={setFilter}>
            <SelectTrigger className="w-full sm:w-48">
              <Filter className="w-4 h-4 mr-2" />
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Activity</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Activity List */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="w-5 h-5" />
              Recent Activity
            </CardTitle>
          </CardHeader>
          <CardContent>
            {filteredActivity.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <Activity className="w-12 h-12 mx-auto mb-4 opacity-50" />
                <p>No activity found</p>
              </div>
            ) : (
              <div className="space-y-4">
                {filteredActivity.map((item, index) => (
                  <motion.div
                    key={item.id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: index * 0.05 }}
                    className={cn(
                      'flex items-start gap-4 p-4 rounded-lg transition-colors',
                      'bg-secondary/30 hover:bg-secondary/50'
                    )}
                  >
                    <div className="mt-1">{getStatusIcon(item.status)}</div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-medium">{item.workflowName}</span>
                        <Badge variant="secondary" className={getTypeColor(item.type)}>
                          {item.type.toUpperCase()}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        {item.message}
                      </p>
                      <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" />
                          {formatTime(item.timestamp)}
                        </span>
                        {item.duration && (
                          <span>Duration: {(item.duration / 1000).toFixed(1)}s</span>
                        )}
                        {item.cost && <span>Cost: ${item.cost.toFixed(3)}</span>}
                      </div>
                    </div>
                    <Button variant="ghost" size="sm" asChild>
                      <a href={`/observability/${item.workflowId}`}>View</a>
                    </Button>
                  </motion.div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

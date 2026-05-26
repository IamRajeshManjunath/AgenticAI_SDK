'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  Activity,
  Play,
  CheckCircle,
  XCircle,
  Clock,
  Search,
  Loader2,
} from 'lucide-react'
import useSWR from 'swr'
import Link from 'next/link'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { useAuthStore } from '@/lib/auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface ActivityDTO {
  id: string
  action: string
  details: Record<string, unknown>
  timestamp: string
}

const fetcher = (url: string) => fetch(url, {
  headers: { 'Authorization': `Bearer ${useAuthStore.getState().token}` },
}).then((r) => { if (!r.ok) throw new Error('Failed to fetch'); return r.json() })

function getActivityIcon(action: string) {
  if (action.includes('created') || action.includes('completed')) return <CheckCircle className="w-4 h-4 text-success" />
  if (action.includes('failed') || action.includes('deleted')) return <XCircle className="w-4 h-4 text-destructive" />
  if (action.includes('running')) return <Play className="w-4 h-4 text-primary" />
  return <Clock className="w-4 h-4 text-muted-foreground" />
}

function getActivityColor(action: string) {
  if (action.includes('created') || action.includes('completed')) return 'bg-success/10 text-success'
  if (action.includes('failed') || action.includes('deleted')) return 'bg-destructive/10 text-destructive'
  if (action.includes('running')) return 'bg-primary/10 text-primary'
  return 'bg-secondary text-secondary-foreground'
}

export default function ActivityPage() {
  const token = useAuthStore((s) => s.token)
  const [search, setSearch] = useState('')

  const { data: logs, error, isLoading } = useSWR<ActivityDTO[]>(
    token ? `${API_BASE_URL}/workflow/activity` : null,
    fetcher,
    { refreshInterval: 10000 }
  )

  const filtered = (logs || []).filter((log) =>
    !search || log.action.toLowerCase().includes(search.toLowerCase())
  )

  if (!token) {
    return (
      <DashboardLayout>
        <div className="p-8"><p className="text-muted-foreground">Sign in to view activity.</p></div>
      </DashboardLayout>
    )
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-6">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold">Activity Log</h1>
            <p className="text-muted-foreground mt-1">Track all actions across your workspace</p>
          </div>
          <div className="relative w-full md:w-64">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input
              placeholder="Search activity..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>

        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {error && (
          <Card className="border-destructive/50">
            <CardContent className="p-6 text-center text-destructive">
              Failed to load activity log. Make sure the backend is running.
            </CardContent>
          </Card>
        )}

        {!isLoading && !error && filtered.length === 0 && (
          <Card>
            <CardContent className="p-12 text-center">
              <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                <Activity className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-lg font-medium mb-2">No activity found</h3>
              <p className="text-muted-foreground">
                {search ? 'No results match your search' : 'Activity will appear as you use the platform'}
              </p>
            </CardContent>
          </Card>
        )}

        <div className="space-y-3">
          {filtered.map((log, i) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.02 }}
            >
              <Card className="hover:bg-accent/50 transition-colors">
                <CardContent className="p-4 flex items-center gap-4">
                  <div className="shrink-0">{getActivityIcon(log.action)}</div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="outline" className={getActivityColor(log.action)}>
                        {log.action}
                      </Badge>
                      <span className="text-sm text-muted-foreground">
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'Unknown'}
                      </span>
                    </div>
                    {log.details?.resource_name && (
                      <p className="text-sm mt-1 truncate">
                        {String(log.details.resource_name)}
                      </p>
                    )}
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

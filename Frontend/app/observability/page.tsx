'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  Activity,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  DollarSign,
  Zap,
  ArrowRight,
  AlertCircle,
  Eye,
} from 'lucide-react'
import useSWR from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { useAuthStore } from '@/lib/auth-store'
import { traceApi } from '@/lib/api'
import type { TraceSummary } from '@/lib/types'

const fetcher = async (): Promise<TraceSummary[]> => {
  const res = await traceApi.list()
  if (res.error) throw new Error(res.error)
  return res.data ?? []
}

const statusIcon = (status: string) => {
  switch (status) {
    case 'completed':
      return <CheckCircle2 className="w-4 h-4 text-success" />
    case 'failed':
      return <XCircle className="w-4 h-4 text-destructive" />
    case 'running':
      return <Loader2 className="w-4 h-4 text-primary animate-spin" />
    default:
      return <Clock className="w-4 h-4 text-muted-foreground" />
  }
}

const statusBadge = (status: string) => {
  switch (status) {
    case 'completed':
      return 'default'
    case 'failed':
      return 'destructive'
    case 'running':
      return 'secondary'
    default:
      return 'outline'
  }
}

export default function ObservabilityListPage() {
  const token = useAuthStore((s) => s.token)
  const [search, setSearch] = useState('')

  const { data: traces, error, isLoading } = useSWR<TraceSummary[]>(
    token ? 'traces-list' : null,
    fetcher,
    { refreshInterval: 5000 }
  )

  const filtered = traces?.filter((t) =>
    t.workflow_name?.toLowerCase().includes(search.toLowerCase()) ||
    t.trace_id?.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Observability</h1>
          <p className="text-muted-foreground mt-1">
            Monitor all workflow executions across your workspace
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="relative flex-1 max-w-sm">
            <Input
              placeholder="Search by workflow name or trace ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8"
            />
            <Activity className="absolute left-2.5 top-2.5 w-4 h-4 text-muted-foreground" />
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-6 h-6 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <Card className="glass-card">
            <CardContent className="py-12 text-center text-muted-foreground">
              <AlertCircle className="w-12 h-12 mx-auto mb-4 opacity-50" />
              <p>Failed to load traces</p>
            </CardContent>
          </Card>
        ) : !filtered?.length ? (
          <Card className="glass-card">
            <CardContent className="py-16 text-center">
              <Activity className="w-16 h-16 mx-auto mb-4 text-muted-foreground/50" />
              <h3 className="text-lg font-medium mb-2">No traces yet</h3>
              <p className="text-muted-foreground max-w-md mx-auto">
                Run a workflow to see execution traces here.
              </p>
            </CardContent>
          </Card>
        ) : (
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Activity className="w-5 h-5" />
                Execution Traces
                <Badge variant="secondary" className="ml-2">{filtered.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Workflow</TableHead>
                    <TableHead>Trace ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Cost</TableHead>
                    <TableHead>Tokens</TableHead>
                    <TableHead>Latency</TableHead>
                    <TableHead>Started</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.map((trace) => (
                    <TableRow key={trace.trace_id}>
                      <TableCell className="font-medium">{trace.workflow_name || trace.workflow_id}</TableCell>
                      <TableCell className="font-mono text-xs text-muted-foreground">
                        {trace.trace_id?.substring(0, 8)}...
                      </TableCell>
                      <TableCell>
                        <Badge variant={statusBadge(trace.status) as 'default' | 'destructive' | 'secondary' | 'outline'}>
                          <span className="flex items-center gap-1">
                            {statusIcon(trace.status)}
                            {trace.status}
                          </span>
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="flex items-center gap-1">
                          <DollarSign className="w-3 h-3 text-muted-foreground" />
                          ${trace.total_cost?.toFixed(4)}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">
                        <span className="flex items-center gap-1">
                          <Zap className="w-3 h-3 text-muted-foreground" />
                          {trace.total_tokens?.toLocaleString()}
                        </span>
                      </TableCell>
                      <TableCell className="text-sm">{trace.latency_ms}ms</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {trace.started_at ? new Date(trace.started_at).toLocaleString() : '-'}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button variant="outline" size="sm" asChild>
                          <Link href={`/observability/${trace.workflow_id}`}>
                            <Eye className="w-3 h-3 mr-1" />
                            Details
                          </Link>
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </DashboardLayout>
  )
}

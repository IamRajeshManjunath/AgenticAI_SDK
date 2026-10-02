'use client'

import { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Filter, X, CheckCircle2, XCircle, Clock, AlertTriangle } from 'lucide-react'
import { HITLApprovalCard } from '@/components/hitl-approval-card'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'

interface HITLApproval {
  id: string
  agent_id: string
  agent_name?: string
  proposed_action: string
  proposed_output: string
  timestamp: number
  status: 'pending' | 'approved' | 'rejected'
}

export default function HITLDashboard() {
  const [pendingApprovals, setPendingApprovals] = useState<any[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved' | 'rejected'>('pending')
  const { token } = useAuthStore()

  const fetchApprovals = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workflow/hitl/pending`, {
        headers: {
          'Authorization': `Bearer ${useAuthStore.getState().token}`,
        },
      })
      if (response.ok) {
        const data = await response.json()
        setPendingApprovals(data)
      }
    } catch (error) {
      console.error('Failed to fetch approvals:', error)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    fetchApprovals()
  }, [filter])

  const filteredApprovals = pendingApprovals.filter((a) => {
    if (filter === 'all') return true
    return a.status === filter
  })

  const stats = {
    total: pendingApprovals.length,
    pending: pendingApprovals.filter(a => a.status === 'pending').length,
    approved: pendingApprovals.filter(a => a.status === 'approved').length,
    rejected: pendingApprovals.filter(a => a.status === 'rejected').length,
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">HITL Approvals</h1>
          <p className="text-muted-foreground mt-1">Review and approve human-in-the-loop requests</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchApprovals}
            disabled={isLoading}
            className="px-4 py-2 rounded-lg bg-primary text-primary-foreground gap-2 flex items-center"
            disabled={isLoading}
          >
            <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-card border border-border rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-muted-foreground">Total</p>
              <p className="text-2xl font-bold">{pendingApprovals.length}</p>
            </div>
            <div className="p-2 rounded-lg bg-muted">
              <svg className="w-5 h-5 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
              </svg>
            </div>
          </div>
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending</p>
                <p className="text-2xl font-bold text-yellow-500">{pendingApprovals.filter(a => a.status === 'pending').length}</p>
              </div>
              <div className="p-2 rounded-lg bg-yellow-100">
                <svg className="w-5 h-5 text-yellow-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Approved</p>
                  <p className="text-2xl font-bold text-green-500">{pendingApprovals.filter(a => a.status === 'approved').length}</p>
                </div>
                <div className="p-2 rounded-lg bg-green-100">
                  <svg className="w-5 h-5 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
              </div>
            </div>
            <div className="bg-card border border-border rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">Rejected</p>
                  <p className="text-2xl font-bold text-red-500">{pendingApprovals.filter(a => a.status === 'rejected').length}</p>
                </div>
                <div className="p-2 rounded-lg bg-red-100">
                  <svg className="w-5 h-5 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </div>
              </div>
            </div>
          </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6">
        {(['all', 'pending', 'approved', 'rejected'] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              filter === f
                ? 'bg-primary text-primary-foreground shadow-sm'
                : 'bg-muted hover:bg-muted/50 text-muted-foreground'
            }`}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            {f !== 'all' && (
              <span className="ml-2 px-2 py-0.5 text-xs bg-primary/20 text-primary rounded-full">
                {pendingApprovals.filter(a => a.status === f).length}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Approvals List */}
      <div className="space-y-4">
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
        ) : filteredApprovals.length === 0 ? (
          <div className="text-center py-12">
            <svg className="w-12 h-12 mx-auto text-muted-foreground mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 11l-2 2-4-4m-6 11l-2-2 4-4m-6 11l-2-2 4-4" />
            </svg>
            <h3 className="text-lg font-medium mb-2">No approvals found</h3>
            <p className="text-muted-foreground">All caught up! No {filter} approvals at the moment.</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredApprovals.map((approval) => (
              <ApprovalCard
                key={approval.id}
                request={{
                  ...approval,
                  agent_name: approval.agent_name || approval.agent_id,
                }}
                onUpdate={fetchApprovals}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default HITLDashboard
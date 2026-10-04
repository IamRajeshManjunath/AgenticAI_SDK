'use client'

import useSWR from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { CreditCard, Check, Zap, Crown, Building2, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/lib/auth-store'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

interface PlanDTO {
  id: string
  name: string
  tokens_per_month: number
  max_workflows: number
  max_api_keys: number
  max_team_members: number
  features: Record<string, boolean>
  price_cents: number
}

interface UsageDTO {
  plan: string
  tokens_used: number
  tokens_limit: number
  workflows_count: number
  workflows_limit: number
  cost_incurred: number
  cost_limit: number
  period_start: string
  period_end: string
}

const fetcher = (url: string) => fetch(url, {
  headers: { 'Authorization': `Bearer ${useAuthStore.getState().token}` },
}).then((r) => { if (!r.ok) throw new Error('Failed to fetch'); return r.json() })

export default function BillingPage() {
  const token = useAuthStore((s) => s.token)

  const { data: usage, isLoading: usageLoading, mutate: mutateUsage } = useSWR<UsageDTO>(
    token ? `${API_BASE_URL}/billing/usage` : null,
    fetcher,
    { refreshInterval: 30000 }
  )

  const { data: plans, isLoading: plansLoading } = useSWR<PlanDTO[]>(
    token ? `${API_BASE_URL}/billing/plans` : null,
    fetcher
  )

  if (!token) {
    return (
      <DashboardLayout>
        <div className="p-8"><p className="text-muted-foreground">Sign in to manage billing.</p></div>
      </DashboardLayout>
    )
  }

  const planIcons: Record<string, React.ElementType> = {
    Starter: Zap,
    Pro: Crown,
    Enterprise: Building2,
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Billing</h1>
          <p className="text-muted-foreground mt-1">Manage your subscription and usage</p>
        </div>
        <div role="status" className="rounded-lg border border-amber-500/30 bg-amber-500/5 px-4 py-3 text-sm text-muted-foreground">
          Subscription changes and the billing portal are unavailable because billing is not configured for this deployment.
        </div>

        {/* Current Usage */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Current Usage
            </CardTitle>
            <CardDescription>
              {usage
                ? `Plan: ${usage.plan} — Resets ${usage.period_end ? new Date(usage.period_end).toLocaleDateString() : 'N/A'}`
                : 'Loading usage...'}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {usageLoading ? (
              <div className="flex justify-center py-4"><Loader2 className="w-5 h-5 animate-spin" /></div>
            ) : usage ? (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Tokens Used</span>
                    <span className="font-medium">
                      {(usage.tokens_used / 1000).toFixed(0)}K / {(usage.tokens_limit / 1000).toFixed(0)}K
                    </span>
                  </div>
                  <Progress value={(usage.tokens_used / usage.tokens_limit) * 100} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Workflows</span>
                    <span className="font-medium">{usage.workflows_count} / {usage.workflows_limit}</span>
                  </div>
                  <Progress value={(usage.workflows_count / usage.workflows_limit) * 100} className="h-2" />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">Cost</span>
                    <span className="font-medium">${usage.cost_incurred.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground">Could not load usage data.</p>
            )}
          </CardContent>
        </Card>

        {/* Plans */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Available Plans</h2>
          {plansLoading ? (
            <div className="flex justify-center py-8"><Loader2 className="w-5 h-5 animate-spin" /></div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {(plans || []).map((plan) => {
                const Icon = planIcons[plan.name] || Zap
                const isCurrentPlan = usage?.plan === plan.name
                return (
                  <Card
                    key={plan.id}
                    className={`relative ${isCurrentPlan ? 'border-primary' : plan.name === 'Pro' ? 'border-primary/50' : ''}`}
                  >
                    {plan.name === 'Pro' && !isCurrentPlan && (
                      <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                        <Badge className="bg-primary">Most Popular</Badge>
                      </div>
                    )}
                    <CardHeader className="text-center pt-8">
                      <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                        <Icon className="w-6 h-6 text-primary" />
                      </div>
                      <CardTitle>{plan.name}</CardTitle>
                      <div className="mt-2">
                        <span className="text-3xl font-bold">${plan.price_cents / 100}</span>
                        <span className="text-muted-foreground">/month</span>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <ul className="space-y-2">
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="w-4 h-4 text-success shrink-0" />
                          {(plan.tokens_per_month / 1000000).toFixed(0)}M tokens/month
                        </li>
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="w-4 h-4 text-success shrink-0" />
                          {plan.max_workflows} workflows
                        </li>
                        <li className="flex items-center gap-2 text-sm">
                          <Check className="w-4 h-4 text-success shrink-0" />
                          {plan.max_team_members > 1 ? `Up to ${plan.max_team_members} team members` : '1 seat'}
                        </li>
                        {Object.entries(plan.features || {}).map(([key, val]) =>
                          val ? (
                            <li key={key} className="flex items-center gap-2 text-sm">
                              <Check className="w-4 h-4 text-success shrink-0" />
                              {key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase())}
                            </li>
                          ) : null
                        )}
                      </ul>
                      <Button
                        className="w-full"
                        variant={isCurrentPlan ? 'secondary' : 'default'}
                        disabled
                      >
                        {isCurrentPlan ? 'Current Plan' : 'Checkout unavailable'}
                      </Button>
                    </CardContent>
                  </Card>
                )
              })}
            </div>
          )}
        </div>

        {/* Payment Method */}
        <Card>
          <CardHeader>
            <CardTitle>Manage Subscription</CardTitle>
            <CardDescription>The billing portal is unavailable until billing is configured.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button disabled variant="outline">
              <CreditCard className="w-4 h-4 mr-2" />
              Portal unavailable
            </Button>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

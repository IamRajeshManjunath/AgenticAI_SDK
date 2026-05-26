'use client'

import { useState } from 'react'
import useSWR from 'swr'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { CreditCard, Check, Zap, Crown, Building2, Loader2 } from 'lucide-react'
import { useAuthStore } from '@/lib/auth-store'
import { useToast } from '@/hooks/use-toast'

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
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)
  const authHeaders = { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }

  const { data: usage, isLoading: usageLoading, mutate: mutateUsage } = useSWR<UsageDTO>(
    token ? `${API_BASE_URL}/billing/usage` : null,
    fetcher,
    { refreshInterval: 30000 }
  )

  const { data: plans, isLoading: plansLoading } = useSWR<PlanDTO[]>(
    token ? `${API_BASE_URL}/billing/plans` : null,
    fetcher
  )

  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)

  const handleUpgrade = async (priceId: string) => {
    setCheckoutLoading(priceId)
    try {
      const res = await fetch(`${API_BASE_URL}/billing/create-checkout-session`, {
        method: 'POST',
        headers: authHeaders,
        body: JSON.stringify({ price_id: priceId, success_url: `${window.location.origin}/billing?success=true`, cancel_url: `${window.location.origin}/billing?canceled=true` }),
      })
      if (!res.ok) throw new Error('Failed to create checkout')
      const data = await res.json()
      if (data.url) {
        window.location.href = data.url
      }
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    } finally {
      setCheckoutLoading(null)
    }
  }

  const handlePortal = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/billing/portal`, {
        headers: { 'Authorization': `Bearer ${token}` },
      })
      if (!res.ok) throw new Error('Failed to open portal')
      const data = await res.json()
      if (data.url) window.location.href = data.url
    } catch (err) {
      toast({ title: 'Error', description: String(err), variant: 'destructive' })
    }
  }

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
                        disabled={isCurrentPlan || checkoutLoading === plan.stripe_price_id}
                        onClick={() => plan.stripe_price_id && handleUpgrade(plan.stripe_price_id)}
                      >
                        {checkoutLoading === plan.stripe_price_id ? (
                          <Loader2 className="w-4 h-4 animate-spin mr-2" />
                        ) : null}
                        {isCurrentPlan ? 'Current Plan' : 'Upgrade'}
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
            <CardDescription>View invoices, update payment method, or cancel</CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={handlePortal} variant="outline">
              <CreditCard className="w-4 h-4 mr-2" />
              Open Billing Portal
            </Button>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

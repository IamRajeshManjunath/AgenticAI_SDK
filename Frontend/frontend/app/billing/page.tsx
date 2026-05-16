'use client'

import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { CreditCard, Check, Zap, Crown, Building2 } from 'lucide-react'

export default function BillingPage() {
  const currentPlan = 'pro'
  const usage = {
    tokens: 850000,
    tokenLimit: 1000000,
    cost: 42.50,
    costLimit: 100,
    workflows: 12,
    workflowLimit: 50,
  }

  const plans = [
    {
      id: 'starter',
      name: 'Starter',
      price: '$0',
      period: '/month',
      description: 'For individuals and small projects',
      icon: Zap,
      features: [
        '100K tokens/month',
        '5 workflows',
        'Basic observability',
        'Community support',
      ],
    },
    {
      id: 'pro',
      name: 'Pro',
      price: '$49',
      period: '/month',
      description: 'For teams and growing businesses',
      icon: Crown,
      features: [
        '1M tokens/month',
        '50 workflows',
        'Advanced observability',
        'Priority support',
        'HITL controls',
        'Custom tools',
      ],
      popular: true,
    },
    {
      id: 'enterprise',
      name: 'Enterprise',
      price: 'Custom',
      period: '',
      description: 'For large organizations',
      icon: Building2,
      features: [
        'Unlimited tokens',
        'Unlimited workflows',
        'Full observability suite',
        'Dedicated support',
        'SSO & SAML',
        'Custom SLA',
        'On-premise option',
      ],
    },
  ]

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        {/* Header */}
        <div>
          <h1 className="text-3xl font-bold text-foreground">Billing</h1>
          <p className="text-muted-foreground mt-1">
            Manage your subscription and usage
          </p>
        </div>

        {/* Current Usage */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard className="w-5 h-5" />
              Current Usage
            </CardTitle>
            <CardDescription>
              Your usage for this billing period (resets in 12 days)
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Tokens Used</span>
                  <span className="font-medium">
                    {(usage.tokens / 1000).toFixed(0)}K / {(usage.tokenLimit / 1000).toFixed(0)}K
                  </span>
                </div>
                <Progress value={(usage.tokens / usage.tokenLimit) * 100} className="h-2" />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Cost</span>
                  <span className="font-medium">
                    ${usage.cost.toFixed(2)} / ${usage.costLimit}
                  </span>
                </div>
                <Progress value={(usage.cost / usage.costLimit) * 100} className="h-2" />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-muted-foreground">Workflows</span>
                  <span className="font-medium">
                    {usage.workflows} / {usage.workflowLimit}
                  </span>
                </div>
                <Progress
                  value={(usage.workflows / usage.workflowLimit) * 100}
                  className="h-2"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Plans */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Available Plans</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <Card
                key={plan.id}
                className={`glass-card relative ${
                  plan.id === currentPlan
                    ? 'border-primary glow-primary-sm'
                    : plan.popular
                    ? 'border-primary/50'
                    : ''
                }`}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary">Most Popular</Badge>
                  </div>
                )}
                <CardHeader className="text-center pt-8">
                  <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                    <plan.icon className="w-6 h-6 text-primary" />
                  </div>
                  <CardTitle>{plan.name}</CardTitle>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{plan.price}</span>
                    <span className="text-muted-foreground">{plan.period}</span>
                  </div>
                  <CardDescription className="mt-2">{plan.description}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <ul className="space-y-2">
                    {plan.features.map((feature, i) => (
                      <li key={i} className="flex items-center gap-2 text-sm">
                        <Check className="w-4 h-4 text-success shrink-0" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                  <Button
                    className={`w-full ${
                      plan.id === currentPlan
                        ? 'bg-secondary text-secondary-foreground hover:bg-secondary/80'
                        : 'glow-primary-sm'
                    }`}
                    disabled={plan.id === currentPlan}
                  >
                    {plan.id === currentPlan
                      ? 'Current Plan'
                      : plan.id === 'enterprise'
                      ? 'Contact Sales'
                      : 'Upgrade'}
                  </Button>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* Payment Method */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle>Payment Method</CardTitle>
            <CardDescription>Manage your payment information</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between p-4 rounded-lg bg-secondary">
              <div className="flex items-center gap-4">
                <div className="w-12 h-8 rounded bg-gradient-to-r from-primary to-chart-4 flex items-center justify-center text-white text-xs font-bold">
                  VISA
                </div>
                <div>
                  <p className="font-medium">Visa ending in 4242</p>
                  <p className="text-sm text-muted-foreground">Expires 12/2025</p>
                </div>
              </div>
              <Button variant="outline" size="sm">
                Update
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  )
}

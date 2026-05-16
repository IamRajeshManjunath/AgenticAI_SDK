'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  Plus,
  Workflow,
  TrendingUp,
  Clock,
  Zap,
  Activity,
  ArrowRight,
} from 'lucide-react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function HomePage() {
  const { workflows, createWorkflow, metrics } = useWorkflowStore()
  const workflowList = Object.values(workflows)

  const handleCreateWorkflow = () => {
    const name = `Workflow ${Object.keys(workflows).length + 1}`
    createWorkflow(name)
  }

  // Calculate aggregate stats
  const totalRuns = Object.keys(metrics).length
  const totalCost = Object.values(metrics).reduce((acc, m) => acc + (m?.total_cost || 0), 0)
  const avgLatency = Object.values(metrics).length > 0
    ? Object.values(metrics).reduce((acc, m) => acc + (m?.avg_latency_ms || 0), 0) / Object.values(metrics).length
    : 0

  const stats = [
    {
      title: 'Total Workflows',
      value: workflowList.length.toString(),
      icon: Workflow,
      color: 'text-primary',
      bgColor: 'bg-primary/10',
    },
    {
      title: 'Total Runs',
      value: totalRuns.toString(),
      icon: Zap,
      color: 'text-success',
      bgColor: 'bg-success/10',
    },
    {
      title: 'Total Cost',
      value: `$${totalCost.toFixed(2)}`,
      icon: TrendingUp,
      color: 'text-warning',
      bgColor: 'bg-warning/10',
    },
    {
      title: 'Avg Latency',
      value: `${avgLatency.toFixed(0)}ms`,
      icon: Clock,
      color: 'text-chart-2',
      bgColor: 'bg-chart-2/10',
    },
  ]

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Dashboard</h1>
            <p className="text-muted-foreground mt-1">
              Orchestrate and monitor your multi-agent workflows
            </p>
          </div>
          <Button onClick={handleCreateWorkflow} className="gap-2 glow-primary-sm">
            <Plus className="w-4 h-4" />
            Create Workflow
          </Button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="glass-card">
                <CardContent className="p-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm text-muted-foreground">{stat.title}</p>
                      <p className="text-2xl font-bold mt-1">{stat.value}</p>
                    </div>
                    <div className={cn(stat.bgColor, 'p-3 rounded-lg')}>
                      <stat.icon className={cn('w-5 h-5', stat.color)} />
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        {/* Recent Workflows */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold">Recent Workflows</h2>
            <Link
              href="/workflows"
              className="text-sm text-primary hover:underline flex items-center gap-1"
            >
              View all
              <ArrowRight className="w-4 h-4" />
            </Link>
          </div>

          {workflowList.length === 0 ? (
            <Card className="glass-card">
              <CardContent className="p-12 text-center">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-primary/10 flex items-center justify-center">
                  <Workflow className="w-8 h-8 text-primary" />
                </div>
                <h3 className="text-lg font-medium mb-2">No workflows yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first workflow to get started with multi-agent orchestration
                </p>
                <Button onClick={handleCreateWorkflow} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Create Workflow
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {workflowList.slice(0, 6).map((workflow, index) => (
                <motion.div
                  key={workflow.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + index * 0.1 }}
                >
                  <Link href={`/workflows/${workflow.id}`}>
                    <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer group">
                      <CardHeader className="pb-3">
                        <div className="flex items-start justify-between">
                          <div className="p-2 rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                            <Workflow className="w-5 h-5 text-primary" />
                          </div>
                          <span className="text-xs text-muted-foreground">
                            {workflow.agents.length} agents
                          </span>
                        </div>
                        <CardTitle className="text-base mt-3">{workflow.name}</CardTitle>
                        <CardDescription className="line-clamp-2">
                          {workflow.description || 'No description'}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="pt-0">
                        <div className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground">
                            Entry: {workflow.entry_point || 'Not set'}
                          </span>
                          <div className="flex items-center gap-1 text-primary">
                            <Activity className="w-4 h-4" />
                            <span>Edit</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  </Link>
                </motion.div>
              ))}
            </div>
          )}
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer">
              <CardContent className="p-6">
                <div className="flex items-center gap-4">
                  <div className="p-3 rounded-lg bg-primary/10">
                    <Plus className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-medium">Import Workflow</h3>
                    <p className="text-sm text-muted-foreground">
                      Import from JSON schema
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Link href="/tools">
              <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-success/10">
                      <Zap className="w-6 h-6 text-success" />
                    </div>
                    <div>
                      <h3 className="font-medium">Configure Tools</h3>
                      <p className="text-sm text-muted-foreground">
                        Set up global tool registry
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>

            <Link href="/rag">
              <Card className="glass-card hover:border-primary/50 transition-colors cursor-pointer">
                <CardContent className="p-6">
                  <div className="flex items-center gap-4">
                    <div className="p-3 rounded-lg bg-warning/10">
                      <Activity className="w-6 h-6 text-warning" />
                    </div>
                    <div>
                      <h3 className="font-medium">RAG Sources</h3>
                      <p className="text-sm text-muted-foreground">
                        Connect vector databases
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </Link>
          </div>
        </div>
      </div>
    </DashboardLayout>
  )
}

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(' ')
}

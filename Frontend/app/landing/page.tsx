'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import {
  Sparkles,
  Workflow,
  Bot,
  Shield,
  GitBranch,
  BarChart3,
  Check,
  ArrowRight,
  Star,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const fadeIn = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <header className="fixed top-0 w-full border-b border-border bg-background/80 backdrop-blur-md z-50">
        <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/landing" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center">
              <Sparkles className="w-5 h-5 text-primary" />
            </div>
            <span className="text-lg font-semibold">AgenticAI</span>
          </Link>
          <nav className="hidden md:flex items-center gap-6 text-sm text-muted-foreground">
            <Link href="/landing#features" className="hover:text-foreground transition-colors">Features</Link>
            <Link href="/blog" className="hover:text-foreground transition-colors">Blog</Link>
            <Link href="/templates" className="hover:text-foreground transition-colors">Templates</Link>
          </nav>
          <div className="flex items-center gap-3">
            <Link href="/login">
              <Button variant="ghost" size="sm">Sign In</Button>
            </Link>
            <Link href="/register">
              <Button size="sm" className="glow-primary-sm">Get Started Free</Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Hero */}
      <section className="pt-32 pb-20 px-4">
        <div className="max-w-5xl mx-auto text-center">
          <motion.div {...fadeIn} transition={{ duration: 0.6 }}>
            <Badge variant="secondary" className="mb-6 px-4 py-1.5 text-sm">
              <Star className="w-3.5 h-3.5 mr-1.5 text-primary" />
              Multi-Agent Workflow Platform
            </Badge>
            <h1 className="text-5xl md:text-7xl font-bold tracking-tight mb-6">
              Build multi-agent workflows
              <span className="text-primary block">in minutes, not weeks.</span>
            </h1>
            <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mx-auto mb-8">
              Describe your automation in plain English. AgenticAI compiles it into a production-grade,
              stateful multi-agent DAG powered by LangGraph.
            </p>
            <div className="flex items-center justify-center gap-4">
              <Link href="/register">
                <Button size="lg" className="text-base gap-2 glow-primary-sm">
                  Get Started Free <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Link href="/templates">
                <Button size="lg" variant="outline" className="text-base">
                  View Templates
                </Button>
              </Link>
            </div>
          </motion.div>
        </div>
      </section>

      {/* vs n8n Comparison */}
      <section className="py-20 px-4 bg-muted/50">
        <div className="max-w-5xl mx-auto">
          <motion.div {...fadeIn} transition={{ duration: 0.6 }}>
            <h2 className="text-3xl font-bold text-center mb-12">
              Why AgenticAI over n8n?
            </h2>
            <div className="grid md:grid-cols-2 gap-8">
              <Card className="border-primary/30">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="w-5 h-5 text-primary" />
                    AgenticAI
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3">
                    {[
                      'Native multi-agent orchestration (LangGraph)',
                      'JSON-in, workflow-out — no drag-and-drop needed',
                      'Built-in HITL, budget, PII, and schema guardrails',
                      'BYOK (bring your own LLM key) — no token markup',
                      'Autonomous agent loops with consensus voting',
                      'RAG-native: Qdrant, Pinecone, Chroma out of the box',
                    ].map((item) => (
                      <li key={item} className="flex items-start gap-2 text-sm">
                        <Check className="w-4 h-4 text-success shrink-0 mt-0.5" />
                        {item}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-muted-foreground">
                    <GitBranch className="w-5 h-5" />
                    n8n
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-3 text-sm text-muted-foreground">
                    {[
                      'Single-node execution per step',
                      'Visual drag-and-drop only',
                      'No built-in AI safety guardrails',
                      'Self-hosted or cloud markup on tokens',
                      'Linear pipeline, no agent loops',
                      'No native RAG integration',
                    ].map((item) => (
                      <li key={item} className="flex items-start gap-2">
                        <span className="text-destructive shrink-0 mt-0.5">✗</span>
                        {item}
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <motion.div {...fadeIn} transition={{ duration: 0.6 }}>
            <h2 className="text-3xl font-bold text-center mb-4">Everything you need</h2>
            <p className="text-muted-foreground text-center mb-12 max-w-xl mx-auto">
              A complete platform for building, running, and monitoring multi-agent AI workflows.
            </p>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                { icon: Bot, title: 'Master Agent', desc: 'Describe your automation in plain English. The Master Agent generates a complete, compilable workflow JSON.' },
                { icon: Workflow, title: 'Multi-Agent DAGs', desc: 'Coordinate multiple AI agents with conditional edges, sub-agents, and parallel execution via LangGraph.' },
                { icon: Shield, title: 'Enterprise Guardrails', desc: 'Budget limits, PII masking, prompt injection detection, schema enforcement, and human-in-the-loop.' },
                { icon: GitBranch, title: 'Human-in-the-Loop', desc: 'Pause execution at any node for human review. Approve, reject, or modify state before resuming.' },
                { icon: BarChart3, title: 'Full Observability', desc: 'Distributed tracing, token tracking, cost attribution per step, Prometheus metrics, and Grafana dashboards.' },
                { icon: Sparkles, title: 'BYOK Architecture', desc: 'Bring your own OpenAI/Anthropic key. No per-token markup — you pay only for the platform.' },
              ].map((feature) => (
                <Card key={feature.title} className="hover:border-primary/50 transition-colors">
                  <CardHeader>
                    <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center mb-3">
                      <feature.icon className="w-5 h-5 text-primary" />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                    <CardDescription>{feature.desc}</CardDescription>
                  </CardHeader>
                </Card>
              ))}
            </div>
          </motion.div>
        </div>
      </section>

      {/* Templates Preview */}
      <section className="py-20 px-4">
        <div className="max-w-5xl mx-auto">
          <motion.div {...fadeIn} transition={{ duration: 0.6 }}>
            <h2 className="text-3xl font-bold text-center mb-4">Start from a template</h2>
            <p className="text-muted-foreground text-center mb-12 max-w-xl mx-auto">
              Pre-built multi-agent workflows for common use cases. Import and customize in one click.
            </p>
            <div className="grid md:grid-cols-3 gap-6">
              {[
                { name: 'Customer Support Bot', desc: 'FAQ agent + human escalation with HITL checkpoint.' },
                { name: 'Research Pipeline', desc: 'Web search → summarization → report generation.' },
                { name: 'Content Review', desc: 'Write → policy check → human approval → publish.' },
              ].map((t) => (
                <Card key={t.name} className="hover:border-primary/50 transition-colors">
                  <CardHeader>
                    <CardTitle className="text-lg">{t.name}</CardTitle>
                    <CardDescription>{t.desc}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Link href="/templates">
                      <Button variant="outline" size="sm" className="gap-1">
                        Browse Templates <ArrowRight className="w-3 h-3" />
                      </Button>
                    </Link>
                  </CardContent>
                </Card>
              ))}
            </div>
          </motion.div>
        </div>
      </section>



      {/* Footer */}
      <footer className="border-t border-border py-12 px-4">
        <div className="max-w-5xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Sparkles className="w-4 h-4 text-primary" />
            &copy; {new Date().getFullYear()} AgenticAI. All rights reserved.
          </div>
          <div className="flex items-center gap-4">
            <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground">Blog</Link>
            <Link href="/templates" className="text-sm text-muted-foreground hover:text-foreground">Templates</Link>
            <Link href="/docs" className="text-sm text-muted-foreground hover:text-foreground">Docs</Link>
          </div>
        </div>
      </footer>
    </div>
  )
}

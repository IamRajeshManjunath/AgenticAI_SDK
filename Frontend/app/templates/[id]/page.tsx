'use client'

import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Sparkles, Users, GitBranch, Copy, Check, AlertTriangle } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { templates } from '@/lib/templates/data'
import { useState } from 'react'

const complexityColors: Record<string, string> = {
  beginner: 'bg-green-500/10 text-green-500 border-green-500/20',
  intermediate: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  advanced: 'bg-red-500/10 text-red-500 border-red-500/20',
}

export default function TemplateDetailPage() {
  const params = useParams()
  const router = useRouter()
  const template = templates.find((t) => t.id === params.id)
  const [copied, setCopied] = useState(false)

  if (!template) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Template not found</h1>
          <Link href="/templates"><Button variant="outline">Back to Templates</Button></Link>
        </div>
      </div>
    )
  }

  const handleCopy = async () => {
    await navigator.clipboard.writeText(JSON.stringify(template.workflow, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="max-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/landing" className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <span className="font-semibold">AgenticAI</span>
          </Link>
          <Link href="/templates" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> All Templates
          </Link>
        </div>
      </header>

      <main className="max-6xl mx-auto px-4 py-12">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <Badge variant="outline">{template.category}</Badge>
              <Badge variant="outline" className={complexityColors[template.complexity]}>{template.complexity}</Badge>
            </div>
            <h1 className="text-3xl font-bold mb-3">{template.name}</h1>
            <p className="text-lg text-muted-foreground mb-8">{template.description}</p>

            <div className="flex items-center gap-4 text-sm text-muted-foreground mb-8">
              <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {template.agentCount} agents</span>
              <span className="flex items-center gap-1"><GitBranch className="w-4 h-4" /> DAG Orchestration</span>
            </div>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between">
                <CardTitle className="text-lg">Workflow JSON</CardTitle>
                <Button variant="outline" size="sm" onClick={handleCopy} className="gap-2">
                  {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                  {copied ? 'Copied' : 'Copy'}
                </Button>
              </CardHeader>
              <CardContent>
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-xs leading-relaxed max-h-96 overflow-y-auto">
                  {JSON.stringify(template.workflow, null, 2)}
                </pre>
              </CardContent>
            </Card>
          </div>

          <div className="lg:col-span-1">
            <div className="sticky top-24 space-y-4">
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">Use this Template</CardTitle>
                  <CardDescription>
                    Import this workflow into your workspace and customize it.
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Link href="/register">
                    <Button className="w-full gap-2">
                      <Sparkles className="w-4 h-4" /> Try AgenticAI Free
                    </Button>
                  </Link>
                  <Button variant="outline" className="w-full gap-2" onClick={handleCopy}>
                    <Copy className="w-4 h-4" /> Copy JSON
                  </Button>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="text-sm font-medium">Requirements</CardTitle>
                </CardHeader>
                <CardContent className="text-sm space-y-2">
                  {template.workflow.rag_sources && (template.workflow.rag_sources as Array<Record<string, unknown>>).length > 0 && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <AlertTriangle className="w-4 h-4 text-yellow-500" /> Requires Qdrant vector DB
                    </div>
                  )}
                  {template.workflow.tools && (template.workflow.tools as Array<Record<string, unknown>>).length > 0 && (
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <AlertTriangle className="w-4 h-4 text-yellow-500" /> Requires API connections
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}

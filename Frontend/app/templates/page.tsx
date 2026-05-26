'use client'

import { useState } from 'react'
import Link from 'next/link'
import { motion } from 'framer-motion'
import { ArrowLeft, Sparkles, Search, GitBranch, Users, Zap, ChevronRight } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { templates } from '@/lib/templates/data'

const categories = Array.from(new Set(templates.map((t) => t.category)))

const complexityColors: Record<string, string> = {
  beginner: 'bg-green-500/10 text-green-500 border-green-500/20',
  intermediate: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
  advanced: 'bg-red-500/10 text-red-500 border-red-500/20',
}

export default function TemplatesPage() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState<string | null>(null)

  const filtered = templates.filter((t) => {
    const matchesSearch = t.name.toLowerCase().includes(search.toLowerCase()) || t.description.toLowerCase().includes(search.toLowerCase())
    const matchesCategory = !category || t.category === category
    return matchesSearch && matchesCategory
  })

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="max-6xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/landing" className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <span className="font-semibold">AgenticAI</span>
          </Link>
          <Link href="/landing" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
        </div>
      </header>

      <main className="max-6xl mx-auto px-4 py-12">
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold mb-3">Workflow Templates</h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Start faster with pre-built multi-agent workflows. Import, customize, and deploy in seconds.
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-4 mb-8 max-w-2xl mx-auto">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <Input placeholder="Search templates..." className="pl-10" value={search} onChange={(e) => setSearch(e.target.value)} />
          </div>
          <select
            className="px-4 py-2 rounded-md border border-input bg-background text-sm"
            value={category || ''}
            onChange={(e) => setCategory(e.target.value || null)}
          >
            <option value="">All Categories</option>
            {categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filtered.map((template, i) => (
            <motion.div
              key={template.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Card className="flex flex-col h-full hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="flex items-center gap-2 mb-2">
                    <Badge variant="outline" className="text-xs">{template.category}</Badge>
                    <Badge variant="outline" className={`text-xs ${complexityColors[template.complexity]}`}>{template.complexity}</Badge>
                  </div>
                  <CardTitle className="text-lg">{template.name}</CardTitle>
                  <CardDescription>{template.description}</CardDescription>
                </CardHeader>
                <CardContent className="flex-1">
                  <div className="flex items-center gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {template.agentCount} agents</span>
                    <span className="flex items-center gap-1"><GitBranch className="w-4 h-4" /> DAG</span>
                  </div>
                </CardContent>
                <CardFooter className="border-t border-border pt-4">
                  <Link href={`/templates/${template.id}`} className="w-full">
                    <Button variant="default" className="w-full gap-2">
                      Use Template <ChevronRight className="w-4 h-4" />
                    </Button>
                  </Link>
                </CardFooter>
              </Card>
            </motion.div>
          ))}
        </div>

        {filtered.length === 0 && (
          <div className="text-center py-12 text-muted-foreground">
            No templates found. Try a different search or category.
          </div>
        )}
      </main>
    </div>
  )
}

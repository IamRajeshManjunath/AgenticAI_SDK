'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { Calendar, User, ArrowLeft, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { blogPosts } from '@/lib/blog/posts'

export default function BlogPage() {
  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="max-w-4xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/landing" className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <span className="font-semibold">AgenticAI</span>
          </Link>
          <Link href="/landing" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-12">
        <h1 className="text-4xl font-bold mb-2">Blog</h1>
        <p className="text-muted-foreground mb-12">Thoughts on multi-agent orchestration, AI workflows, and building the future.</p>

        <div className="space-y-6">
          {blogPosts.map((post, i) => (
            <motion.div
              key={post.slug}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
            >
              <Link href={`/blog/${post.slug}`}>
                <Card className="hover:border-primary/50 transition-colors">
                  <CardHeader>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground mb-2">
                      <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{post.date}</span>
                      <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" />{post.author}</span>
                    </div>
                    <CardTitle className="text-xl mb-1">{post.title}</CardTitle>
                    <CardDescription className="text-base">{post.description}</CardDescription>
                    <div className="flex gap-2 mt-3">
                      {post.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">{tag}</Badge>
                      ))}
                    </div>
                  </CardHeader>
                </Card>
              </Link>
            </motion.div>
          ))}
        </div>
      </main>
    </div>
  )
}

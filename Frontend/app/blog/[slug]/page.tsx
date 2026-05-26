'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { Calendar, User, ArrowLeft, Sparkles } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { blogPosts } from '@/lib/blog/posts'

export default function BlogPostPage() {
  const params = useParams()
  const slug = params.slug as string
  const post = blogPosts.find((p) => p.slug === slug)

  if (!post) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Post not found</h1>
          <Link href="/blog"><Button variant="outline">Back to Blog</Button></Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="max-w-3xl mx-auto px-4 h-16 flex items-center justify-between">
          <Link href="/landing" className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-primary" />
            <span className="font-semibold">AgenticAI</span>
          </Link>
          <Link href="/blog" className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" /> All Posts
          </Link>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-12">
        <div className="flex items-center gap-3 text-sm text-muted-foreground mb-4">
          <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{post.date}</span>
          <span className="flex items-center gap-1"><User className="w-3.5 h-3.5" />{post.author}</span>
        </div>

        <h1 className="text-4xl font-bold mb-4">{post.title}</h1>
        <p className="text-lg text-muted-foreground mb-6">{post.description}</p>

        <div className="flex gap-2 mb-8">
          {post.tags.map((tag) => (
            <Badge key={tag} variant="secondary">{tag}</Badge>
          ))}
        </div>

        <article className="prose prose-invert max-w-none">
          {post.content.split('\n').map((line, i) => {
            if (line.startsWith('## ')) {
              return <h2 key={i} className="text-2xl font-bold mt-8 mb-4">{line.slice(3)}</h2>
            }
            if (line.startsWith('### ')) {
              return <h3 key={i} className="text-xl font-bold mt-6 mb-3">{line.slice(4)}</h3>
            }
            if (line.startsWith('| ') && line.endsWith(' |')) {
              return null
            }
            if (line.startsWith('|---')) {
              return null
            }
            if (line.startsWith('```')) {
              return null
            }
            if (line.trim() === '') {
              return <div key={i} className="h-4" />
            }
            if (line.startsWith('- **') && line.includes('**:')) {
              const parts = line.split('**:')
              const label = parts[0].replace('- **', '')
              const value = parts.slice(1).join('**:')
              return (
                <p key={i} className="mb-2">
                  <strong>{label}</strong>{value}
                </p>
              )
            }
            if (line.startsWith('- ')) {
              return <li key={i} className="ml-4 mb-1 list-disc">{line.slice(2)}</li>
            }
            if (line.startsWith('|')) {
              const cells = line.split('|').filter(Boolean).map((c) => c.trim())
              return (
                <span key={i} className="text-sm font-mono text-muted-foreground block">
                  {cells.join('  |  ')}
                </span>
              )
            }
            return <p key={i} className="mb-3 leading-relaxed">{line}</p>
          })}
        </article>

        <div className="mt-12 pt-8 border-t border-border">
          <Link href="/register">
            <Button size="lg" className="gap-2">
              Try AgenticAI Free <ArrowLeft className="w-4 h-4 rotate-180" />
            </Button>
          </Link>
        </div>
      </main>
    </div>
  )
}

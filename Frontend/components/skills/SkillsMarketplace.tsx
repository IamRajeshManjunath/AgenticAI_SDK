'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Switch } from '@/components/ui/switch'
import { cn } from '@/lib/utils'
import { Search, Plus, FileText, Settings, RefreshCw, Download, Trash2, Edit, ExternalLink, Filter, Plus, Eye, Star, StarOff, Download, Upload } from 'lucide-react'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface SkillMetadata {
  name: string
  description: string
  source: "local" | "git" | "s3" | "fleet"
  modified_at: string
  author?: string
  version?: string
  tags?: string[]
  downloads?: number
  rating?: number
  verified?: boolean
}

interface SkillManifest {
  name: string
  description: string
  frontmatter: Record<string, any>
  content: string
  files: Record<string, string>
  source: string
  modified_at: string
}

const mockRemoteSkills: SkillMetadata[] = [
  { name: "web-research", description: "Search the web and synthesize findings", source: "fleet", modified_at: "2024-01-15T10:00:00Z", author: "AgenticAI Team", version: "1.0.0", tags: ["search", "research", "web"], downloads: 1247, rating: 4.8, verified: true },
  { name: "code-generation", description: "Generate code from specifications", source: "fleet", modified_at: "2024-01-14T15:30:00Z", author: "AgenticAI Team", version: "1.1.0", tags: ["code", "generation", "python", "typescript"], downloads: 2341, rating: 4.9, verified: true },
  { name: "document-analysis", description: "Analyze documents for insights", source: "fleet", modified_at: "2024-01-13T09:00:00Z", author: "Community", version: "1.0.0", tags: ["analysis", "documents", "pdf"], downloads: 892, rating: 4.6, verified: true },
  { name: "data-processing", description: "Process and transform data", source: "fleet", modified_at: "2024-01-12T14:00:00Z", author: "Community", version: "1.2.0", tags: ["data", "etl", "pandas"], downloads: 567, rating: 4.4, verified: false },
  { name: "api-integration", description: "Integrate with external APIs", source: "fleet", modified_at: "2024-01-11T11:00:00Z", author: "AgenticAI Team", version: "1.0.0", tags: ["api", "rest", "graphql"], downloads: 834, rating: 4.7, verified: true },
  { name: "reasoning", description: "Multi-step reasoning and problem solving", source: "fleet", modified_at: "2024-01-10T16:00:00Z", author: "Community", version: "1.0.0", tags: ["reasoning", "chain-of-thought", "logic"], downloads: 421, rating: 4.5, verified: false },
  { name: "planning", description: "Create execution plans for complex tasks", source: "fleet", modified_at: "2024-01-09T10:00:00Z", author: "Community", version: "1.0.0", tags: ["planning", "task-decomposition"], downloads: 312, rating: 4.3, verified: false },
  { name: "sentiment-analysis", description: "Analyze sentiment in text", source: "fleet", modified_at: "2024-01-08T12:00:00Z", author: "Community", version: "1.0.0", tags: ["nlp", "sentiment", "classification"], downloads: 234, rating: 4.2, verified: false },
  { name: "image-analysis", description: "Analyze images and extract information", source: "fleet", modified_at: "2024-01-07T09:00:00Z", author: "Community", version: "1.0.0", tags: ["vision", "image", "ocr"], downloads: 189, rating: 4.1, verified: false },
  { name: "sql-query", description: "Generate and execute SQL queries", source: "fleet", modified_at: "2024-01-06T14:00:00Z", author: "Community", version: "1.1.0", tags: ["sql", "database", "query"], downloads: 456, rating: 4.5, verified: true },
];

export default function SkillsMarketplace() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedSource, setSelectedSource] = useState<string>("all")
  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [selectedSkill, setSelectedSkill] = useState<any>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [skills, setSkills] = useState<typeof mockRemoteSkills>(mockRemoteSkills)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    fetchSkills()
  }, [])

  const fetchSkills = async () => {
    setLoading(true)
    try {
      // In production, this would call the API
      // const response = await fetch("/api/v1/skills/marketplace");
      // const data = await response.json();
      // setSkills(data.skills);
    } catch (error) {
      console.error("Failed to fetch skills:", error)
    } finally {
      setLoading(false)
    }
  }

  const filteredSkills = skills.filter(skill => {
    if (selectedSource !== "all" && skill.source !== selectedSource) return false
    if (selectedCategory !== "all" && !skill.tags?.includes(selectedCategory)) return false
    if (searchQuery && !skill.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !skill.description.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !skill.tags?.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))) return false
    return true
  })

  const categories = ["all", "search", "code", "analysis", "data", "api", "reasoning", "planning", "nlp", "vision", "sql", "logic"]

  const categoriesCount = categories.reduce((acc, cat) => {
    if (cat === "all") {
      acc[cat] = skills.length
    } else {
      acc[cat] = skills.filter(s => s.tags?.includes(cat)).length
    }
    return acc
  }, {} as Record<string, number>)

  const handleView = async (skillName: string) => {
    const skill = skills.find(s => s.name === skillName)
    if (skill) {
      setSelectedSkill({
        name: skill.name,
        description: skill.description,
        frontmatter: { name: skill.name, description: skill.description, license: "MIT" },
        content: `# ${skill.name}\n\nSkill instructions would go here...`,
        files: {},
        source: skill.source,
        modified_at: skill.modified_at,
      })
    }
  }

  const handleInstall = async (skillName: string) => {
    // In production: POST to /api/v1/skills/install
    alert(`Would install ${skillName} from marketplace`)
  }

  const handleValidate = async (skillName: string) => {
    alert(`Validation would run for ${skillName}`)
  }

  const handleDelete = async (skillName: string) => {
    if (!confirm(`Delete skill "${skillName}"?`)) return
    // In production: DELETE /api/v1/skills/${skillName}
    // setSkills(prev => prev.filter(s => s.name !== skillName))
  }

  const filteredSkills = skills.filter(skill => {
    if (selectedSource !== "all" && skill.source !== selectedSource) return false
    if (selectedCategory !== "all" && !skill.tags?.includes(selectedCategory)) return false
    if (searchQuery && !skill.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !skill.description.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !skill.tags?.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))) return false
    return true
  })

  const handleInstall = (skillName: string) => {
    alert(`Would install ${skillName} to your workspace`)
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Skills Marketplace</h1>
          <p className="text-muted-foreground">Discover, install, and share Deep Agent skills from the community</p>
        </div>
        <Button variant="outline">
          <Download className="h-4 w-4 mr-2" />
          Sync with Fleet
        </Button>
      </div>

      {/* Filters */}
      <Card className="border-border">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
              <Input
                placeholder="Search skills..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={selectedSource} onValueChange={setSelectedSource}>
              <SelectTrigger>
                <SelectValue placeholder="All Sources" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Sources</SelectItem>
                <SelectItem value="local">Local</SelectItem>
                <SelectItem value="fleet">Fleet</SelectItem>
                <SelectItem value="git">Git</SelectItem>
                <SelectItem value="s3">S3</SelectItem>
              </SelectContent>
            </Select>
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger>
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map(cat => (
                  <SelectItem key={cat} value={cat}>{cat.charAt(0).toUpperCase() + cat.slice(1)} ({categoriesCount[cat] || 0})</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => { /* sync remotes */ }}>
              <Download className="h-4 w-4 mr-2" />
              Sync Fleet
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Skills Grid */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Marketplace ({filteredSkills.length})</CardTitle>
          </CardHeader>
          <CardContent>
            {filteredSkills.length === 0 ? (
              <div className="text-center py-12 text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
                <p>No skills found</p>
                <p className="text-sm">Try adjusting your filters or search query</p>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {filteredSkills.map(skill => (
                  <Card key={skill.name} className="h-full flex flex-col">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div>
                          <CardTitle className="text-lg">{skill.name}</CardTitle>
                          <p className="text-sm text-muted-foreground line-clamp-2">{skill.description}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant={skill.verified ? "default" : "secondary"}>
                            {skill.verified ? <CheckCircle2 className="h-3 w-3 mr-1" /> : null} {skill.verified ? "Verified" : "Community"}
                          </Badge>
                          <Badge variant={skill.source === "fleet" ? "default" : "secondary"}>
                            {skill.source}
                          </Badge>
                        </div>
                      </CardHeader>
                      <CardContent className="flex flex-col flex-1">
                        <div className="flex flex-wrap gap-1 mb-3">
                          {skill.tags?.slice(0, 4).map(tag => (
                            <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                          ))}
                        </div>
                        <div className="flex items-center gap-4 text-xs text-muted-foreground mt-auto pt-2 border-t">
                          <span className="flex items-center gap-1">
                            <Star className="h-3 w-3 fill-current text-yellow-500" />
                            {skill.rating?.toFixed(1) || "N/A"}
                          </span>
                          <span className="flex items-center gap-1">
                            <Download className="h-3 w-3" />
                            {skill.downloads?.toLocaleString() || "0"}
                          </span>
                          <Badge variant={skill.verified ? "default" : "secondary"} className="text-xs">
                            {skill.verified ? <CheckCircle2 className="h-2.5 w-2.5 mr-1" /> : null} {skill.verified ? "Verified" : "Community"}
                          </Badge>
                        </div>
                      </CardContent>
                      <CardFooter className="flex items-center justify-between p-0 pt-4">
                        <Button variant="outline" size="sm" className="flex-1" onClick={() => handleView(skill.name)}>
                          <FileText className="h-4 w-4 mr-1" />
                          View Details
                        </Button>
                        <Button variant="default" size="sm" className="flex-1" onClick={() => { handleInstall(skill.name) }}>
                          <Download className="h-4 w-4 mr-1" />
                          Install
                        </Button>
                      </CardFooter>
                    </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Skill Detail Modal */}
        {selectedSkill && (
          <Dialog open onOpenChange={open => !open && setSelectedSkill(null)}>
            <DialogContent className="max-w-4xl max-h-[90vh]">
              <DialogHeader>
                <div className="flex items-center justify-between">
                  <DialogTitle>{selectedSkill.name}</DialogTitle>
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">{selectedSkill.source}</Badge>
                    {selectedSkill.verified && <Badge variant="default"><CheckCircle2 className="h-3 w-3 mr-1" /> Verified</Badge>}
                  </div>
                </div>
              </DialogHeader>
              <SkillViewer skill={selectedSkill} onClose={() => setSelectedSkill(null)} />
            </DialogContent>
          </Dialog>
        )}
      </div>
    </div>
  );
}

function SkillViewer({ skill, onClose }: { skill: any; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState("overview")

  return (
    <div className="space-y-4">
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="content">Content</TabsTrigger>
          <TabsTrigger value="frontmatter">Frontmatter</TabsTrigger>
          <TabsTrigger value="files">Files</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="space-y-4">
            <div>
              <Label>Description</Label>
              <p className="text-muted-foreground">{skill.description}</p>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Source</Label>
                <Badge variant="secondary">{skill.source}</Badge>
              </div>
              <div>
                <Label>Version</Label>
                <p className="text-sm text-muted-foreground font-mono">{skill.version || "1.0.0"}</p>
              </div>
              <div>
                <Label>Author</Label>
                <p className="text-sm text-muted-foreground">{skill.author || "Unknown"}</p>
              </div>
            </div>
            <div>
              <Label>Tags</Label>
              <div className="flex flex-wrap gap-1 mt-1">
                {skill.tags?.map(tag => (
                  <Badge key={tag} variant="outline" className="text-xs">{tag}</Badge>
                ))}
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4 mt-4">
              <div>
                <Label>Rating</Label>
                <div className="flex items-center gap-1">
                  <Star className="h-4 w-3 fill-current text-yellow-500" />
                  <span className="font-mono">{skill.rating?.toFixed(1) || "N/A"}</span>
                </div>
              </div>
              <div>
                <Label>Downloads</Label>
                <div className="flex items-center gap-1">
                  <Download className="h-3 w-3" />
                  <span className="font-mono">{skill.downloads?.toLocaleString() || "0"}</span>
                </div>
              </div>
              <div>
                <Label>Status</Label>
                <Badge variant={skill.verified ? "default" : "secondary"}>
                  {skill.verified ? <CheckCircle2 className="h-3 w-3 mr-1" /> : null} {skill.verified ? "Verified" : "Community"}
                </Badge>
              </div>
            </div>
          </TabsContent>

          <TabsContent value="content">
            <div className="bg-muted/50 p-4 rounded font-mono text-sm whitespace-pre-wrap max-h-[500px] overflow-y-auto">
              {skill.content || "# Skill content would be displayed here"}
            </div>
          </TabsContent>

          <TabsContent value="frontmatter">
            <div className="bg-muted/50 p-4 rounded font-mono text-sm overflow-x-auto">
              {JSON.stringify(skill.frontmatter || { name: skill.name, description: skill.description, license: "MIT" }, null, 2)}
            </div>
          </TabsContent>

          <TabsContent value="files">
            <p className="text-center text-muted-foreground py-8">No supporting files</p>
          </TabsContent>
        </Tabs>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>Close</Button>
          <Button onClick={() => handleInstall(skill.name)}>
            <Download className="h-4 w-4 mr-2" />
            Install to Workspace
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function SkillEditor({ onSubmit, onCancel }: { onSubmit: (data: any) => void; onCancel: () => void }) {
  const [name, setName] = useState("")
  const [description, setDescription] = useState("")
  const [license, setLicense] = useState("MIT")
  const [content, setContent] = useState("")
  const [frontmatter, setFrontmatter] = useState(JSON.stringify({ name: "", description: "", license: "MIT" }, null, 2))
  const [error, setError] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const fm = JSON.parse(frontmatter)
      if (!fm.name || !fm.description) {
        setError("Name and description are required")
        return
      }
      onSubmit({ name: fm.name, frontmatter: fm, content })
    } catch (err) {
      setError("Invalid frontmatter JSON")
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {error && <div className="text-red-600 text-sm">{error}</div>}
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label>Name</Label>
          <Input
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="my-skill"
            required
          />
        </div>
        <div>
          <Label>License</Label>
          <Input value={license} onChange={e => setLicense(e.target.value)} />
        </div>
      </div>
      
      <div>
        <Label>Description</Label>
        <Input
          value={description}
          onChange={e => setDescription(e.target.value)}
          placeholder="What this skill does and when to use it"
          required
        />
      </div>

      <div>
        <Label>Frontmatter (JSON)</Label>
        <Textarea
          value={frontmatter}
          onChange={e => setFrontmatter(e.target.value)}
          className="font-mono text-sm"
          rows={6}
        />
      </div>

      <div>
        <Label>Content (Markdown)</Label>
        <Textarea
          value={content}
          onChange={e => setContent(e.target.value)}
          className="font-mono text-sm"
          rows={12}
          placeholder="# Skill Name\n\n## Overview\n\n## Instructions\n\n### 1. Step one..."
        />
      </div>

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>Cancel</Button>
        <Button type="submit">Create Skill</Button>
      </DialogFooter>
    </form>
  )
}
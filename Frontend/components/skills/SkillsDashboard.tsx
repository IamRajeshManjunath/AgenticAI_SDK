"use client";

import { useState, useEffect } from "react";
import { Search, Plus, FileText, Settings, RefreshCw, Download, Trash2, Edit, ExternalLink, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";

export interface SkillMetadata {
  name: string;
  description: string;
  source: "local" | "git" | "s3" | "fleet";
  modified_at: string;
}

interface SkillManifest {
  name: string;
  description: string;
  frontmatter: Record<string, any>;
  content: string;
  files: Record<string, string>;
  source: string;
  modified_at: string;
}

const mockSkills: SkillMetadata[] = [
  { name: "web-research", description: "Search the web and synthesize findings", source: "local", modified_at: "2024-01-15T10:00:00Z" },
  { name: "code-generation", description: "Generate code from specifications", source: "local", modified_at: "2024-01-14T15:30:00Z" },
  { name: "document-analysis", description: "Analyze documents for insights", source: "local", modified_at: "2024-01-13T09:00:00Z" },
  { name: "data-processing", description: "Process and transform data", source: "local", modified_at: "2024-01-12T14:00:00Z" },
  { name: "api-integration", description: "Integrate with external APIs", source: "local", modified_at: "2024-01-11T11:00:00Z" },
  { name: "reasoning", description: "Multi-step reasoning and problem solving", source: "local", modified_at: "2024-01-10T16:00:00Z" },
  { name: "planning", description: "Create execution plans for complex tasks", source: "local", modified_at: "2024-01-09T10:00:00Z" },
];

export function SkillsDashboard() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSource, setSelectedSource] = useState<string>("all");
  const [selectedSkill, setSelectedSkill] = useState<SkillManifest | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [skills, setSkills] = useState<SkillMetadata[]>(mockSkills);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchSkills();
  }, []);

  const fetchSkills = async () => {
    setLoading(true);
    try {
      // In production, this would call the API
      // const response = await fetch("/api/v1/skills");
      // const data = await response.json();
      // setSkills(data.skills);
    } catch (error) {
      console.error("Failed to fetch skills:", error);
    } finally {
      setLoading(false);
    }
  };

  const filteredSkills = skills.filter(skill => {
    if (selectedSource !== "all" && skill.source !== selectedSource) return false;
    if (searchQuery && !skill.name.toLowerCase().includes(searchQuery.toLowerCase()) &&
        !skill.description.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const handleView = async (skillName: string) => {
    // In production: fetch full skill from API
    // const response = await fetch(`/api/v1/skills/${skillName}`);
    // const skill = await response.json();
    // setSelectedSkill(skill);
    
    // Mock data for demo
    setSelectedSkill({
      name: skillName,
      description: mockSkills.find(s => s.name === skillName)?.description || "",
      frontmatter: { name: skillName, description: "", license: "MIT" },
      content: `# ${skillName}\n\nSkill instructions would go here...`,
      files: {},
      source: "local",
      modified_at: new Date().toISOString(),
    });
  };

  const handleCreate = async () => {
    // In production: POST to /api/v1/skills
    setIsCreating(false);
    fetchSkills();
  };

  const handleDelete = async (skillName: string) => {
    if (!confirm(`Delete skill "${skillName}"?`)) return;
    // In production: DELETE /api/v1/skills/${skillName}
    setSkills(prev => prev.filter(s => s.name !== skillName));
  };

  const handleValidate = async (skillName: string) => {
    // In production: POST /api/v1/skills/${skillName}/validate
    alert(`Validation would run for ${skillName}`);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Skills</h1>
          <p className="text-muted-foreground">Manage Deep Agent skills (SKILL.md files)</p>
        </div>
        <Dialog open={isCreating} onOpenChange={setIsCreating}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="h-4 w-4 mr-2" />
              New Skill
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl">
            <DialogHeader>
              <DialogTitle>Create New Skill</DialogTitle>
            </DialogHeader>
            <SkillEditor onSubmit={handleCreate} onCancel={() => setIsCreating(false)} />
          </DialogContent>
        </Dialog>
        <Button variant="outline" onClick={() => { /* refresh */ }}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Refresh
        </Button>
      </div>

      {/* Filters */}
      <Card className="border-border">
        <CardContent className="pt-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                <SelectItem value="git">Git</SelectItem>
                <SelectItem value="s3">S3</SelectItem>
                <SelectItem value="fleet">Fleet</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline" onClick={() => { /* sync remotes */ }}>
              <Download className="h-4 w-4 mr-2" />
              Sync Remotes
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Skills Table */}
      <Card>
        <CardHeader>
          <CardTitle>Skills ({filteredSkills.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {filteredSkills.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground/50" />
              <p>No skills found</p>
              <p className="text-sm">Click "New Skill" to create your first skill</p>
            </div>
          ) : (
            <ScrollArea className="h-[500px]">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Skill</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Source</TableHead>
                    <TableHead>Last Modified</TableHead>
                    <TableHead className="w-48">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredSkills.map(skill => (
                    <TableRow key={skill.name}>
                      <TableCell className="font-medium">{skill.name}</TableCell>
                      <TableCell className="max-w-md truncate">{skill.description}</TableCell>
                      <TableCell>
                        <Badge variant={skill.source === "local" ? "default" : "secondary"}>
                          {skill.source}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-sm font-mono">
                        {new Date(skill.modified_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => handleView(skill.name)} title="View">
                            <FileText className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleValidate(skill.name)} title="Validate">
                            <Settings className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" onClick={() => handleDelete(skill.name)} title="Delete" className="text-red-600 hover:text-red-600">
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
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
                </div>
              </div>
            </DialogHeader>
            <SkillViewer skill={selectedSkill} onClose={() => setSelectedSkill(null)} />
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

function SkillViewer({ skill, onClose }: { skill: SkillManifest; onClose: () => void }) {
  const [activeTab, setActiveTab] = useState("overview");

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
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Source</Label>
                <Badge variant="secondary">{skill.source}</Badge>
              </div>
              <div>
                <Label>Last Modified</Label>
                <p className="text-sm text-muted-foreground font-mono">
                  {new Date(skill.modified_at).toLocaleString()}
                </p>
              </div>
            </div>
            <div>
              <Label>Frontmatter</Label>
              <pre className="bg-muted p-4 rounded text-sm overflow-x-auto">
                {JSON.stringify(skill.frontmatter, null, 2)}
              </pre>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="content">
          <div className="bg-muted/50 p-4 rounded font-mono text-sm whitespace-pre-wrap max-h-[500px] overflow-y-auto">
            {skill.content || "No content"}
          </div>
        </TabsContent>

        <TabsContent value="frontmatter">
          <div className="bg-muted/50 p-4 rounded font-mono text-sm overflow-x-auto">
            {JSON.stringify(skill.frontmatter, null, 2)}
          </div>
        </TabsContent>

        <TabsContent value="files">
          {Object.keys(skill.files).length === 0 ? (
            <p className="text-center text-muted-foreground py-8">No supporting files</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Path</TableHead>
                  <TableHead>Size</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {Object.entries(skill.files).map(([path, content]) => (
                  <TableRow key={path}>
                    <TableCell className="font-mono text-sm">{path}</TableCell>
                    <TableCell className="text-sm">{content.length} chars</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </TabsContent>
      </Tabs>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Close</Button>
      </DialogFooter>
    </div>
  );
}

function SkillEditor({ onSubmit, onCancel }: { onSubmit: (data: any) => void; onCancel: () => void }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [license, setLicense] = useState("MIT");
  const [content, setContent] = useState("");
  const [frontmatter, setFrontmatter] = useState(JSON.stringify({ name: "", description: "", license: "MIT" }, null, 2));
  const [error, setError] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    try {
      const fm = JSON.parse(frontmatter);
      if (!fm.name || !fm.description) {
        setError("Name and description are required");
        return;
      }
      onSubmit({ name: fm.name, frontmatter: fm, content });
    } catch (err) {
      setError("Invalid frontmatter JSON");
    }
  };

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
  );
}
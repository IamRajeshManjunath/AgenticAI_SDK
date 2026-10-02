'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger, DialogFooter } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { RefreshCw, Plus, Edit, Trash2, Shield, ShieldCheck, ShieldAlert, ShieldOff, User, Users, Key, Search, Filter, Settings, ShieldAlert, ShieldCheck, FileText, Copy, Save, AlertCircle, CheckCircle2, Loader2, X, ChevronDown, ChevronUp, Menu, X } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface Policy {
  id: string
  name: string
  description: string | null
  is_system: boolean
  policy_document: PolicyDocument
  created_at: string
  updated_at: string
}

interface PolicyDocument {
  Version: string
  Statement: PolicyStatement[]
}

interface PolicyStatement {
  Effect: 'Allow' | 'Deny'
  Action: string[]
  Resource: string[]
  Condition?: Record<string, unknown>
}

interface RolePolicy {
  role: string
  name: string
  description: string
  document: PolicyDocument
}

const DEFAULT_ROLE_POLICIES: Record<string, RolePolicy> = {
  admin: {
    role: 'admin',
    name: 'Admin Full Access',
    description: 'Unrestricted access to all resources',
    document: {
      Version: '1',
      Statement: [{ Effect: 'Allow', Action: ['*'], Resource: ['*'] }],
    },
  },
  editor: {
    role: 'editor',
    name: 'Editor Access',
    description: 'Full CRUD except admin & billing actions',
    document: {
      Version: '1',
      Statement: [
        { Effect: 'Allow', Action: ['*'], Resource: ['*'] },
        { Effect: 'Deny', Action: ['member:invite', 'member:remove', 'member:update-role', 'workspace:delete', 'workspace:transfer', 'apikey:delete', 'apikey:regenerate', 'billing:*', 'admin:*'], Resource: ['*'] },
      ],
    },
  },
  viewer: {
    role: 'viewer',
    name: 'Viewer Access',
    description: 'Read-only plus workflow execution',
    document: {
      Version: '1',
      Statement: [
        { Effect: 'Allow', Action: ['workflow:read', 'workflow:run', 'tool:read', 'rag:read', 'rag:query', 'member:list', 'member:read', 'workspace:read', 'apikey:read', 'integration:read', 'integration:registry:read', 'cron:read', 'observability:read', 'execution:read', 'template:read', 'notification:read', 'approval:read', 'audit:read', 'tag:read', 'settings:read', 'secret:read'], Resource: ['*'] },
      ],
    },
  },
}

export default function RBACPolicyEditor() {
  const [policies, setPolicies] = useState<Policy[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [editingPolicy, setEditingPolicy] = useState<Policy | null>(null)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    is_system: false,
    document: {
      Version: '1',
      Statement: [{ Effect: 'Allow', Action: ['*'], Resource: ['*'] }],
    },
  })
  const [activeTab, setActiveTab] = useState<'policies' | 'roles' | 'editor'>('policies')
  const [validationErrors, setValidationErrors] = useState<string[]>([])
  const [isSaving, setIsSaving] = useState(false)

  const { token } = useAuthStore()

  useEffect(() => {
    fetchPolicies()
  }, [])

  const fetchPolicies = async () => {
    setIsLoading(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/policies`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) {
        const data = await response.json()
        setPolicies(data)
      }
    } catch (error) {
      console.error('Failed to fetch policies:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const handleCreatePolicy = async () => {
    setIsSaving(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/policies`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
        body: JSON.stringify(formData),
      })
      if (response.ok) {
        await fetchPolicies()
        setEditingPolicy(null)
        setFormData({ name: '', description: '', is_system: false, document: { Version: '1', Statement: [{ Effect: 'Allow', Action: ['*'], Resource: ['*'] }] } })
      } else {
        const error = await response.json()
        alert(`Failed to create: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to create: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleUpdatePolicy = async () => {
    if (!editingPolicy) return
    setIsSaving(true)
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/policies/${editingPolicy.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
        body: JSON.stringify(formData),
      })
      if (response.ok) {
        await fetchPolicies()
        setEditingPolicy(null)
        setFormData({ name: '', description: '', is_system: false, document: { Version: '1', Statement: [{ Effect: 'Allow', Action: ['*'], Resource: ['*'] }] } })
      } else {
        const error = await response.json()
        alert(`Failed to update: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to update: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setIsSaving(false)
    }
  }

  const handleDeletePolicy = async (id: string) => {
    if (!confirm('Delete this policy? This cannot be undone.')) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/policies/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) {
        await fetchPolicies()
      } else {
        const error = await response.json()
        alert(`Failed to delete: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to delete: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleEdit = (policy: Policy) => {
    setEditingPolicy(policy)
    setFormData({
      name: policy.name,
      description: policy.description || '',
      is_system: policy.is_system,
      document: policy.policy_document,
    })
  }

  const handleNewPolicy = () => {
    setEditingPolicy(null)
    setFormData({
      name: '',
      description: '',
      is_system: false,
      document: { Version: '1', Statement: [{ Effect: 'Allow', Action: ['*'], Resource: ['*'] }] },
    })
  }

  const validatePolicyDocument = (doc: PolicyDocument): string[] => {
    const errors: string[] = []
    if (!doc.Version) errors.push('Version is required')
    if (!doc.Statement || !Array.isArray(doc.Statement) || doc.Statement.length === 0) {
      errors.push('At least one statement is required')
    } else {
      doc.Statement.forEach((stmt, i) => {
        if (!stmt.Effect || !['Allow', 'Deny'].includes(stmt.Effect)) {
          errors.push(`Statement ${i + 1}: Effect must be 'Allow' or 'Deny'`)
        }
        if (!stmt.Action || !Array.isArray(stmt.Action) || stmt.Action.length === 0) {
          errors.push(`Statement ${i + 1}: At least one action is required`)
        }
        if (!stmt.Resource || !Array.isArray(stmt.Resource) || stmt.Resource.length === 0) {
          errors.push(`Statement ${i + 1}: At least one resource is required`)
        }
      })
    }
    return errors
  }

  const validateForm = () => {
    const errors = validatePolicyDocument(formData.document)
    if (!formData.name.trim()) errors.push('Policy name is required')
    setValidationErrors(errors)
    return errors.length === 0
  }

  const handleNewPolicy = () => {
    setEditingPolicy(null)
    setFormData({
      name: '',
      description: '',
      is_system: false,
      document: { Version: '1', Statement: [{ Effect: 'Allow', Action: ['*'], Resource: ['*'] }] },
    })
  }

  const handleEdit = (policy: Policy) => {
    setEditingPolicy(policy)
    setFormData({
      name: policy.name,
      description: policy.description || '',
      is_system: policy.is_system,
      document: policy.policy_document,
    })
  }

  const handleSubmit = () => {
    if (!validateForm()) return
    if (editingPolicy) handleUpdatePolicy()
    else handleCreatePolicy()
  }

  const handleDocumentChange = (path: string, value: any) => {
    const keys = path.split('.')
    const newDoc = JSON.parse(JSON.stringify(formData.document))
    let obj: any = newDoc
    for (let i = 0; i < keys.length - 1; i++) {
      obj = obj[keys[i]]
    }
    obj[keys[keys.length - 1]] = value
    setFormData(prev => ({ ...prev, document: newDoc }))
  }

  const addStatement = () => {
    const newStmt = { Effect: 'Allow' as const, Action: ['*'], Resource: ['*'] }
    setFormData(prev => ({
      ...prev,
      document: { ...prev.document, Statement: [...prev.document.Statement, newStmt] },
    })
  }

  const removeStatement = (index: number) => {
    setFormData(prev => ({
      ...prev,
      document: { ...prev.document, Statement: prev.document.Statement.filter((_, i) => i !== index) },
    })
  }

  const updateStatement = (index: number, field: keyof PolicyStatement, value: any) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      newDoc.Statement[index][field] = value
      return { ...prev, document: newDoc }
    })
  }

  const addAction = (stmtIndex: number) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      newDoc.Statement[stmtIndex].Action.push('')
      return { ...prev, document: newDoc }
    })
  }

  const removeAction = (stmtIndex: number, actionIndex: number) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      newDoc.Statement[stmtIndex].Action.splice(actionIndex, 1)
      return { ...prev, document: newDoc }
    })
  }

  const updateAction = (stmtIndex: number, actionIndex: number, value: string) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      newDoc.Statement[stmtIndex].Action[actionIndex] = value
      return { ...prev, document: newDoc }
    })
  }

  const addResource = (stmtIndex: number) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      newDoc.Statement[stmtIndex].Resource.push('')
      return { ...prev, document: newDoc }
    })
  }

  const removeResource = (stmtIndex: number, resourceIndex: number) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      newDoc.Statement[stmtIndex].Resource.splice(resourceIndex, 1)
      return { ...prev, document: newDoc }
    })
  }

  const updateResource = (stmtIndex: number, resourceIndex: number, value: string) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      newDoc.Statement[stmtIndex].Resource[resourceIndex] = value
      return { ...prev, document: newDoc }
    })
  }

  const addCondition = (stmtIndex: number, key: string, value: any) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      if (!newDoc.Statement[stmtIndex].Condition) newDoc.Statement[stmtIndex].Condition = {}
      newDoc.Statement[stmtIndex].Condition![key] = value
      return { ...prev, document: newDoc }
    })
  }

  const removeCondition = (stmtIndex: number, key: string) => {
    setFormData(prev => {
      const newDoc = JSON.parse(JSON.stringify(prev.document))
      if (newDoc.Statement[stmtIndex].Condition) {
        delete newDoc.Statement[stmtIndex].Condition[key]
        if (Object.keys(newDoc.Statement[stmtIndex].Condition!).length === 0) {
          delete newDoc.Statement[stmtIndex].Condition
        }
      }
      return { ...prev, document: newDoc }
    })
  }

  const validateJson = (jsonStr: string): { valid: boolean; error?: string } => {
    try {
      JSON.parse(jsonStr)
      return { valid: true }
    } catch (error) {
      return { valid: false, error: error instanceof Error ? error.message : 'Invalid JSON' }
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">RBAC Policy Editor</h1>
          <p className="text-muted-foreground mt-1">Create and manage IAM policies with visual editor</p>
        </div>
        <Button onClick={handleNewPolicy} className="gap-2">
          <Plus className="h-4 w-4" />
          New Policy
        </Button>
      </div>

      <Tabs defaultValue="policies" onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="policies">Policies</TabsTrigger>
          <TabsTrigger value="roles">Default Roles</TabsTrigger>
          <TabsTrigger value="editor">Visual Editor</TabsTrigger>
        </TabsList>

        <TabsContent value="policies" className="mt-6">
          <div className="space-y-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Policies ({policies.length})</h3>
              <Button onClick={handleNewPolicy} className="gap-2">
                <Plus className="h-4 w-4" />
                New Policy
              </Button>
            </div>

            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Type</TableHead>
                    <TableHead>Statements</TableHead>
                    <TableHead className="w-48">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {policies.map((policy) => (
                    <TableRow key={policy.id}>
                      <TableCell className="font-medium">{policy.name}</TableCell>
                      <TableCell className="text-muted-foreground max-w-xs truncate">{policy.description || 'No description'}</TableCell>
                      <TableCell>
                        <Badge variant={policy.is_system ? 'default' : 'secondary'}>
                          {policy.is_system ? 'System' : 'Custom'}
                        </Badge>
                      </TableCell>
                      <TableCell>{policy.policy_document.Statement.length} statement(s)</TableCell>
                      <TableCell>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-8 w-8">
                              <MoreHorizontal className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem onClick={() => handleEdit(policy)}>
                              <Edit className="w-4 h-4 mr-2" />
                              Edit
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => { /* duplicate */ }}>
                              <Copy className="w-4 h-4 mr-2" />
                              Duplicate
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => handleDeletePolicy(policy.id)} className="text-destructive">
                              <Trash2 className="w-4 h-4 mr-2" />
                              Delete
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </TabsContent>

          <TabsContent value="roles" className="mt-6">
            <div className="grid gap-4 md:grid-cols-3">
              {Object.entries(DEFAULT_ROLE_POLICIES).map(([roleKey, role]) => (
                <Card key={roleKey} className="h-full">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="capitalize">{roleKey}</CardTitle>
                      <Badge variant={role.document.Statement[0].Effect === 'Allow' ? 'default' : 'destructive'}>
                        {role.document.Statement[0].Effect}
                      </Badge>
                    </div>
                    <CardDescription>{role.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="space-y-2">
                      {role.document.Statement.map((stmt, i) => (
                        <div key={i} className="p-3 rounded-lg bg-muted/50 border border-border">
                          <div className="flex items-center gap-2 mb-2">
                            <Badge variant={stmt.Effect === 'Allow' ? 'default' : 'destructive'}>{stmt.Effect}</Badge>
                            <span className="text-sm text-muted-foreground">Statement {i + 1}</span>
                          </div>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="text-muted-foreground">Actions:</span>
                              <p className="font-mono text-xs">{stmt.Action.join(', ')}</p>
                            </div>
                            <div>
                              <span className="text-muted-foreground">Resources:</span>
                              <p className="font-mono text-xs">{stmt.Resource.join(', ')}</p>
                            </div>
                          </div>
                        ))}
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </TabsContent>

            <TabsContent value="editor" className="mt-6">
              <Card className="h-[800px] flex flex-col">
                <CardHeader className="flex flex-row items-center justify-between">
                  <CardTitle className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-primary" />
                    Visual Policy Editor
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={handleNewPolicy} className="gap-1">
                      <Plus className="h-4 w-4" />
                      New
                    </Button>
                    <Button variant="outline" size="sm" onClick={handleSavePolicy} disabled={isSaving} className="gap-1">
                      <Save className="w-4 h-4 mr-1" />
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
                  </div>
                </CardHeader>
                <CardContent className="flex-1 overflow-hidden">
                  <div className="h-full grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Statement List */}
                    <div className="lg:col-span-1 space-y-3 overflow-y-auto p-4 bg-muted/30 rounded-lg">
                      <h4 className="font-medium mb-3">Statements ({formData.document.Statement.length})</h4>
                      <Button variant="outline" size="sm" onClick={addStatement} className="w-full gap-1 mb-3">
                        <Plus className="h-4 w-4" />
                        Add Statement
                      </Button>
                      <div className="space-y-2 max-h-[400px] overflow-y-auto">
                        {formData.document.Statement.map((stmt, index) => (
                          <div key={index} className="p-3 bg-card border border-border rounded-lg space-y-2">
                            <div className="flex items-center justify-between">
                              <select
                                value={stmt.Effect}
                                onChange={(e) => updateStatement(index, 'Effect', e.target.value as 'Allow' | 'Deny')}
                                className={`px-2 py-1 rounded text-sm ${stmt.Effect === 'Allow' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
                              >
                                <option value="Allow">Allow</option>
                                <option value="Deny">Deny</option>
                              </select>
                              <Button variant="ghost" size="icon" onClick={() => removeStatement(index)} className="text-red-500 hover:text-red-700">
                                <Trash2 className="w-4 h-4" />
                              </Button>
                            </div>
                            <div className="space-y-2">
                              <div>
                                <Label className="text-xs text-muted-foreground">Actions</Label>
                                <div className="flex flex-wrap gap-1">
                                  {stmt.Action.map((action, aIdx) => (
                                    <div key={aIdx} className="flex items-center gap-1">
                                      <Input value={action} onChange={(e) => updateAction(index, aIdx, e.target.value)} className="w-32 text-xs" />
                                      <Button variant="ghost" size="icon" onClick={() => removeAction(index, aIdx)} className="text-red-500">
                                        <X className="w-3 h-3" />
                                      </Button>
                                    </div>
                                  ))}
                                  <Button variant="outline" size="sm" onClick={() => addAction(index)} className="w-full mt-1">
                                    <Plus className="h-3 w-3 mr-1" />
                                    Add Action
                                  </Button>
                                </div>
                                <div className="space-y-1">
                                  <Label className="text-xs text-muted-foreground">Resources</Label>
                                  <div className="flex flex-wrap gap-1">
                                    {stmt.Resource.map((resource, rIdx) => (
                                      <div key={rIdx} className="flex items-center gap-1">
                                        <Input value={resource} onChange={(e) => updateResource(index, rIdx, e.target.value)} className="w-40 text-xs" />
                                        <Button variant="ghost" size="icon" onClick={() => removeResource(index, rIdx)} className="text-red-500">
                                          <X className="w-3 h-3" />
                                        </Button>
                                      </div>
                                    ))}
                                    <Button variant="outline" size="sm" onClick={() => addResource(index)} className="w-full mt-1">
                                      <Plus className="h-3 w-3 mr-1" />
                                      Add Resource
                                    </Button>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                          <div className="mt-4 pt-4 border-t">
                            <Button variant="outline" size="sm" onClick={addStatement} className="w-full gap-1">
                              <Plus className="h-4 w-4" />
                              Add Another Statement
                            </Button>
                          </div>
                        </div>
                      </TabsContent>
                    </Tabs>
                  </CardContent>
                </Card>
              </Tabs>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  )
}

export default RBACPolicyEditor
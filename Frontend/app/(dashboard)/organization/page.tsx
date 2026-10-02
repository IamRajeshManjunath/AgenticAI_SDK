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
import { RefreshCw, Plus, Edit, Trash2, Users, Building2, Shield, Key, Settings, Mail, Send, X, CheckCircle2, AlertCircle, Loader2, MoreHorizontal } from 'lucide-react'
import { api } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface Organization {
  id: string
  name: string
  description: string | null
  slug: string
  owner_id: string
  plan: 'free' | 'pro' | 'enterprise'
  settings: Record<string, any>
  created_at: string
  updated_at: string
}

interface Workspace {
  id: string
  organization_id: string
  name: string
  description: string | null
  owner_id: string
  plan_id: string | null
  stripe_customer_id: string | null
  stripe_subscription_id: string | null
  subscription_status: 'active' | 'inactive' | 'cancelled' | 'trialing'
  created_at: string
  updated_at: string
}

interface WorkspaceMember {
  id: string
  workspace_id: string
  user_id: string
  role: 'admin' | 'editor' | 'viewer'
  invited_by: string
  created_at: string
  user: {
    id: string
    email: string
    full_name: string
  }
}

interface Invitation {
  id: string
  workspace_id: string
  email: string
  role: 'admin' | 'editor' | 'viewer'
  invited_by: string
  status: 'pending' | 'accepted' | 'rejected' | 'expired'
  created_at: string
  expires_at: string
}

export default function OrganizationPage() {
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [members, setMembers] = useState<WorkspaceMember[]>([])
  const [invitations, setInvitations] = useState<Invitation[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'organizations' | 'workspaces' | 'members' | 'invitations'>('organizations')
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null)
  const [editingWorkspace, setEditingWorkspace] = useState<Workspace | null>(null)
  const [inviting, setInviting] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState<'admin' | 'editor' | 'viewer'>('editor')
  const { token } = useAuthStore()

  useEffect(() => {
    fetchOrganizations()
    fetchWorkspaces()
    fetchMembers()
    fetchInvitations()
  }, [])

  const fetchOrganizations = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/organizations`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) {
        const data = await response.json()
        setOrganizations(data)
      }
    } catch (error) {
      console.error('Failed to fetch organizations:', error)
    }
  }

  const fetchWorkspaces = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workspaces`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) {
        const data = await response.json()
        setWorkspaces(data)
      }
    } catch (error) {
      console.error('Failed to fetch workspaces:', error)
    }
  }

  const fetchMembers = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/workspace/members`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) {
        const data = await response.json()
        setMembers(data)
      }
    } catch (error) {
      console.error('Failed to fetch members:', error)
    }
  }

  const fetchInvitations = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/workspace/invitations`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) {
        const data = await response.json()
        setInvitations(data)
      }
    } catch (error) {
      console.error('Failed to fetch invitations:', error)
    }
  }

  const handleCreateOrg = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/organizations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
        body: JSON.stringify({ name: `Organization ${organizations.length + 1}`, slug: `org-${Date.now()}` }),
      })
      if (response.ok) await fetchOrganizations()
    } catch (error) {
      console.error('Failed to create organization:', error)
    }
  }

  const handleUpdateOrg = async (org: Organization) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/organizations/${org.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
        body: JSON.stringify({ name: org.name, description: org.description }),
      })
      if (response.ok) await fetchOrganizations()
    } catch (error) {
      console.error('Failed to update organization:', error)
    }
  }

  const handleDeleteOrg = async (id: string) => {
    if (!confirm('Delete this organization? This cannot be undone.')) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/organizations/${id}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) await fetchOrganizations()
    } catch (error) {
      console.error('Failed to delete organization:', error)
    }
  }

  const handleCreateWorkspace = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/workspaces`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
        body: JSON.stringify({ name: `Workspace ${workspaces.length + 1}` }),
      })
      if (response.ok) await fetchWorkspaces()
    } catch (error) {
      console.error('Failed to create workspace:', error)
    }
  }

  const handleInvite = async () => {
    if (!inviteEmail) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/workspace/invite`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
        body: JSON.stringify({ email: inviteEmail, role: inviteRole }),
      })
      if (response.ok) {
        await fetchInvitations()
        setInviting(false)
        setInviteEmail('')
      } else {
        const error = await response.json()
        alert(`Failed to invite: ${error.detail || 'Unknown error'}`)
      }
    } catch (error) {
      alert(`Failed to invite: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const handleRemoveMember = async (memberId: string) => {
    if (!confirm('Remove this member?')) return
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/workspace/members/${memberId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) await fetchMembers()
    } catch (error) {
      console.error('Failed to remove member:', error)
    }
  }

  const handleUpdateRole = async (memberId: string, role: 'admin' | 'editor' | 'viewer') => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/workspace/members/${memberId}/role`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
        body: JSON.stringify({ role }),
      })
      if (response.ok) await fetchMembers()
    } catch (error) {
      console.error('Failed to update role:', error)
    }
  }

  const handleCancelInvitation = async (invitationId: string) => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'}/auth/workspace/invitations/${invitationId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token') || ''}` },
      })
      if (response.ok) await fetchInvitations()
    } catch (error) {
      console.error('Failed to cancel invitation:', error)
    }
  }

  return (
    <div className="p-6 space-y-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 mb-6">
        <div>
          <h1 className="text-3xl font-bold">Organization & Workspace</h1>
          <p className="text-muted-foreground mt-1">Manage organizations, workspaces, and team members</p>
        </div>
      </div>

      <Tabs defaultValue="organizations" onValueChange={setActiveTab} className="w-full">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="organizations">Organizations</TabsTrigger>
          <TabsTrigger value="workspaces">Workspaces</TabsTrigger>
          <TabsTrigger value="members">Members</TabsTrigger>
          <TabsTrigger value="invitations">Invitations</TabsTrigger>
        </TabsList>

        <TabsContent value="organizations" className="mt-6">
          <div className="flex justify-between items-center mb-4">
            <CardTitle className="text-lg">Organizations</CardTitle>
            <Button onClick={() => { /* create org */ }} className="gap-2">
              <Plus className="h-4 w-4" />
              Create Organization
            </Button>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {organizations.map((org) => (
              <Card key={org.id} className="hover:border-primary/50 transition-colors">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">{org.name}</CardTitle>
                    <Badge variant={org.plan === 'enterprise' ? 'default' : org.plan === 'pro' ? 'secondary' : 'outline'}>
                      {org.plan}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  {org.description && <p className="text-sm text-muted-foreground">{org.description}</p>}
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span>ID: {org.id.slice(0, 8)}...</span>
                    <span>Owner: {org.owner_id.slice(0, 8)}...</span>
                  </div>
                  <div className="flex gap-2 pt-2 border-t">
                    <Button variant="outline" size="sm" onClick={() => setEditingOrg(org)} className="gap-1">
                      <Edit className="h-4 w-4" />
                      Edit
                    </Button>
                    <Button variant="outline" size="sm" variant="destructive" onClick={() => handleDeleteOrg(org.id)} className="gap-1">
                      <Trash2 className="h-4 w-4" />
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
            {organizations.length === 0 && (
              <div className="text-center py-12">
                <Building2 className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No organizations</h3>
                <p className="text-muted-foreground mb-4">Create your first organization to get started</p>
                <Button onClick={() => { /* create org */ }} className="gap-2">
                  <Plus className="w-4 h-4" />
                  Create Organization
                </Button>
              </div>
            )}
          </TabsContent>

          <TabsContent value="workspaces" className="mt-6">
            <div className="flex justify-between items-center mb-4">
              <CardTitle className="text-lg">Workspaces</CardTitle>
              <Button onClick={handleCreateWorkspace} className="gap-2">
                <Plus className="h-4 w-4" />
                Create Workspace
              </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {workspaces.map((ws) => (
                <Card key={ws.id} className="hover:border-primary/50 transition-colors">
                  <CardHeader>
                    <CardTitle className="text-lg">{ws.name}</CardTitle>
                    <CardDescription>{ws.description || 'No description'}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Badge variant={ws.subscription_status === 'active' ? 'default' : 'secondary'}>
                        {ws.subscription_status}
                      </Badge>
                      <span>Owner: {ws.owner_id.slice(0, 8)}...</span>
                    </div>
                    <div className="flex gap-2 pt-2 border-t">
                      <Button variant="outline" size="sm" className="gap-1">
                        <Settings className="h-4 w-4" />
                        Settings
                      </Button>
                      <Button variant="outline" size="sm" variant="destructive" className="gap-1" onClick={() => handleDeleteWorkspace(ws.id)}>
                        <Trash2 className="h-4 w-4" />
                        Delete
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {workspaces.length === 0 && (
                <div className="text-center py-12">
                  <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-muted/50 flex items-center justify-center">
                    <WorkFlow className="w-6 h-6 text-muted-foreground" />
                  </div>
                  <h3 className="text-lg font-medium mb-2">No workspaces</h3>
                  <p className="text-muted-foreground mb-4">Create your first workspace to get started</p>
                  <Button onClick={handleCreateWorkspace} className="gap-2">
                    <Plus className="w-4 h-4" />
                    Create Workspace
                  </Button>
                </div>
              )}
            </TabsContent>

          <TabsContent value="members" className="mt-6">
            <div className="flex justify-between items-center mb-4">
              <CardTitle className="text-lg">Workspace Members</CardTitle>
              <Button onClick={() => setInviting(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                Invite Member
              </Button>
            </div>

            <Card>
              <CardContent>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Member</TableHead>
                      <TableHead>Role</TableHead>
                      <TableHead>Invited By</TableHead>
                      <TableHead>Joined</TableHead>
                      <TableHead className="w-48">Actions</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center text-primary text-sm font-medium">
                            {member.user.full_name?.split(' ').map(n => n[0]).join('').toUpperCase() || member.user.email[0].toUpperCase()}
                          </div>
                          <div>
                            <p className="font-medium">{member.user.full_name || member.user.email}</p>
                            <p className="text-xs text-muted-foreground">{member.user.email}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={member.role === 'admin' ? 'default' : member.role === 'editor' ? 'secondary' : 'outline'}>
                            {member.role}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">{member.invited_by?.slice(0, 8)}...</TableCell>
                        <TableCell className="text-sm text-muted-foreground">{new Date(member.created_at).toLocaleDateString()}</TableCell>
                        <TableCell>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon" className="h-8 w-8">
                                <MoreHorizontal className="w-4 h-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem onClick={() => handleUpdateRole(member.id, 'admin')}>
                                <Shield className="w-4 h-4 mr-2" />
                                Make Admin
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleUpdateRole(member.id, 'editor')}>
                                <Edit className="w-4 h-4 mr-2" />
                                Make Editor
                              </DropdownMenuItem>
                              <DropdownMenuItem onClick={() => handleUpdateRole(member.id, 'viewer')}>
                                <Eye className="w-4 h-4 mr-2" />
                                Make Viewer
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem onClick={() => handleRemoveMember(member.id)} className="text-destructive focus:text-destructive">
                                <Trash2 className="w-4 h-4 mr-2" />
                                Remove
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="invitations" className="mt-6">
            <div className="flex justify-between items-center mb-4">
              <CardTitle className="text-lg">Pending Invitations</CardTitle>
              <Button onClick={() => setInviting(true)} className="gap-2">
                <Plus className="h-4 w-4" />
                Invite Member
              </Button>
            </div>

            <Card>
              <CardContent>
                {invitations.length === 0 ? (
                  <div className="text-center py-12">
                    <Mail className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
                    <h3 className="text-lg font-medium mb-2">No pending invitations</h3>
                    <p className="text-muted-foreground mb-4">Invite team members to collaborate</p>
                    <Button onClick={() => setInviting(true)} className="gap-2">
                      <Plus className="w-4 h-4" />
                      Invite Member
                    </Button>
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Email</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead>Invited By</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead>Expires</TableHead>
                        <TableHead className="w-48">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {invitations.map((inv) => (
                        <TableRow key={inv.id}>
                          <TableCell className="font-medium">{inv.email}</TableCell>
                          <TableCell>
                            <Badge variant={inv.role === 'admin' ? 'default' : inv.role === 'editor' ? 'secondary' : 'outline'}>
                              {inv.role}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">{inv.invited_by?.slice(0, 8)}...</TableCell>
                          <TableCell>
                            <Badge variant={inv.status === 'pending' ? 'secondary' : inv.status === 'accepted' ? 'default' : 'destructive'}>
                              {inv.status}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-sm text-muted-foreground">{new Date(inv.expires_at).toLocaleDateString()}</TableCell>
                          <TableCell>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button variant="ghost" size="icon" className="h-8 w-8">
                                  <MoreHorizontal className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem onClick={() => handleCancelInvitation(inv.id)} className="text-destructive">
                                  <X className="w-4 h-4 mr-2" />
                                  Cancel Invitation
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  )
}

export default OrganizationPage
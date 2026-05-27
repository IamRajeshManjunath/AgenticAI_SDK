'use client'

import { useState } from 'react'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Shield, Users, Mail, UserMinus, Loader2, Plus, Trash2, Eye, FileText } from 'lucide-react'
import useSWR, { mutate } from 'swr'
import { useToast } from '@/hooks/use-toast'
import { memberApi, policyApi } from '@/lib/api'
import { useAuthStore } from '@/lib/auth-store'
import type { WorkspaceMember, Policy, PolicyDocument } from '@/lib/types'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import Link from 'next/link'

const membersFetcher = async (): Promise<WorkspaceMember[]> => {
  const res = await memberApi.list()
  if (res.error) throw new Error(res.error)
  return res.data ?? []
}

const policiesFetcher = async (): Promise<Policy[]> => {
  const res = await policyApi.list()
  if (res.error) throw new Error(res.error)
  return res.data ?? []
}

export default function TeamPage() {
  const { toast } = useToast()
  const token = useAuthStore((s) => s.token)

  const { data: members, error: membersError, isLoading: membersLoading } = useSWR<WorkspaceMember[]>(
    token ? 'team-members' : null,
    membersFetcher
  )
  const { data: policies, error: policiesError, isLoading: policiesLoading } = useSWR<Policy[]>(
    token ? 'team-policies' : null,
    policiesFetcher
  )

  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteEmail, setInviteEmail] = useState('')
  const [inviteRole, setInviteRole] = useState('editor')
  const [inviting, setInviting] = useState(false)
  const [viewPolicy, setViewPolicy] = useState<Policy | null>(null)

  const handleDeletePolicy = async (id: string) => {
    const res = await policyApi.delete(id)
    if (res.error) {
      toast({ title: 'Error', description: 'Failed to delete policy', variant: 'destructive' })
      return
    }
    toast({ title: 'Deleted', description: 'Policy deleted' })
    mutate('team-policies')
  }

  return (
    <DashboardLayout>
      <div className="p-6 md:p-8 space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-foreground">Team</h1>
          <p className="text-muted-foreground mt-1">
            Manage team members and access policies
          </p>
        </div>

        <Tabs defaultValue="members">
          <TabsList>
            <TabsTrigger value="members" className="gap-2">
              <Users className="w-4 h-4" />
              Members
            </TabsTrigger>
            <TabsTrigger value="policies" className="gap-2">
              <Shield className="w-4 h-4" />
              Policies
            </TabsTrigger>
          </TabsList>

          <TabsContent value="members" className="mt-6">
            <Card className="glass-card">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Workspace Members</CardTitle>
                    <CardDescription>
                      Manage who has access to this workspace
                    </CardDescription>
                  </div>
                  <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
                    <DialogTrigger asChild>
                      <Button className="gap-2">
                        <Mail className="w-4 h-4" />
                        Invite Member
                      </Button>
                    </DialogTrigger>
                    <DialogContent>
                      <DialogHeader>
                        <DialogTitle>Invite Member</DialogTitle>
                        <DialogDescription>
                          Send an invitation to join this workspace
                        </DialogDescription>
                      </DialogHeader>
                      <div className="space-y-4">
                        <div className="space-y-2">
                          <Label htmlFor="invite-email">Email Address</Label>
                          <Input
                            id="invite-email"
                            type="email"
                            placeholder="colleague@company.com"
                            value={inviteEmail}
                            onChange={(e) => setInviteEmail(e.target.value)}
                          />
                        </div>
                        <div className="space-y-2">
                          <Label htmlFor="invite-role">Role</Label>
                          <Select value={inviteRole} onValueChange={setInviteRole}>
                            <SelectTrigger id="invite-role">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="admin">Admin</SelectItem>
                              <SelectItem value="editor">Editor</SelectItem>
                              <SelectItem value="viewer">Viewer</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>
                        <Button
                          onClick={async () => {
                            if (!inviteEmail) {
                              toast({ title: 'Error', description: 'Email is required', variant: 'destructive' })
                              return
                            }
                            setInviting(true)
                            try {
                              const res = await memberApi.invite(inviteEmail, inviteRole)
                              if (res.error) throw new Error(res.error)
                              toast({ title: 'Invited', description: `Invitation sent to ${inviteEmail}` })
                              setInviteOpen(false)
                              setInviteEmail('')
                              mutate('team-members')
                            } catch (e) {
                              toast({ title: 'Error', description: e instanceof Error ? e.message : 'Failed to invite', variant: 'destructive' })
                            } finally {
                              setInviting(false)
                            }
                          }}
                          disabled={inviting}
                          className="w-full"
                        >
                          {inviting && <Loader2 className="w-4 h-4 mr-2 animate-spin" />}
                          Send Invitation
                        </Button>
                      </div>
                    </DialogContent>
                  </Dialog>
                </div>
              </CardHeader>
              <CardContent>
                {membersLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                ) : membersError ? (
                  <p className="text-destructive text-sm">Failed to load members</p>
                ) : !members?.length ? (
                  <p className="text-muted-foreground text-sm py-8 text-center">No members found</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead>Role</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {members.map((m) => (
                        <TableRow key={m.user_id}>
                          <TableCell className="font-medium">{m.full_name || '-'}</TableCell>
                          <TableCell className="text-muted-foreground">{m.email}</TableCell>
                          <TableCell>
                            <Select
                              defaultValue={m.role}
                              onValueChange={async (role) => {
                                const res = await memberApi.updateRole(m.user_id, role)
                                if (res.error) {
                                  toast({ title: 'Error', description: 'Failed to update role', variant: 'destructive' })
                                  return
                                }
                                toast({ title: 'Updated', description: `Role changed to ${role}` })
                                mutate('team-members')
                              }}
                            >
                              <SelectTrigger className="w-28 h-8 text-sm">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="admin">Admin</SelectItem>
                                <SelectItem value="editor">Editor</SelectItem>
                                <SelectItem value="viewer">Viewer</SelectItem>
                              </SelectContent>
                            </Select>
                          </TableCell>
                          <TableCell className="text-right">
                            <AlertDialog>
                              <AlertDialogTrigger asChild>
                                <Button variant="destructive" size="sm">
                                  <UserMinus className="w-3 h-3 mr-1" />
                                  Remove
                                </Button>
                              </AlertDialogTrigger>
                              <AlertDialogContent>
                                <AlertDialogHeader>
                                  <AlertDialogTitle>Remove Member</AlertDialogTitle>
                                  <AlertDialogDescription>
                                    Remove {m.email} from this workspace? They will lose access to all workspace resources.
                                  </AlertDialogDescription>
                                </AlertDialogHeader>
                                <AlertDialogFooter>
                                  <AlertDialogCancel>Cancel</AlertDialogCancel>
                                  <AlertDialogAction onClick={async () => {
                                    const res = await memberApi.remove(m.user_id)
                                    if (res.error) {
                                      toast({ title: 'Error', description: 'Failed to remove member', variant: 'destructive' })
                                      return
                                    }
                                    toast({ title: 'Removed', description: `${m.email} removed from workspace` })
                                    mutate('team-members')
                                  }}>
                                    Remove
                                  </AlertDialogAction>
                                </AlertDialogFooter>
                              </AlertDialogContent>
                            </AlertDialog>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="policies" className="mt-6">
            <Card className="glass-card">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle>Access Policies</CardTitle>
                    <CardDescription>
                      Manage IAM policies for workspace resources
                    </CardDescription>
                  </div>
                  <Link href="/policies">
                    <Button className="gap-2">
                      <Plus className="w-4 h-4" />
                      Manage Policies
                    </Button>
                  </Link>
                </div>
              </CardHeader>
              <CardContent>
                {policiesLoading ? (
                  <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
                  </div>
                ) : policiesError ? (
                  <p className="text-destructive text-sm">Failed to load policies</p>
                ) : !policies?.length ? (
                  <p className="text-muted-foreground text-sm py-8 text-center">No policies found</p>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Name</TableHead>
                        <TableHead>Description</TableHead>
                        <TableHead>Status</TableHead>
                        <TableHead className="text-right">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {policies.map((policy) => (
                        <TableRow key={policy.id}>
                          <TableCell className="font-medium font-mono text-sm">{policy.name}</TableCell>
                          <TableCell className="text-muted-foreground text-sm max-w-[200px] truncate">
                            {policy.description || '-'}
                          </TableCell>
                          <TableCell>
                            <Badge variant={policy.is_system ? 'secondary' : 'default'}>
                              {policy.is_system ? 'System' : 'Custom'}
                            </Badge>
                          </TableCell>
                          <TableCell className="text-right">
                            <div className="flex items-center justify-end gap-2">
                              <Button variant="outline" size="sm" onClick={() => setViewPolicy(policy)}>
                                <Eye className="w-3 h-3" />
                              </Button>
                              <AlertDialog>
                                <AlertDialogTrigger asChild>
                                  <Button variant="destructive" size="sm">
                                    <Trash2 className="w-3 h-3" />
                                  </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent>
                                  <AlertDialogHeader>
                                    <AlertDialogTitle>Delete Policy</AlertDialogTitle>
                                    <AlertDialogDescription>
                                      Are you sure you want to delete "{policy.name}"? This action cannot be undone.
                                    </AlertDialogDescription>
                                  </AlertDialogHeader>
                                  <AlertDialogFooter>
                                    <AlertDialogCancel>Cancel</AlertDialogCancel>
                                    <AlertDialogAction onClick={() => handleDeletePolicy(policy.id)}>
                                      Delete
                                    </AlertDialogAction>
                                  </AlertDialogFooter>
                                </AlertDialogContent>
                              </AlertDialog>
                            </div>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

        <Dialog open={!!viewPolicy} onOpenChange={(o) => !o && setViewPolicy(null)}>
          <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <FileText className="w-5 h-5" />
                {viewPolicy?.name}
              </DialogTitle>
            </DialogHeader>
            {viewPolicy && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Description</Label>
                    <p className="text-sm text-muted-foreground mt-1">
                      {viewPolicy.description || 'No description'}
                    </p>
                  </div>
                  <div>
                    <Label>Status</Label>
                    <div className="mt-1">
                      <Badge variant={viewPolicy.is_system ? 'secondary' : 'default'}>
                        {viewPolicy.is_system ? 'System' : 'Custom'}
                      </Badge>
                    </div>
                  </div>
                </div>
                <div>
                  <Label>Policy Document</Label>
                  <pre className="mt-2 p-4 rounded-lg bg-secondary text-xs font-mono overflow-x-auto whitespace-pre-wrap">
                    {JSON.stringify(viewPolicy.policy_document, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </DashboardLayout>
  )
}

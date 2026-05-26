'use client'

import { useState, type ChangeEvent, type KeyboardEvent, type MouseEvent } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import {
  ChevronDown,
  ChevronRight,
  Plus,
  Workflow,
  Wrench,
  Database,
  Settings,
  CreditCard,
  LayoutDashboard,
  Activity,
  Menu,
  X,
  Sparkles,
  FolderOpen,
  MoreHorizontal,
  Copy,
  Trash2,
  Eye,
  Bot,
  LogOut,
  User,
  Lock,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkflowStore } from '@/lib/store'
import { useAuthStore } from '@/lib/auth-store'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Avatar,
  AvatarFallback,
} from '@/components/ui/avatar'
import type { Workspace, WorkflowSchema } from '@/lib/types'

export function GlobalSidebar() {
  const pathname = usePathname()
  const [workflowsExpanded, setWorkflowsExpanded] = useState(true)
  const [editingWorkspaceId, setEditingWorkspaceId] = useState<string | null>(null)
  const [editingWorkflowId, setEditingWorkflowId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState('')

  const {
    workspaces,
    activeWorkspaceId,
    workflows,
    sidebarOpen,
    toggleSidebar,
    createWorkspace,
    setActiveWorkspace,
    updateWorkspace,
    deleteWorkspace,
    createWorkflow,
    setActiveWorkflow,
    updateWorkflow,
    deleteWorkflow,
    duplicateWorkflow,
  } = useWorkflowStore()

  const { user, logout } = useAuthStore()

  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) ?? null
  const workspaceWorkflows: WorkflowSchema[] = activeWorkspace
    ? activeWorkspace.workflows.map((id) => workflows[id]).filter(Boolean)
    : Object.values(workflows)

  const handleCreateWorkspace = () => {
    createWorkspace(`Workspace ${workspaces.length + 1}`)
  }

  const handleCreateWorkflow = () => {
    createWorkflow(`Workflow ${Object.keys(workflows).length + 1}`)
  }

  const handleLogout = () => {
    logout()
  }

  const userInitials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() ?? '??'

  return (
    <>
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 p-2 rounded-lg bg-card border border-border md:hidden"
        aria-label="Toggle sidebar"
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      <AnimatePresence>
        {sidebarOpen && (
          <motion.aside
            initial={{ x: -280, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: -280, opacity: 0 }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed left-0 top-0 h-full w-64 bg-sidebar border-r border-sidebar-border z-40 flex flex-col"
          >
            {/* Logo */}
            <div className="p-4 border-b border-sidebar-border">
              <Link href="/" className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center glow-primary-sm">
                  <Sparkles className="w-5 h-5 text-primary" />
                </div>
                <span className="text-lg font-semibold text-foreground">AgenticAI</span>
              </Link>
            </div>

            {/* Workspace Selector */}
            <div className="p-3 border-b border-sidebar-border">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    className="w-full justify-between text-sm font-medium h-9"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FolderOpen className="w-4 h-4 text-muted-foreground shrink-0" />
                      <span className="truncate">
                        {activeWorkspace?.name || 'All Workflows'}
                      </span>
                    </div>
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuItem onClick={() => setActiveWorkspace(null)}>
                    All Workflows
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  {workspaces.map((workspace) => (
                    <DropdownMenuItem
                      key={workspace.id}
                      onClick={() => setActiveWorkspace(workspace.id)}
                      className="flex items-center justify-between group"
                    >
                      {editingWorkspaceId === workspace.id ? (
                        <input
                          autoFocus
                          value={editValue}
                          onChange={(e: ChangeEvent<HTMLInputElement>) => setEditValue(e.target.value)}
                          onBlur={() => {
                            if (editValue.trim() && editValue !== workspace.name) {
                              updateWorkspace(workspace.id, { name: editValue.trim() })
                            }
                            setEditingWorkspaceId(null)
                          }}
                          onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
                            if (e.key === 'Enter') {
                              if (editValue.trim() && editValue !== workspace.name) {
                                updateWorkspace(workspace.id, { name: editValue.trim() })
                              }
                              setEditingWorkspaceId(null)
                            }
                            if (e.key === 'Escape') setEditingWorkspaceId(null)
                          }}
                          className="flex-1 bg-transparent border-b border-primary outline-none focus:ring-0 text-sm"
                          onClick={(e: MouseEvent<HTMLInputElement>) => e.stopPropagation()}
                        />
                      ) : (
                        <span
                          className="truncate flex-1 cursor-text"
                          onDoubleClick={() => {
                            setEditValue(workspace.name)
                            setEditingWorkspaceId(workspace.id)
                          }}
                        >
                          {workspace.name}
                        </span>
                      )}

                      <Trash2
                        className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity ml-2 shrink-0"
                        onClick={(e: MouseEvent) => {
                          e.stopPropagation()
                          deleteWorkspace(workspace.id)
                        }}
                      />
                    </DropdownMenuItem>
                  ))}
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={handleCreateWorkspace}>
                    <Plus className="w-4 h-4 mr-2" />
                    Create Workspace
                  </DropdownMenuItem>
                  {activeWorkspace && (
                    <DropdownMenuItem
                      onClick={(e: MouseEvent) => {
                        e.preventDefault()
                        setEditValue(activeWorkspace.name)
                        setEditingWorkspaceId(activeWorkspace.id)
                      }}
                    >
                      <Settings className="w-4 h-4 mr-2" />
                      Rename Active Workspace
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-1">
              <Link
                href="/"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <LayoutDashboard className="w-4 h-4" />
                Dashboard
              </Link>

              <Link
                href="/agent"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/agent'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <Bot className="w-4 h-4" />
                Master Agent
              </Link>

              <div className="pt-3">
                <button
                  onClick={() => setWorkflowsExpanded(!workflowsExpanded)}
                  className="flex items-center justify-between w-full px-3 py-2 text-xs font-medium text-muted-foreground uppercase tracking-wider hover:text-foreground transition-colors"
                >
                  <span>Workflows</span>
                  {workflowsExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>

                <AnimatePresence>
                  {workflowsExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="space-y-1 mt-1">
                        {workspaceWorkflows.map((workflow) => (
                          <div
                            key={workflow.id}
                            className={cn(
                              'group flex items-center justify-between rounded-lg transition-colors',
                              pathname === `/workflows/${workflow.id}`
                                ? 'bg-sidebar-accent'
                                : 'hover:bg-sidebar-accent/50'
                            )}
                          >
                            <Link
                              href={`/workflows/${workflow.id}`}
                              onClick={() => setActiveWorkflow(workflow.id)}
                              className="flex items-center gap-3 px-3 py-2 flex-1 min-w-0"
                            >
                              <Workflow className="w-4 h-4 shrink-0 text-primary" />
                              {editingWorkflowId === workflow.id ? (
                                <input
                                  autoFocus
                                  value={editValue}
                                  onChange={(e: ChangeEvent<HTMLInputElement>) => setEditValue(e.target.value)}
                                  onBlur={() => {
                                    if (editValue.trim() && editValue !== workflow.name) {
                                      updateWorkflow(workflow.id, { name: editValue.trim() })
                                    }
                                    setEditingWorkflowId(null)
                                  }}
                                  onKeyDown={(e: KeyboardEvent<HTMLInputElement>) => {
                                    if (e.key === 'Enter') {
                                      if (editValue.trim() && editValue !== workflow.name) {
                                        updateWorkflow(workflow.id, { name: editValue.trim() })
                                      }
                                      setEditingWorkflowId(null)
                                    }
                                    if (e.key === 'Escape') setEditingWorkflowId(null)
                                  }}
                                  className="text-sm border-b border-primary bg-transparent outline-none flex-1 min-w-0"
                                  onClick={(e: MouseEvent<HTMLInputElement>) => e.preventDefault()}
                                />
                              ) : (
                                <span
                                  className="text-sm truncate cursor-text flex-1"
                                  onDoubleClick={() => {
                                    setEditValue(workflow.name)
                                    setEditingWorkflowId(workflow.id)
                                  }}
                                >
                                  {workflow.name}
                                </span>
                              )}
                            </Link>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-8 w-8 p-0 opacity-0 group-hover:opacity-100 transition-opacity mr-1"
                                >
                                  <MoreHorizontal className="w-4 h-4" />
                                </Button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent align="end">
                                <DropdownMenuItem asChild>
                                  <Link href={`/observability/${workflow.id}`}>
                                    <Eye className="w-4 h-4 mr-2" />
                                    Observability
                                  </Link>
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => {
                                  setEditValue(workflow.name)
                                  setEditingWorkflowId(workflow.id)
                                }}>
                                  <Plus className="w-4 h-4 mr-2" />
                                  Rename
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={() => duplicateWorkflow(workflow.id)}>
                                  <Copy className="w-4 h-4 mr-2" />
                                  Duplicate
                                </DropdownMenuItem>
                                <DropdownMenuSeparator />
                                <DropdownMenuItem
                                  onClick={() => deleteWorkflow(workflow.id)}
                                  className="text-destructive"
                                >
                                  <Trash2 className="w-4 h-4 mr-2" />
                                  Delete
                                </DropdownMenuItem>
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        ))}

                        <Button
                          onClick={handleCreateWorkflow}
                          variant="ghost"
                          className="w-full justify-start gap-3 px-3 py-2 h-auto text-muted-foreground hover:text-foreground"
                        >
                          <Plus className="w-4 h-4" />
                          <span className="text-sm">Create Workflow</span>
                        </Button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              <Link
                href="/tools"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/tools'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <Wrench className="w-4 h-4" />
                Global Tools
              </Link>

              <Link
                href="/rag"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/rag'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <Database className="w-4 h-4" />
                RAG Sources
              </Link>

              <Link
                href="/activity"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/activity'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <Activity className="w-4 h-4" />
                Activity Log
              </Link>

              <Link
                href="/secrets"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/secrets'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <Lock className="w-4 h-4" />
                Secrets
              </Link>
            </nav>

            {/* Bottom Section: Settings + User */}
            <div className="p-3 border-t border-sidebar-border space-y-1">
              <Link
                href="/settings"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/settings'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <Settings className="w-4 h-4" />
                Settings
              </Link>
              <Link
                href="/billing"
                className={cn(
                  'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors',
                  pathname === '/billing'
                    ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                    : 'text-sidebar-foreground hover:bg-sidebar-accent/50'
                )}
              >
                <CreditCard className="w-4 h-4" />
                Billing
              </Link>

              {/* User section */}
              <div className="pt-2 border-t border-sidebar-border mt-2">
                <div className="flex items-center gap-3 px-3 py-2">
                  <Avatar className="w-8 h-8">
                    <AvatarFallback className="text-xs bg-primary/20 text-primary">
                      {userInitials}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate text-foreground">
                      {user?.full_name || user?.email || 'User'}
                    </p>
                    <p className="text-xs text-muted-foreground truncate">
                      {user?.email || ''}
                    </p>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 shrink-0"
                    onClick={handleLogout}
                    title="Sign out"
                  >
                    <LogOut className="w-4 h-4 text-muted-foreground hover:text-destructive" />
                  </Button>
                </div>
              </div>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}

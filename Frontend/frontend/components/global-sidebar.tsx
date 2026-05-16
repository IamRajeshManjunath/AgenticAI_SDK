'use client'

import { useState } from 'react'
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
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { useWorkflowStore } from '@/lib/store'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'

export function GlobalSidebar() {
  const pathname = usePathname()
  const [workflowsExpanded, setWorkflowsExpanded] = useState(true)
  
  const {
    workspaces,
    activeWorkspaceId,
    workflows,
    activeWorkflowId,
    sidebarOpen,
    toggleSidebar,
    createWorkspace,
    setActiveWorkspace,
    createWorkflow,
    setActiveWorkflow,
    deleteWorkflow,
    duplicateWorkflow,
  } = useWorkflowStore()

  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId)
  const workspaceWorkflows = activeWorkspace
    ? activeWorkspace.workflows.map((id) => workflows[id]).filter(Boolean)
    : Object.values(workflows)

  const handleCreateWorkspace = () => {
    const name = `Workspace ${workspaces.length + 1}`
    createWorkspace(name)
  }

  const handleCreateWorkflow = () => {
    const name = `Workflow ${Object.keys(workflows).length + 1}`
    createWorkflow(name)
  }

  return (
    <>
      {/* Mobile Toggle */}
      <button
        onClick={toggleSidebar}
        className="fixed top-4 left-4 z-50 p-2 rounded-lg bg-card border border-border md:hidden"
      >
        {sidebarOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Sidebar */}
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
                <span className="text-lg font-semibold text-foreground">Harpy.AI</span>
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
                      <FolderOpen className="w-4 h-4 text-muted-foreground" />
                      <span className="truncate">
                        {activeWorkspace?.name || 'All Workflows'}
                      </span>
                    </div>
                    <ChevronDown className="w-4 h-4 text-muted-foreground shrink-0" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="w-56">
                  <DropdownMenuItem onClick={() => setActiveWorkspace(null as any)}>
                    All Workflows
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  {workspaces.map((workspace) => (
                    <DropdownMenuItem
                      key={workspace.id}
                      onClick={() => setActiveWorkspace(workspace.id)}
                      className="flex items-center justify-between group"
                    >
                      <span className="truncate flex-1">{workspace.name}</span>
                      <Trash2 
                        className="w-3.5 h-3.5 text-muted-foreground hover:text-destructive opacity-0 group-hover:opacity-100 transition-opacity ml-2"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Are you sure you want to delete workspace "${workspace.name}"?`)) {
                            deleteWorkspace(workspace.id);
                          }
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
                    <DropdownMenuItem onClick={() => {
                      const newName = prompt('Enter new workspace name:', activeWorkspace.name)
                      if (newName) updateWorkspace(activeWorkspace.id, { name: newName })
                    }}>
                      <Settings className="w-4 h-4 mr-2" />
                      Rename Active Workspace
                    </DropdownMenuItem>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Navigation */}
            <nav className="flex-1 overflow-y-auto scrollbar-thin p-3 space-y-1">
              {/* Dashboard Link */}
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

              {/* Workflows Section */}
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
                              <span className="text-sm truncate">{workflow.name}</span>
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
                                  const newName = prompt('Enter new workflow name:', workflow.name)
                                  if (newName) updateWorkflow(workflow.id, { name: newName })
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

              {/* Global Tools */}
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

              {/* RAG Sources */}
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

              {/* Activity */}
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
            </nav>

            {/* Bottom Section */}
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
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>
  )
}

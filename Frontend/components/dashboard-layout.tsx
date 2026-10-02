'use client'

import { GlobalSidebar } from '@/components/global-sidebar'
import { useWorkflowStore } from '@/lib/store'
import { useAuthStore } from '@/lib/auth-store'
import { ErrorBoundary } from '@/components/error-boundary'
import { cn } from '@/lib/utils'
import { User } from 'lucide-react'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Settings, LogOut, User as UserIcon, Workspace, Plus } from 'lucide-react'
import Link from 'next/link'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { sidebarOpen, workspaces, activeWorkspaceId, setActiveWorkspace, createWorkspace, toggleSidebar } = useWorkflowStore()
  const { user, logout } = useAuthStore()
  
  const activeWorkspace = workspaces.find((w) => w.id === activeWorkspaceId) ?? null
  const userInitials = user?.full_name
    ? user.full_name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
    : user?.email?.slice(0, 2).toUpperCase() ?? '??'

  return (
    <div className="min-h-screen bg-background">
      <GlobalSidebar />
      <main
        className="min-h-screen transition-all duration-300 md:ml-64"
      >
        {/* Top Header Bar */}
        <header className="sticky top-0 z-30 w-full border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 md:ml-64 transition-all duration-300">
          <div className="flex h-16 items-center justify-between px-4 md:px-6 lg:px-8">
            {/* Mobile menu toggle */}
            <button
              onClick={() => toggleSidebar()}
              className="md:hidden p-2 rounded-lg hover:bg-accent transition-colors"
              aria-label="Toggle sidebar"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            
            {/* Page title area */}
            <div className="flex-1" />
            
            {/* Right side actions */}
            <div className="flex items-center gap-3">
              {/* Workspace Selector */}
              <div className="hidden md:flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Workspace:</span>
                <select
                  value={activeWorkspaceId || ''}
                  onChange={(e) => setActiveWorkspace(e.target.value || null)}
                  className="bg-background border border-border rounded-lg px-3 py-1.5 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-ring"
                >
                  <option value="">All Workflows</option>
                  {workspaces.map((w) => (
                    <option key={w.id} value={w.id}>{w.name}</option>
                  ))}
                </select>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => createWorkspace(`Workspace ${workspaces.length + 1}`)}
                  className="h-8 gap-1"
                >
                  <span className="hidden sm:inline">New</span>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                </Button>
              </div>
              
              {/* User Menu */}
              <div className="relative">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="ghost" className="relative h-9 w-9 rounded-full">
                      <div className="relative w-9 h-9 rounded-full bg-primary/20 flex items-center justify-center">
                        <User className="w-5 h-5 text-primary" />
                      </div>
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-56">
                    <div className="p-2">
                      <p className="text-sm font-medium truncate">{user?.full_name || 'User'}</p>
                      <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
                    </div>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem asChild>
                      <Link href="/settings">
                        <Settings className="w-4 h-4 mr-2" />
                        Settings
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuItem asChild>
                      <Link href="/team">
                        <User className="w-4 h-4 mr-2" />
                        Team
                      </Link>
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem onClick={logout}>
                      <LogOut className="w-4 h-4 mr-2" />
                      Sign out
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>
          </div>
        </header>

        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </main>
    </div>
  )
}
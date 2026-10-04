'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { LogOut, Menu, Settings, Users } from 'lucide-react'
import { GlobalSidebar } from '@/components/global-sidebar'
import { ErrorBoundary } from '@/components/error-boundary'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/lib/auth-store'
import { useWorkflowStore } from '@/lib/store'

interface DashboardLayoutProps {
  children: React.ReactNode
}

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/agent': 'Master Agent',
  '/activity': 'Activity',
  '/billing': 'Billing',
  '/integrations': 'Integrations',
  '/observability': 'Observability',
  '/policies': 'IAM policies',
  '/rag': 'Knowledge sources',
  '/secrets': 'Secrets',
  '/settings': 'Settings',
  '/team': 'Team',
  '/tools': 'Tools',
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const pathname = usePathname()
  const toggleSidebar = useWorkflowStore((state) => state.toggleSidebar)
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const pageTitle =
    pageTitles[pathname] ??
    (pathname.startsWith('/workflows/') ? 'Workflow builder' : 'AgenticAI')
  const initials = (user?.full_name || user?.email || 'U')
    .split(/[\s@._-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('')

  return (
    <div className="min-h-screen bg-background">
      <GlobalSidebar />
      <main className="min-h-screen md:ml-64">
        <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-border bg-background/95 px-4 backdrop-blur supports-[backdrop-filter]:bg-background/80 md:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              aria-label="Open navigation"
              onClick={toggleSidebar}
            >
              <Menu className="h-5 w-5" />
            </Button>
            <div className="min-w-0">
              <p className="truncate text-sm font-semibold">{pageTitle}</p>
              <p className="hidden text-xs text-muted-foreground sm:block">
                AgenticAI workspace
              </p>
            </div>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                className="h-10 gap-2 px-2"
                aria-label="Open account menu"
              >
                <Avatar className="h-8 w-8">
                  <AvatarFallback className="bg-primary/10 text-xs font-semibold text-primary">
                    {initials || 'U'}
                  </AvatarFallback>
                </Avatar>
                <span className="hidden max-w-40 truncate text-sm sm:inline">
                  {user?.full_name || user?.email || 'Account'}
                </span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <div className="px-2 py-1.5">
                <p className="truncate text-sm font-medium">
                  {user?.full_name || 'Account'}
                </p>
                {user?.email && (
                  <p className="truncate text-xs text-muted-foreground">{user.email}</p>
                )}
              </div>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings">
                  <Settings className="mr-2 h-4 w-4" />
                  Settings
                </Link>
              </DropdownMenuItem>
              <DropdownMenuItem asChild>
                <Link href="/team">
                  <Users className="mr-2 h-4 w-4" />
                  Team
                </Link>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" />
                Sign out
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        <ErrorBoundary>
          {children}
        </ErrorBoundary>
      </main>
    </div>
  )
}

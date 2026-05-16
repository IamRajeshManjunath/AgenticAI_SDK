'use client'

import { GlobalSidebar } from '@/components/global-sidebar'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface DashboardLayoutProps {
  children: React.ReactNode
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  const { sidebarOpen } = useWorkflowStore()

  return (
    <div className="min-h-screen bg-background">
      <GlobalSidebar />
      <main
        className={cn(
          'min-h-screen transition-all duration-300',
          sidebarOpen ? 'md:ml-64' : 'ml-0'
        )}
      >
        {children}
      </main>
    </div>
  )
}

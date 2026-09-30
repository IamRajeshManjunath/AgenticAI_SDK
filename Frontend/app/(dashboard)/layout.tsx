"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Database, Plug, Activity, Settings, BarChart3, Shield, ChevronLeft, ChevronRight, Menu, X, Bell, User, LogOut, Search, Command, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Integrations", href: "/integrations", icon: Plug, badge: "46" },
  { name: "Observability", href: "/observability", icon: Activity },
  { name: "Skills", href: "/skills", icon: BookOpen, badge: "7" },
  { name: "Database Routes", href: "/settings/database-routes", icon: Database },
  { name: "Governance", href: "/governance", icon: Shield },
  { name: "Settings", href: "/settings", icon: Settings },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const pathname = usePathname();

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background">
        {/* Mobile header */}
        <div className="lg:hidden fixed top-0 left-0 right-0 z-50 bg-background border-b border-border">
          <div className="flex items-center justify-between h-16 px-4">
            <Button variant="ghost" size="icon" onClick={() => setMobileOpen(true)}>
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-lg font-semibold">AgenticAI</h1>
            <div className="w-10" />
          </div>
        </div>

        {/* Sidebar */}
        <aside
          className={cn(
            "fixed lg:static inset-y-0 left-0 z-40 bg-background border-r border-border transition-all duration-300",
            collapsed ? "w-16" : "w-64",
            mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
          )}
        >
          <div className="flex flex-col h-full">
            {/* Logo */}
            <div className={cn("flex items-center justify-between h-16 px-4 border-b", collapsed && "justify-center")}>
              {!collapsed && (
                <Link href="/dashboard" className="flex items-center gap-2">
                  <div className="p-2 bg-primary rounded-lg">
                    <Activity className="h-5 w-5 text-primary-foreground" />
                  </div>
                  <span className="font-bold text-lg">AgenticAI</span>
                </Link>
              )}
              {collapsed && (
                <Link href="/dashboard" className="p-2">
                  <div className="p-2 bg-primary rounded-lg">
                    <Activity className="h-5 w-5 text-primary-foreground" />
                  </div>
                </Link>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setCollapsed(!collapsed)}
                className={cn("ml-auto", collapsed && "mx-auto")}
              >
                {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronLeft className="h-4 w-4" />}
              </Button>
            </div>

            {/* Navigation */}
            <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
              {navigation.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <Tooltip key={item.name} disabled={!collapsed}>
                    <TooltipTrigger asChild>
                      <Link
                        href={item.href}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors",
                          isActive
                            ? "bg-primary text-primary-foreground"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
                          collapsed && "justify-center"
                        )}
                      >
                        <item.icon className="h-5 w-5 flex-shrink-0" />
                        {!collapsed && (
                          <>
                            <span>{item.name}</span>
                            {item.badge && (
                              <span className="ml-auto px-2 py-0.5 text-xs bg-primary/20 text-primary rounded-full">
                                {item.badge}
                              </span>
                            )}
                          </>
                        )}
                      </Link>
                    </TooltipTrigger>
                    <TooltipContent side="right" align="center">
                      <p>{item.name}</p>
                    </TooltipContent>
                  </Tooltip>
                );
              })}
            </nav>

            {/* Footer */}
            <div className="p-4 border-t">
              <Tooltip disabled={!collapsed}>
                <TooltipTrigger asChild>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button
                        variant="ghost"
                        className={cn("w-full justify-start gap-3", collapsed && "justify-center")}
                      >
                        <Avatar className="h-8 w-8">
                          <AvatarImage src="https://github.com/shadcn.png" alt="User" />
                          <AvatarFallback>U</AvatarFallback>
                        </Avatar>
                        {!collapsed && (
                          <div className="text-left flex-1">
                            <p className="text-sm font-medium">User</p>
                            <p className="text-xs text-muted-foreground">admin@agenticai.dev</p>
                          </div>
                        )}
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end" className={cn(collapsed && "w-48")}>
                      <DropdownMenuLabel>My Account</DropdownMenuLabel>
                      <DropdownMenuItem>Profile</DropdownMenuItem>
                      <DropdownMenuItem>API Keys</DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem className="text-red-600" onClick={() => { /* logout */ }}>
                        <LogOut className="h-4 w-4 mr-2" />
                        Sign out
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </TooltipTrigger>
                <TooltipContent side="right" align="center">
                  <p>User Menu</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </div>
        </aside>

        {/* Mobile overlay */}
        {mobileOpen && (
          <div
            className="fixed inset-0 z-30 bg-black/50 lg:hidden"
            onClick={() => setMobileOpen(false)}
          />
        )}

        {/* Main content */}
        <main
          className={cn(
            "lg:ml-64 min-h-screen transition-all duration-300",
            collapsed ? "lg:ml-16" : ""
          )}
        >
          <div className="lg:ml-0">
            {/* Top bar */}
            <header className="sticky top-0 z-20 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 border-b border-border">
              <div className="flex items-center justify-between h-16 px-4 lg:px-8">
                <div className="flex items-center gap-4 flex-1">
                  <div className="relative w-full max-w-md hidden md:block">
                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" size={18} />
                    <Input
                      placeholder="Search integrations, configs, logs..."
                      className="pl-10"
                    />
                    <kbd className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-muted-foreground bg-muted px-1.5 py-0.5 rounded">
                      ⌘K
                    </kbd>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Button variant="ghost" size="icon" className="relative">
                        <Bell className="h-5 w-5" />
                        <span className="absolute top-1 right-1 h-2 w-2 bg-red-500 rounded-full" />
                      </Button>
                    </TooltipTrigger>
                    <TooltipContent>Notifications</TooltipContent>
                  </Tooltip>
                </div>
              </div>
            </header>

            {/* Page content */}
            <div className="p-4 lg:p-8">
              {children}
            </div>
          </div>
        </main>
      </div>
    </TooltipProvider>
  );
}
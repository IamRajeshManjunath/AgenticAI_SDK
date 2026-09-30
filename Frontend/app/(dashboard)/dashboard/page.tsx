import Link from "next/link";
import { Activity, Plug, Database, Activity as ActivityIcon, Shield, Settings, TrendingUp, DollarSign, Zap, AlertTriangle, Server, CheckCircle, AlertCircle, XCircle, ExternalLink } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

const stats = [
  { name: "Total Requests", value: "28,452", change: "+12.3%", icon: Activity, color: "text-blue-600", bg: "bg-blue-100" },
  { name: "Total Cost", value: "$245.40", change: "+8.7%", icon: DollarSign, color: "text-green-600", bg: "bg-green-100" },
  { name: "Avg Latency", value: "892ms", change: "-5.2%", icon: Zap, color: "text-yellow-600", bg: "bg-yellow-100" },
  { name: "Error Rate", value: "1.2%", change: "+0.3%", icon: AlertTriangle, color: "text-red-600", bg: "bg-red-100" },
];

const quickActions = [
  { name: "Add Integration", href: "/integrations", icon: Plug, description: "Browse and install new integrations" },
  { name: "Configure DB Routes", href: "/settings/database-routes", icon: Database, description: "Set up purpose-bound databases" },
  { name: "View Observability", href: "/observability", icon: ActivityIcon, description: "Monitor traces, costs, health" },
  { name: "Governance Events", href: "/governance", icon: Shield, description: "Review compliance and audit logs" },
];

const recentActivity = [
  { type: "INTEGRATION_INSTALLED", message: "Installed langchain-tavily v0.3.0", time: "2 min ago", status: "success" },
  { type: "DB_ROUTE_CREATED", message: "Created vector_store route: primary-qdrant", time: "15 min ago", status: "success" },
  { type: "COST_ALERT", message: "Monthly spend reached 80% of budget ($400/$500)", time: "1 hour ago", status: "warning" },
  { type: "SCHEMA_DRIFT", message: "Vector dimension mismatch detected in staging", time: "3 hours ago", status: "error" },
  { type: "HEALTH_CHECK", message: "All database connections healthy", time: "5 hours ago", status: "success" },
];

const systemHealth = [
  { name: "PostgreSQL (Checkpointer)", status: "healthy", latency: "12ms" },
  { name: "Qdrant (Vector Store)", status: "healthy", latency: "45ms" },
  { name: "Redis (Cache)", status: "healthy", latency: "3ms" },
  { name: "OpenAI API", status: "degraded", latency: "1.2s" },
  { name: "LangGraph Server", status: "healthy", latency: "56ms" },
  { name: "E2B Sandbox", status: "error", latency: "N/A" },
];

function StatCard({ name, value, change, icon: Icon, color, bg }: typeof stats[0]) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{name}</CardTitle>
        <div className={cn("p-2 rounded-lg", bg)}>
          <Icon className={cn("h-4 w-4", color)} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className="text-xs text-muted-foreground">{change} vs last period</p>
      </CardContent>
    </Card>
  );
}

function HealthItem({ name, status, latency }: typeof systemHealth[0]) {
  const statusConfig = {
    healthy: { icon: CheckCircle, color: "text-green-500", bg: "bg-green-100", label: "Healthy" },
    degraded: { icon: AlertCircle, color: "text-yellow-500", bg: "bg-yellow-100", label: "Degraded" },
    error: { icon: XCircle, color: "text-red-500", bg: "bg-red-100", label: "Error" },
  };
  const config = statusConfig[status];
  const Icon = config.icon;

  return (
    <div className="flex items-center justify-between py-2 border-b last:border-0">
      <div className="flex items-center gap-3">
        <div className={cn("p-1.5 rounded", config.bg)}>
          <Icon className={cn("h-4 w-4", config.color)} />
        </div>
        <span className="text-sm font-medium">{name}</span>
      </div>
      <div className="flex items-center gap-3">
        <Badge variant="secondary" className={cn("gap-1", config.bg, config.color)}>
          <Icon className="h-3 w-3" />
          {config.label}
        </Badge>
        <span className="text-sm text-muted-foreground font-mono">{latency}</span>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground">Overview of your AgenticAI workspace</p>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <StatCard key={stat.name} {...stat} />
        ))}
      </div>

      {/* Quick Actions & System Health */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {quickActions.map((action) => (
              <Link
                key={action.name}
                href={action.href}
                className="flex items-center gap-3 p-3 rounded-lg hover:bg-accent transition-colors"
              >
                <div className="p-2 bg-primary/10 rounded-lg">
                  <action.icon className="h-5 w-5 text-primary" />
                </div>
                <div className="flex-1">
                  <p className="font-medium">{action.name}</p>
                  <p className="text-sm text-muted-foreground">{action.description}</p>
                </div>
                <ExternalLink className="h-4 w-4 text-muted-foreground" />
              </Link>
            ))}
          </CardContent>
        </Card>

        {/* System Health */}
        <Card>
          <CardHeader>
            <CardTitle>System Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-0">
              {systemHealth.map((item) => (
                <HealthItem key={item.name} {...item} />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Activity */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Recent Activity</CardTitle>
            <Button variant="ghost" size="sm" asChild>
              <Link href="/activity">View All</Link>
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {recentActivity.map((activity, index) => (
              <div key={index} className="flex items-center gap-4 p-3 rounded-lg hover:bg-accent/50">
                <div className="p-2 rounded-lg bg-muted">
                  {activity.status === "success" && <CheckCircle className="h-5 w-5 text-green-600" />}
                  {activity.status === "warning" && <AlertCircle className="h-5 w-5 text-yellow-600" />}
                  {activity.status === "error" && <XCircle className="h-5 w-5 text-red-600" />}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{activity.message}</p>
                  <p className="text-xs text-muted-foreground">{activity.type}</p>
                </div>
                <Badge variant="outline" className="text-xs">
                  {activity.time}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
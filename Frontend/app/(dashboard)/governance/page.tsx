import Link from 'next/link'
import { Activity, KeyRound, ScrollText, ShieldCheck, Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const governanceAreas = [
  {
    title: 'Audit activity',
    description: 'Review recorded workspace activity and operational events.',
    href: '/activity',
    icon: Activity,
    action: 'View activity',
  },
  {
    title: 'Policies',
    description: 'Manage the policy rules configured for this workspace.',
    href: '/policies',
    icon: ScrollText,
    action: 'Manage policies',
  },
  {
    title: 'API keys',
    description: 'Create and revoke credentials used to access the platform.',
    href: '/api-keys',
    icon: KeyRound,
    action: 'Manage API keys',
  },
  {
    title: 'Access control',
    description: 'Review workspace roles and member permissions.',
    href: '/rbac',
    icon: Users,
    action: 'Manage access',
  },
]

export default function GovernancePage() {
  return (
    <main className="space-y-6 p-6 md:p-8">
      <header>
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-7 w-7 text-primary" />
          <h1 className="text-3xl font-bold tracking-tight">Governance</h1>
        </div>
        <p className="mt-2 text-muted-foreground">
          Workspace controls and audit surfaces, backed by the platform services.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        {governanceAreas.map(({ title, description, href, icon: Icon, action }) => (
          <Card key={href}>
            <CardHeader>
              <div className="flex items-center gap-3">
                <Icon className="h-5 w-5 text-primary" />
                <CardTitle>{title}</CardTitle>
              </div>
              <CardDescription>{description}</CardDescription>
            </CardHeader>
            <CardContent>
              <Button asChild variant="outline">
                <Link href={href}>{action}</Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </main>
  )
}

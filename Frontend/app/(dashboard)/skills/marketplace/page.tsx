import Link from 'next/link'
import { DashboardLayout } from '@/components/dashboard-layout'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export default function SkillsMarketplacePage() {
  return (
    <DashboardLayout>
      <main className="mx-auto w-full max-w-4xl p-6 md:p-8">
        <Card>
          <CardHeader>
            <CardTitle>External skills catalog is not configured</CardTitle>
            <CardDescription>
              This workspace can manage and synchronize configured skill sources, but it does not have a public marketplace catalog.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild>
              <Link href="/skills">Manage workspace skills</Link>
            </Button>
          </CardContent>
        </Card>
      </main>
    </DashboardLayout>
  )
}
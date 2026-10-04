import Link from 'next/link'
import { AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function HITLDashboard() {
  return (
    <main className="mx-auto max-w-3xl p-6">
      <Card>
        <CardHeader>
          <CardTitle>Human-in-the-loop approvals</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-start gap-3 text-muted-foreground">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <p>
              The API currently supports approving or rejecting an active workflow execution, but does not
              provide a pending-approvals queue. Use the workflow execution monitor to follow an active run.
            </p>
          </div>
          <Button asChild>
            <Link href="/dashboard">Open dashboard</Link>
          </Button>
        </CardContent>
      </Card>
    </main>
  )
}

'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { CheckCircle2, XCircle, Loader2, AlertTriangle, MessageSquare, User } from 'lucide-react'
import { useHITLApproval } from '@/lib/hooks'
import { useWorkflowStore } from '@/lib/store'
import { cn } from '@/lib/utils'

interface HITLApprovalCardProps {
  request: {
    id: string
    agent_id: string
    proposed_action: string
    proposed_output: string
    timestamp: number
    status: 'pending' | 'approved' | 'rejected'
    agent_name?: string
  }
  onUpdate: () => void
}

export function HITLApprovalCard({ request, onUpdate }: HITLApprovalCardProps) {
  const { approve, reject, isLoading } = useHITLApproval()
  const [feedback, setFeedback] = useState('')

  if (request.status !== 'pending') {
    return null
  }

  return (
    <Card className="border-warning/30 bg-warning/5">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-warning/20">
              <User className="w-5 h-5 text-warning" />
            </div>
            <div>
              <CardTitle className="text-base font-medium">{request.agent_name || request.agent_id}</CardTitle>
              <p className="text-xs text-muted-foreground">
                {new Date(request.timestamp).toLocaleString()}
              </p>
            </div>
          </div>
          <Badge variant="secondary" className="bg-warning text-warning-foreground">
            <AlertTriangle className="w-3 h-3 mr-1" />
            Awaiting Review
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label className="text-sm font-medium">Proposed Action</Label>
          <div className="p-3 rounded-lg bg-muted/50 border border-border font-mono text-sm whitespace-pre-wrap max-h-48 overflow-auto">
            {request.proposed_action}
          </div>
        </div>

        <div className="space-y-2">
          <Label className="text-sm font-medium">Proposed Output</Label>
          <div className="p-3 rounded-lg bg-muted/50 border border-border font-mono text-sm whitespace-pre-wrap max-h-64 overflow-auto">
            {request.proposed_output}
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="feedback" className="text-sm font-medium">
            Feedback (Optional)
          </Label>
          <Textarea
            id="feedback"
            placeholder="Add feedback for the agent..."
            value={feedback}
            onChange={(e) => setFeedback(e.target.value)}
            rows={3}
            className="bg-background"
          />
        </div>

        <div className="flex items-center gap-3 pt-2 border-t pt-4">
          <Button
            variant="destructive"
            onClick={() => {
              if (!window.confirm('Are you sure you want to reject this action?')) return
              useHITLApproval().reject(request.id, 'agent_id_placeholder', feedback)
            }}
            disabled
            className="flex-1 gap-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
            Reject
          </Button>
          <Button
            onClick={() => {
              useHITLApproval().approve(request.id, 'agent_id_placeholder', feedback)
            }}
            className="flex-1 gap-2 glow-primary-sm"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            Approve
          </Button>
        </div>
      </div>
    </CardContent>
  </Card>
)
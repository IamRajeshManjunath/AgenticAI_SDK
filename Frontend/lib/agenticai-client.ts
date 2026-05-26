/**
 * TypeScript client SDK for AgenticAI — run workflows from any application.
 *
 * Usage:
 *   const client = new AgenticAI({ apiKey: 'wfk_a1b2c3d4e5f6...' })
 *   const result = await client.run('What are your business hours?')
 *   console.log(result.messages.at(-1)?.content)
 */

export type AgenticAIResult = {
  thread_id: string
  status: 'complete' | 'interrupted'
  messages: Array<{ type: string; content: string; tool_calls?: unknown[] }>
  scratchpad: Record<string, unknown>
  retrieved_context: Array<Record<string, unknown>>
  inner_thoughts: Array<Record<string, unknown>>
  next_step: string | null
}

export class AgenticAI {
  private apiKey: string
  private baseUrl: string
  private timeout: number

  constructor(opts: {
    apiKey: string
    baseUrl?: string
    timeout?: number
  }) {
    this.apiKey = opts.apiKey
    this.baseUrl = opts.baseUrl ?? 'http://localhost:8000'
    this.timeout = opts.timeout ?? 120_000
  }

  async run(
    inputMessage: string,
    opts?: {
      workflowId?: string
      threadId?: string
      initialScratchpad?: Record<string, unknown>
    },
  ): Promise<AgenticAIResult> {
    const body: Record<string, unknown> = { input_message: inputMessage }
    if (opts?.workflowId) body.workflow_id = opts.workflowId
    if (opts?.threadId) body.thread_id = opts.threadId
    if (opts?.initialScratchpad) body.initial_scratchpad = opts.initialScratchpad

    const res = await this._post('/api/v1/workflow/run', body)
    return res.json()
  }

  async runById(
    workflowId: string,
    inputMessage: string,
    opts?: {
      threadId?: string
      initialScratchpad?: Record<string, unknown>
    },
  ): Promise<AgenticAIResult> {
    const body: Record<string, unknown> = { input_message: inputMessage }
    if (opts?.threadId) body.thread_id = opts.threadId
    if (opts?.initialScratchpad) body.initial_scratchpad = opts.initialScratchpad

    const res = await this._post(`/api/v1/workflow/run/${workflowId}`, body)
    return res.json()
  }

  lastMessage(result: AgenticAIResult): string {
    const msgs = result.messages
    if (!msgs || msgs.length === 0) return ''
    return msgs[msgs.length - 1]?.content ?? ''
  }

  private async _post(path: string, body: unknown): Promise<Response> {
    const controller = new AbortController()
    const timer = setTimeout(() => controller.abort(), this.timeout)

    try {
      const res = await fetch(`${this.baseUrl}${path}`, {
        method: 'POST',
        headers: {
          'X-API-Key': this.apiKey,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(body),
        signal: controller.signal,
      })

      if (!res.ok) {
        const errBody = await res.text()
        throw new Error(`AgenticAI error ${res.status}: ${errBody}`)
      }

      return res
    } finally {
      clearTimeout(timer)
    }
  }
}

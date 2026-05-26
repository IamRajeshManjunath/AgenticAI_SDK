export interface BlogPost {
  slug: string
  title: string
  description: string
  date: string
  author: string
  tags: string[]
  content: string
}

export const blogPosts: BlogPost[] = [
  {
    slug: 'build-customer-support-agent',
    title: 'How to Build a Customer Support Agent in 5 Minutes',
    description: 'Create a multi-agent customer support workflow that answers FAQs and escalates to humans when needed.',
    date: '2026-05-15',
    author: 'AgenticAI Team',
    tags: ['tutorial', 'customer-support'],
    content: `
## Overview

In this tutorial, you'll build a customer support agent that:
- Answers common FAQs from a knowledge base
- Escalates complex issues to a human agent
- Sends a summary email after resolution

## Step 1: Describe your workflow

Go to the **Master Agent** page and type:

\`\`\`
Create a customer support agent with two sub-agents: 
1. A FAQ agent that answers common questions from a knowledge base
2. An escalation agent that routes complex issues to a human

The coordinator should try the FAQ agent first, 
and escalate if the question cannot be answered.
\`\`\`

## Step 2: Review the generated proposal

The Master Agent will generate a complete workflow JSON. You can see:
- The coordinator agent that routes requests
- The FAQ agent with RAG source configuration
- The escalation agent with HITL (human-in-the-loop) checkpoint

## Step 3: Validate and deploy

Click **"Validate & Compile"** to ensure the workflow is compatible with the downstream SDK compiler. Then click **"Deploy to Workspace"** to save it.

## Step 4: Run the workflow

Open the workflow in the canvas and click **"Run Workflow"**. Enter a test message like:

\`\`\`
What are your business hours?
\`\`\`

The FAQ agent will respond. Try a complex question and watch it escalate to the HITL checkpoint.

## Why this matters

Traditional workflow builders (like n8n) require manual configuration of every node and edge. With AgenticAI's Master Agent, you describe the *what* and it handles the *how* — generating a production-grade LangGraph DAG in seconds.
    `,
  },
  {
    slug: 'multi-agent-orchestration-patterns',
    title: 'Multi-Agent Orchestration: Patterns That Scale',
    description: 'Explore the three core orchestration patterns: model-driven, agent-driven, and consensus-based routing.',
    date: '2026-05-10',
    author: 'AgenticAI Team',
    tags: ['architecture', 'patterns'],
    content: `
## The Three Patterns

AgenticAI supports three orchestration modes, each suited to different use cases:

### 1. Model-Driven Routing

The LLM decides which agent to call next based on the conversation state. This is the default mode and works well for most workflows.

\`\`\`
Coordinator → LLM decides → FAQ Agent or Escalation Agent
\`\`\`

**Best for:** Customer support, content generation, research pipelines.

### 2. Agent-Driven Routing

Each agent decides its own next step. Agents have autonomy and can delegate tasks to sub-agents.

\`\`\`
Research Agent → decides to call Web Search Agent → 
  → decides to call Summarizer Agent → returns result
\`\`\`

**Best for:** Complex autonomous tasks, research, code generation.

### 3. Consensus-Based Routing

Multiple LLM instances run the same prompt in parallel and vote on the answer. This improves reliability for critical decisions.

\`\`\`
3× Instances → parallel execution → majority vote → final output
\`\`\`

**Best for:** Critical decisions, compliance checks, content moderation.

## When to Use Each

| Pattern | Reliability | Speed | Cost |
|---------|------------|-------|------|
| Model-Driven | Medium | Fast | Low |
| Agent-Driven | Medium | Medium | Medium |
| Consensus | High | Slow | High |

## Combining Patterns

The real power comes from combining patterns. For example:

1. Use **model-driven** routing for initial triage
2. Use **consensus** for the final decision
3. Use **agent-driven** for complex research sub-tasks

This is exactly what AgenticAI's DAG compiler enables — mix and match patterns within a single workflow.
    `,
  },
  {
    slug: 'bring-your-own-key-architecture',
    title: 'Why BYOK is the Future of AI Platforms',
    description: 'How bring-your-own-key pricing eliminates token markup and aligns platform incentives with users.',
    date: '2026-05-05',
    author: 'AgenticAI Team',
    tags: ['pricing', 'architecture'],
    content: `
## The Problem with Token Markup

Most AI platforms charge a markup on LLM tokens. You pay $0.02/1K tokens to OpenAI, and the platform charges you $0.05/1K — a 150% markup.

This creates misaligned incentives:
- The platform makes more money when you use more tokens
- There's no incentive to optimize prompt efficiency
- You can't use your existing OpenAI/Azure enterprise agreements

## The BYOK Alternative

AgenticAI's **Bring Your Own Key** model means:

\`\`\`
You provide: OPENAI_API_KEY=sk-...
You pay OpenAI: $0.01/1K tokens (your negotiated rate)
You pay AgenticAI: $49/month (platform fee, no token markup)
\`\`\`

## Benefits

### For Startups
- No surprise bills from token usage spikes
- Fixed monthly cost for the platform
- Use your free OpenAI credits

### For Enterprises
- Use existing enterprise agreements with OpenAI/Anthropic
- No vendor lock-in — switch LLM providers anytime
- Compliance: data never touches a third-party proxy

### For Developers
- Experiment freely without watching token costs
- Run the same workflow with different providers to compare
- No rate limiting based on your plan tier

## The Economics

| | Traditional Platform | AgenticAI (BYOK) |
|---|---|---|
| Platform fee | $49/mo | $49/mo |
| Token cost | $0.03/1K (includes markup) | $0.01/1K (direct to OpenAI) |
| 1M tokens/mo | $79 | $59 |
| 10M tokens/mo | $349 | $149 |

## Getting Started

Just set \`OPENAI_API_KEY\` or \`ANTHROPIC_API_KEY\` in your environment variables. AgenticAI uses them directly — no proxy, no markup.
    `,
  },
  {
    slug: 'n8n-alternative-for-ai-agents',
    title: 'AgenticAI vs n8n: Why AI Workflows Need More Than Drag-and-Drop',
    description: 'A technical comparison of AgenticAI and n8n for building AI agent workflows.',
    date: '2026-04-28',
    author: 'AgenticAI Team',
    tags: ['comparison', 'n8n'],
    content: `
## The Fundamental Difference

n8n is an excellent workflow automation tool for traditional integrations (send email, sync CRM, post to Slack). But AI agent workflows have fundamentally different requirements.

### 1. State Management

**n8n:** Each node is stateless. Data passes through once and is gone. No built-in conversation memory.

**AgenticAI:** Full stateful execution with LangGraph checkpoints. Every workflow maintains a scratchpad, message history, and persistent state across invocations.

### 2. Conditional Routing

**n8n:** Rules-based branching only (if/else on data values).

**AgenticAI:** Model-driven routing — the LLM decides which agent to call next based on context. Plus conditional edges using Python expressions.

### 3. Human-in-the-Loop

**n8n:** No native HITL support. Requires manual workarounds with webhooks.

**AgenticAI:** First-class HITL checkpoints. Pause execution at any node, approve/reject with state modifications, then resume.

### 4. Agent Loops

**n8n:** Linear pipelines only. No loops, no sub-agents, no recursion.

**AgenticAI:** Full DAG with cycles. Agents can call sub-agents, loop for refinement, and run consensus voting.

### 5. Observability

**n8n:** Execution logs only.

**AgenticAI:** Distributed tracing per step, token accounting, cost attribution, Prometheus metrics, Grafana dashboards.

## When to Use Which

| Use Case | AgenticAI | n8n |
|---|---|---|
| AI agent coordination | ✓ | ✗ |
| Multi-step LLM reasoning | ✓ | ✗ |
| CRM sync / email automation | ✗ | ✓ |
| API integration chaining | ✓ | ✓ |
| Human review workflows | ✓ | ✗ |
| Simple if/this/then/that | ✗ | ✓ |

## Bottom Line

n8n is great for traditional automation. AgenticAI is built for AI agent orchestration. They're complementary — use both if needed.
    `,
  },
]

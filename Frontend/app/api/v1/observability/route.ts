import { NextRequest, NextResponse } from "next/server";

interface TraceData {
  id: string;
  name: string;
  type: string;
  status: "success" | "error" | "running";
  duration: number;
  tokens: number;
  cost: number;
  timestamp: string;
  workspace: string;
  metadata?: Record<string, any>;
}

interface CostData {
  provider: string;
  model: string;
  requests: number;
  tokens: number;
  cost: number;
  change: number;
  period: string;
}

interface HealthData {
  component: string;
  type: "database" | "api" | "service" | "sandbox";
  status: "healthy" | "degraded" | "error";
  latency: number;
  lastCheck: string;
  details?: Record<string, any>;
}

// Mock data generators
function generateTraces(count: number, timeRange: string): TraceData[] {
  const types = ["RAG Pipeline", "Chat", "Tool", "Embedding", "LangGraph", "Agent"];
  const statuses: Array<"success" | "error" | "running"> = ["success", "success", "success", "error", "running"];
  const now = new Date();

  return Array.from({ length: count }, (_, i) => {
    const minutesAgo = Math.floor(Math.random() * getTimeRangeMinutes(timeRange));
    const timestamp = new Date(now.getTime() - minutesAgo * 60000);
    
    return {
      id: `tr_${Date.now()}_${i}`,
      name: `${types[Math.floor(Math.random() * types.length)].toLowerCase().replace(" ", "-")}-${i}`,
      type: types[Math.floor(Math.random() * types.length)],
      status: statuses[Math.floor(Math.random() * statuses.length)],
      duration: Math.floor(Math.random() * 5000) + 100,
      tokens: Math.floor(Math.random() * 5000),
      cost: Math.random() * 0.01,
      timestamp: timestamp.toISOString(),
      workspace: ["prod", "staging", "dev"][Math.floor(Math.random() * 3)],
    };
  });
}

function generateCosts(): CostData[] {
  return [
    { provider: "openai", model: "gpt-4o", requests: 12450, tokens: 4500000, cost: 124.50, change: 12.3, period: "24h" },
    { provider: "openai", model: "gpt-4o-mini", requests: 8920, tokens: 2100000, cost: 12.40, change: -5.2, period: "24h" },
    { provider: "anthropic", model: "claude-3.5-sonnet", requests: 5600, tokens: 3200000, cost: 89.60, change: 8.7, period: "24h" },
    { provider: "groq", model: "llama-3.1-70b", requests: 23400, tokens: 8900000, cost: 0, change: 0, period: "24h" },
    { provider: "google", model: "gemini-1.5-pro", requests: 1200, tokens: 890000, cost: 18.90, change: -2.1, period: "24h" },
  ];
}

function generateHealth(): HealthData[] {
  return [
    { component: "PostgreSQL (Checkpointer)", type: "database", status: "healthy", latency: 12, lastCheck: new Date().toISOString() },
    { component: "Qdrant (Vector Store)", type: "database", status: "healthy", latency: 45, lastCheck: new Date().toISOString() },
    { component: "Redis (Cache)", type: "database", status: "healthy", latency: 3, lastCheck: new Date().toISOString() },
    { component: "OpenAI API", type: "api", status: "degraded", latency: 1200, lastCheck: new Date().toISOString() },
    { component: "Anthropic API", type: "api", status: "healthy", latency: 890, lastCheck: new Date().toISOString() },
    { component: "LangGraph Server", type: "service", status: "healthy", latency: 56, lastCheck: new Date().toISOString() },
    { component: "E2B Sandbox", type: "sandbox", status: "error", latency: 0, lastCheck: new Date(Date.now() - 30000).toISOString() },
  ];
}

function getTimeRangeMinutes(range: string): number {
  const ranges: Record<string, number> = {
    "5m": 5,
    "15m": 15,
    "1h": 60,
    "24h": 1440,
    "7d": 10080,
    "30d": 43200,
  };
  return ranges[range] || 60;
}

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type") || "summary";
  const timeRange = searchParams.get("timeRange") || "1h";
  const workspace = searchParams.get("workspace");

  switch (type) {
    case "traces": {
      const traces = generateTraces(100, timeRange);
      const filtered = workspace ? traces.filter(t => t.workspace === workspace) : traces;
      return NextResponse.json({
        traces: filtered.slice(0, 50),
        total: filtered.length,
        timeRange,
      });
    }
    case "costs": {
      const costs = generateCosts();
      return NextResponse.json({ costs, timeRange });
    }
    case "health": {
      const health = generateHealth();
      return NextResponse.json({ health, timeRange });
    }
    case "summary": {
      const traces = generateTraces(100, timeRange);
      const costs = generateCosts();
      const health = generateHealth();

      const totalRequests = traces.length;
      const totalCost = costs.reduce((sum, c) => sum + c.cost, 0);
      const avgLatency = traces.reduce((sum, t) => sum + t.duration, 0) / traces.length;
      const errorRate = traces.filter(t => t.status === "error").length / traces.length * 100;

      return NextResponse.json({
        metrics: {
          totalRequests,
          totalCost: Math.round(totalCost * 100) / 100,
          avgLatency: Math.round(avgLatency),
          errorRate: Math.round(errorRate * 100) / 100,
        },
        costs: costs.slice(0, 3),
        health: health.slice(0, 3),
        timeRange,
      });
    }
    default:
      return NextResponse.json({ error: "Invalid type" }, { status: 400 });
  }
}
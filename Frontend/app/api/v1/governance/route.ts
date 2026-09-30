import { NextRequest, NextResponse } from "next/server";

interface GovernanceEvent {
  id: string;
  type: string;
  severity: "info" | "warning" | "critical";
  message: string;
  timestamp: string;
  workspace: string;
  user: string;
  metadata?: Record<string, any>;
}

interface CompliancePolicy {
  id: string;
  name: string;
  type: "RETENTION" | "COST_LIMIT" | "SECURITY" | "DATA_QUALITY" | "ACCESS_CONTROL";
  status: "active" | "inactive" | "draft";
  description: string;
  workspaces: string[];
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
  created_by: string;
}

interface ApiKey {
  id: string;
  name: string;
  provider: string;
  scopes: string[];
  key_prefix: string;
  last_used: string | null;
  expires_at: string;
  status: "active" | "expiring" | "expired" | "revoked";
  created_at: string;
  created_by: string;
}

const MOCK_EVENTS: GovernanceEvent[] = [
  { id: "evt_1", type: "COMPLIANCE_CHECK", severity: "info", message: "Data retention policy validated for workspace 'prod'", timestamp: "2024-01-15T10:25:00Z", workspace: "prod", user: "system" },
  { id: "evt_2", type: "ACCESS_GRANTED", severity: "info", message: "API key created for integration: tavily", timestamp: "2024-01-15T10:20:00Z", workspace: "prod", user: "admin@agenticai.dev" },
  { id: "evt_3", type: "RATE_LIMIT_EXCEEDED", severity: "warning", message: "Workspace 'dev' exceeded rate limit for openai (1000 req/min)", timestamp: "2024-01-15T10:15:00Z", workspace: "dev", user: "system" },
  { id: "evt_4", type: "SCHEMA_DRIFT_DETECTED", severity: "critical", message: "Vector store schema mismatch: dimension 1536 vs 3072 in collection 'documents'", timestamp: "2024-01-15T10:10:00Z", workspace: "staging", user: "system" },
  { id: "evt_5", type: "COST_THRESHOLD", severity: "warning", message: "Monthly cost threshold 80% reached ($450/$500)", timestamp: "2024-01-15T10:05:00Z", workspace: "prod", user: "system" },
];

const MOCK_POLICIES: CompliancePolicy[] = [
  {
    id: "pol_1",
    name: "Data Retention",
    type: "RETENTION",
    status: "active",
    description: "Delete user data after 90 days of inactivity",
    workspaces: ["prod", "staging"],
    config: { retention_days: 90, action: "delete" },
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    created_by: "admin@agenticai.dev",
  },
  {
    id: "pol_2",
    name: "Cost Governance",
    type: "COST_LIMIT",
    status: "active",
    description: "Alert at 80% budget, block at 100% ($500/month)",
    workspaces: ["prod"],
    config: { monthly_limit: 500, alert_threshold: 0.8, block_threshold: 1.0 },
    created_at: "2024-01-01T00:00:00Z",
    updated_at: "2024-01-01T00:00:00Z",
    created_by: "admin@agenticai.dev",
  },
];

const MOCK_API_KEYS: ApiKey[] = [
  { id: "key_1", name: "Production OpenAI", provider: "openai", scopes: ["chat", "embeddings", "tools"], key_prefix: "sk-prod-", last_used: "2024-01-15T10:30:00Z", expires_at: "2024-04-15T00:00:00Z", status: "active", created_at: "2024-01-01T00:00:00Z", created_by: "admin@agenticai.dev" },
  { id: "key_2", name: "Staging Anthropic", provider: "anthropic", scopes: ["chat", "tools"], key_prefix: "sk-staging-", last_used: "2024-01-15T09:30:00Z", expires_at: "2024-03-20T00:00:00Z", status: "active", created_at: "2024-01-10T00:00:00Z", created_by: "admin@agenticai.dev" },
  { id: "key_3", name: "Dev Tavily", provider: "tavily", scopes: ["search"], key_prefix: "tvly-dev-", last_used: "2024-01-12T15:00:00Z", expires_at: "2024-02-28T00:00:00Z", status: "expiring", created_at: "2024-01-15T00:00:00Z", created_by: "dev@agenticai.dev" },
];

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type") || "events";
  const workspace = searchParams.get("workspace");
  const severity = searchParams.get("severity");
  const limit = parseInt(searchParams.get("limit") || "50");

  switch (type) {
    case "events": {
      let events = [...MOCK_EVENTS];
      if (workspace) events = events.filter(e => e.workspace === workspace);
      if (severity) events = events.filter(e => e.severity === severity);
      return NextResponse.json({ events: events.slice(0, limit), total: events.length });
    }
    case "policies": {
      let policies = [...MOCK_POLICIES];
      if (workspace) policies = policies.filter(p => p.workspaces.includes(workspace));
      return NextResponse.json({ policies, total: policies.length });
    }
    case "api-keys": {
      let keys = [...MOCK_API_KEYS];
      if (workspace) keys = keys.filter(k => k.created_by.includes(workspace)); // simplified
      return NextResponse.json({ keys, total: keys.length });
    }
    case "summary": {
      const criticalEvents = MOCK_EVENTS.filter(e => e.severity === "critical").length;
      const warningEvents = MOCK_EVENTS.filter(e => e.severity === "warning").length;
      const activePolicies = MOCK_POLICIES.filter(p => p.status === "active").length;
      const activeKeys = MOCK_API_KEYS.filter(k => k.status === "active").length;
      const expiringKeys = MOCK_API_KEYS.filter(k => k.status === "expiring").length;

      return NextResponse.json({
        summary: {
          criticalEvents,
          warningEvents,
          activePolicies,
          activeKeys,
          expiringKeys,
        },
      });
    }
    default:
      return NextResponse.json({ error: "Invalid type" }, { status: 400 });
  }
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");

  try {
    const body = await request.json();

    switch (type) {
      case "policy": {
        const { name, type: policyType, description, workspaces, config } = body;
        
        if (!name || !policyType || !description || !workspaces || !config) {
          return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
        }

        const newPolicy: CompliancePolicy = {
          id: `pol_${Date.now()}`,
          name,
          type: policyType,
          status: "draft",
          description,
          workspaces,
          config,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          created_by: "current-user@agenticai.dev", // In production, get from auth
        };

        MOCK_POLICIES.push(newPolicy);
        return NextResponse.json(newPolicy, { status: 201 });
      }
      case "api-key": {
        const { name, provider, scopes, expires_in_days = 90 } = body;
        
        if (!name || !provider || !scopes) {
          return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
        }

        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + expires_in_days);

        const newKey: ApiKey = {
          id: `key_${Date.now()}`,
          name,
          provider,
          scopes,
          key_prefix: `${provider.slice(0, 4)}-${name.toLowerCase().replace(/\s+/g, "-")}-`,
          last_used: null,
          expires_at: expiresAt.toISOString(),
          status: "active",
          created_at: new Date().toISOString(),
          created_by: "current-user@agenticai.dev",
        };

        MOCK_API_KEYS.push(newKey);
        return NextResponse.json(newKey, { status: 201 });
      }
      default:
        return NextResponse.json({ error: "Invalid type" }, { status: 400 });
    }
  } catch (error) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}
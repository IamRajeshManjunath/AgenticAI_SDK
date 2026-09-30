import { NextRequest, NextResponse } from "next/server";

interface User {
  id: string;
  email: string;
  name: string;
  role: "admin" | "editor" | "viewer";
  workspaces: string[];
  created_at: string;
}

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  last_used: string | null;
  expires_at: string;
  status: "active" | "expiring" | "expired" | "revoked";
  created_at: string;
}

const MOCK_USERS: User[] = [
  { id: "user_1", email: "admin@agenticai.dev", name: "Admin User", role: "admin", workspaces: ["prod", "staging", "dev"], created_at: "2024-01-01T00:00:00Z" },
  { id: "user_2", email: "dev@agenticai.dev", name: "Dev User", role: "editor", workspaces: ["dev"], created_at: "2024-01-10T00:00:00Z" },
  { id: "user_3", email: "viewer@agenticai.dev", name: "Viewer User", role: "viewer", workspaces: ["prod"], created_at: "2024-01-15T00:00:00Z" },
];

const MOCK_API_KEYS: ApiKey[] = [
  { id: "key_1", name: "Production OpenAI", key_prefix: "sk-prod-", scopes: ["chat", "embeddings", "tools"], last_used: "2024-01-15T10:30:00Z", expires_at: "2024-04-15T00:00:00Z", status: "active", created_at: "2024-01-01T00:00:00Z" },
  { id: "key_2", name: "Staging Anthropic", key_prefix: "sk-staging-", scopes: ["chat", "tools"], last_used: "2024-01-15T09:30:00Z", expires_at: "2024-03-20T00:00:00Z", status: "active", created_at: "2024-01-10T00:00:00Z" },
];

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const type = searchParams.get("type");

  switch (type) {
    case "me": {
      // In production, get from auth session
      return NextResponse.json(MOCK_USERS[0]);
    }
    case "users": {
      return NextResponse.json({ users: MOCK_USERS, total: MOCK_USERS.length });
    }
    case "api-keys": {
      return NextResponse.json({ keys: MOCK_API_KEYS, total: MOCK_API_KEYS.length });
    }
    case "permissions": {
      const roles = {
        admin: [
          "system:admin",
          "workspace:read", "workspace:write", "workspace:delete",
          "integration:read", "integration:write", "integration:delete",
          "database:read", "database:write", "database:delete",
          "agent:read", "agent:write", "agent:delete", "agent:execute",
          "trace:read", "cost:read", "governance:read", "governance:write",
          "apikey:read", "apikey:write", "apikey:delete",
          "policy:read", "policy:write", "policy:delete",
        ],
        editor: [
          "workspace:read",
          "integration:read", "integration:write",
          "database:read", "database:write",
          "agent:read", "agent:write", "agent:execute",
          "trace:read", "cost:read",
          "apikey:read", "apikey:write",
        ],
        viewer: [
          "workspace:read",
          "integration:read",
          "database:read",
          "agent:read",
          "trace:read", "cost:read",
        ],
      };
      return NextResponse.json({ roles });
    }
    default:
      return NextResponse.json({ error: "Invalid type" }, { status: 400 });
  }
}

export async function POST(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const action = searchParams.get("action");

  try {
    const body = await request.json();

    switch (action) {
      case "create-api-key": {
        const { name, scopes, expires_in_days = 90 } = body;
        
        if (!name || !scopes) {
          return NextResponse.json({ error: "Missing required fields" }, { status: 400 });
        }

        const expiresAt = new Date();
        expiresAt.setDate(expiresAt.getDate() + expires_in_days);

        // Generate a mock key
        const keyValue = `sk-${Math.random().toString(36).substring(2, 22)}`;
        const keyPrefix = keyValue.substring(0, 12) + "...";

        const newKey: ApiKey = {
          id: `key_${Date.now()}`,
          name,
          key_prefix: keyPrefix,
          scopes,
          last_used: null,
          expires_at: expiresAt.toISOString(),
          status: "active",
          created_at: new Date().toISOString(),
        };

        MOCK_API_KEYS.push(newKey);

        return NextResponse.json({
          ...newKey,
          key: keyValue, // Only returned once!
        }, { status: 201 });
      }
      case "revoke-api-key": {
        const { keyId } = body;
        const index = MOCK_API_KEYS.findIndex(k => k.id === keyId);
        if (index === -1) {
          return NextResponse.json({ error: "API key not found" }, { status: 404 });
        }
        MOCK_API_KEYS[index].status = "revoked";
        return NextResponse.json({ success: true });
      }
      default:
        return NextResponse.json({ error: "Invalid action" }, { status: 400 });
    }
  } catch (error) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}
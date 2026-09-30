import { NextRequest, NextResponse } from "next/server";

const PURPOSES = [
  "vector_store",
  "checkpointer",
  "store",
  "analytics",
  "audit_log",
  "cache",
  "rate_limit",
] as const;

type Purpose = typeof PURPOSES[number];

interface DatabaseRoute {
  id: string;
  name: string;
  purpose: Purpose;
  provider: string;
  config: Record<string, any>;
  schema_contract: Record<string, any>;
  is_active: boolean;
  health_status: "healthy" | "degraded" | "error" | "unknown";
  last_health_check: string | null;
  schema_validation_status: "valid" | "invalid" | "pending" | "drift_detected";
  created_at: string;
  updated_at: string;
}

const MOCK_ROUTES: DatabaseRoute[] = [
  {
    id: "route_1",
    name: "primary-vector",
    purpose: "vector_store",
    provider: "qdrant",
    config: { url: "http://localhost:6333", collection: "documents" },
    schema_contract: {
      purpose: "vector_store",
      collections: {
        documents: {
          columns: {
            vector: { type: "vector", dimension: 1536 },
            content: { type: "text" },
            metadata: { type: "json" },
          },
        },
      },
    },
    is_active: true,
    health_status: "healthy",
    last_health_check: new Date().toISOString(),
    schema_validation_status: "valid",
    created_at: "2024-01-10T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
  {
    id: "route_2",
    name: "langgraph-checkpointer",
    purpose: "checkpointer",
    provider: "postgresql",
    config: { connectionString: "postgresql://user:pass@localhost:5432/langgraph" },
    schema_contract: {
      purpose: "checkpointer",
      tables: {
        checkpoints: "langgraph_standard",
        checkpoint_blobs: "langgraph_standard",
        checkpoint_writes: "langgraph_standard",
      },
    },
    is_active: true,
    health_status: "healthy",
    last_health_check: new Date().toISOString(),
    schema_validation_status: "valid",
    created_at: "2024-01-10T10:00:00Z",
    updated_at: "2024-01-15T10:00:00Z",
  },
];

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const purpose = searchParams.get("purpose");
  const active = searchParams.get("active");

  let routes = [...MOCK_ROUTES];

  if (purpose) {
    routes = routes.filter(r => r.purpose === purpose);
  }

  if (active === "true") {
    routes = routes.filter(r => r.is_active);
  }

  return NextResponse.json({
    routes,
    total: routes.length,
    purposes: PURPOSES,
  });
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { name, purpose, provider, config, schema_contract, is_active = true } = body;

    // Validate purpose
    if (!PURPOSES.includes(purpose)) {
      return NextResponse.json({ error: "Invalid purpose" }, { status: 400 });
    }

    // Check for existing active route with same purpose (enforce uniqueness)
    const existingActive = MOCK_ROUTES.find(r => r.purpose === purpose && r.is_active);
    if (existingActive && is_active) {
      return NextResponse.json(
        { error: `An active route for purpose '${purpose}' already exists: ${existingActive.name}` },
        { status: 409 }
      );
    }

    // Validate schema contract
    const validation = validateSchemaContract(purpose, schema_contract);
    if (!validation.valid) {
      return NextResponse.json({ error: "Schema validation failed", details: validation.errors }, { status: 400 });
    }

    // Test connection
    const connectionTest = await testConnection(purpose, provider, config);
    if (!connectionTest.success) {
      return NextResponse.json(
        { error: "Connection test failed", details: connectionTest.message },
        { status: 400 }
      );
    }

    // Create route
    const newRoute: DatabaseRoute = {
      id: `route_${Date.now()}`,
      name,
      purpose,
      provider,
      config,
      schema_contract,
      is_active,
      health_status: "healthy",
      last_health_check: new Date().toISOString(),
      schema_validation_status: "valid",
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    MOCK_ROUTES.push(newRoute);

    return NextResponse.json(newRoute, { status: 201 });
  } catch (error) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}

function validateSchemaContract(purpose: Purpose, schema: Record<string, any>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Basic validation - in production this would be much more comprehensive
  if (!schema.purpose || schema.purpose !== purpose) {
    errors.push(`Schema purpose must be '${purpose}'`);
  }

  switch (purpose) {
    case "vector_store":
      if (!schema.collections?.documents?.columns?.vector?.dimension) {
        errors.push("Vector store schema must define vector dimension");
      }
      break;
    case "checkpointer":
      if (!schema.tables?.checkpoints) {
        errors.push("Checkpointer schema must define checkpoints table");
      }
      break;
    case "store":
      if (!schema.tables?.store) {
        errors.push("Store schema must define store table");
      }
      break;
  }

  return { valid: errors.length === 0, errors };
}

async function testConnection(purpose: Purpose, provider: string, config: Record<string, any>): Promise<{ success: boolean; message: string }> {
  // In production, this would actually test the database connection
  // For now, simulate success for valid configs
  await new Promise(resolve => setTimeout(resolve, 500));
  
  // Simulate occasional failures for demo
  if (Math.random() < 0.1) {
    return { success: false, message: "Connection timeout" };
  }
  
  return { success: true, message: "Connection successful" };
}
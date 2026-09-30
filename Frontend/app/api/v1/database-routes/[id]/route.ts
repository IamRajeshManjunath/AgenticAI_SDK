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

function findRoute(id: string): DatabaseRoute | undefined {
  return MOCK_ROUTES.find(r => r.id === id);
}

function findRouteIndex(id: string): number {
  return MOCK_ROUTES.findIndex(r => r.id === id);
}

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const route = findRoute(id);

  if (!route) {
    return NextResponse.json({ error: "Database route not found" }, { status: 404 });
  }

  return NextResponse.json(route);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const index = findRouteIndex(id);

  if (index === -1) {
    return NextResponse.json({ error: "Database route not found" }, { status: 404 });
  }

  try {
    const body = await request.json();
    const { name, purpose, provider, config, schema_contract, is_active } = body;

    const existingRoute = MOCK_ROUTES[index];

    // If purpose is changing or being activated, check uniqueness
    if ((purpose && purpose !== existingRoute.purpose) || (is_active !== undefined && is_active !== existingRoute.is_active)) {
      const targetPurpose = purpose || existingRoute.purpose;
      const targetActive = is_active !== undefined ? is_active : existingRoute.is_active;

      if (targetActive) {
        const conflict = MOCK_ROUTES.find(r => r.id !== id && r.purpose === targetPurpose && r.is_active);
        if (conflict) {
          return NextResponse.json(
            { error: `An active route for purpose '${targetPurpose}' already exists: ${conflict.name}` },
            { status: 409 }
          );
        }
      }
    }

    // Validate schema if provided
    if (schema_contract) {
      const validation = validateSchemaContract(purpose || existingRoute.purpose, schema_contract);
      if (!validation.valid) {
        return NextResponse.json({ error: "Schema validation failed", details: validation.errors }, { status: 400 });
      }
    }

    // Test connection if config changed
    if (config || provider) {
      const testConfig = config || existingRoute.config;
      const testProvider = provider || existingRoute.provider;
      const connectionTest = await testConnection(purpose || existingRoute.purpose, testProvider, testConfig);
      if (!connectionTest.success) {
        return NextResponse.json(
          { error: "Connection test failed", details: connectionTest.message },
          { status: 400 }
        );
      }
    }

    // Update route
    MOCK_ROUTES[index] = {
      ...existingRoute,
      ...(name && { name }),
      ...(purpose && { purpose }),
      ...(provider && { provider }),
      ...(config && { config }),
      ...(schema_contract && { schema_contract }),
      ...(is_active !== undefined && { is_active }),
      updated_at: new Date().toISOString(),
    };

    return NextResponse.json(MOCK_ROUTES[index]);
  } catch (error) {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const index = findRouteIndex(id);

  if (index === -1) {
    return NextResponse.json({ error: "Database route not found" }, { status: 404 });
  }

  const route = MOCK_ROUTES[index];
  MOCK_ROUTES.splice(index, 1);

  return NextResponse.json({
    success: true,
    message: `Database route '${route.name}' deleted`,
    deleted_at: new Date().toISOString(),
  });
}

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;
  const { searchParams } = new URL(request.url);
  const action = searchParams.get("action");
  const route = findRoute(id);

  if (!route) {
    return NextResponse.json({ error: "Database route not found" }, { status: 404 });
  }

  if (action === "test") {
    const connectionTest = await testConnection(route.purpose, route.provider, route.config);
    
    // Update health status
    const index = findRouteIndex(id);
    if (index !== -1) {
      MOCK_ROUTES[index] = {
        ...route,
        health_status: connectionTest.success ? "healthy" : "error",
        last_health_check: new Date().toISOString(),
        schema_validation_status: connectionTest.success ? "valid" : "invalid",
      };
    }

    return NextResponse.json({
      success: connectionTest.success,
      message: connectionTest.message,
      tested_at: new Date().toISOString(),
    });
  }

  if (action === "validate-schema") {
    // In production, this would connect to the actual database and validate schema
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    const index = findRouteIndex(id);
    if (index !== -1) {
      // Simulate schema drift detection
      const hasDrift = Math.random() < 0.1;
      MOCK_ROUTES[index] = {
        ...route,
        schema_validation_status: hasDrift ? "drift_detected" : "valid",
        last_health_check: new Date().toISOString(),
      };
    }

    return NextResponse.json({
      valid: !hasDrift,
      message: hasDrift ? "Schema drift detected: vector dimension mismatch" : "Schema validation passed",
      validated_at: new Date().toISOString(),
    });
  }

  return NextResponse.json({ error: "Invalid action" }, { status: 400 });
}

function validateSchemaContract(purpose: Purpose, schema: Record<string, any>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

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
  await new Promise(resolve => setTimeout(resolve, 500));
  
  if (Math.random() < 0.1) {
    return { success: false, message: "Connection timeout" };
  }
  
  return { success: true, message: "Connection successful" };
}
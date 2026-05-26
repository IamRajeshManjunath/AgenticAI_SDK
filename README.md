# AgenticAI SDK — JSON-to-Workflow Engine

> **Production-grade, enterprise-ready framework** for compiling declarative JSON configurations into async, resilient, stateful multi-agent DAGs powered by **LangGraph** orchestration, **DeepAgent** cognitive loops, and **AWS IAM-style** permission-based authorization.

---

## Architecture

```
JWT / API Key (agk_ / wfk_)
      │
      ▼
AuthMiddleware
  ├── JWT (Bearer) → decode → set user_id + workspace_id
  ├── API Key (agk_) → hash lookup → set workspace_id
  ├── API Key (wfk_) → hash lookup → set workspace_id + workflow_scope
  └── require_permission(action) → evaluate_policies(principal, action, resource)
      │
      ▼
JSON Workflow Config
      │
      ▼
WorkflowSchema (Pydantic V2 Validation)
      │
      ▼
Orchestrator
  ├── LLMClientFactory   → ChatOpenAI / ChatAnthropic / ChatOllama
  ├── ToolRegistry       → MCP (JSON-RPC) / REST API / Custom Python (Dynamic) / Built-in
  ├── VectorDBClientFactory → Qdrant / Pinecone / PgVector
  ├── KnowledgeRetrieverEngine → async semantic retrieval (+ S3/Upload Ingestion)
  ├── DeepAgentFactory
  │     ├── model_driven  → ReAct-style autonomous tool use
  │     └── agent_driven  → explicit reasoning step sequences
  │
  ├── MiddlewarePipeline
  │     ├── BudgetGuardrails     → token/cost estimation & loop timeouts
  │     ├── PIIMaskingRouter     → PII/PHI detection & reversible masking
  │     ├── InjectionFirewall    → adversarial prompt detection
  │     ├── ContextCompression   → context window management
  │     ├── SchemaValidation     → Strict JSON Schema Input/Output enforcement (Audit Logged)
  │     └── RateLimiter          → Persistent execution throttling
  │
  ├── Enterprise Orchestration
  │     ├── Multi-DB Data Router → Map stages to Postgres/ClickHouse/SQLite
  │     ├── MCP Connector (v1.0) → Standard Model Context Protocol integration
  │     ├── Dynamic Tooling      → Register Python code strings at runtime
  │     ├── HITLBreakpoints      → state freeze/thaw + Slack/Teams webhooks
  │     └── AgentDelegation      → Hierarchical sub-agent management
  │
  └── Evaluation & Observability
        ├── Prometheus Metrics   → Latency/TPM/Error histogram exports
        ├── OpenTelemetry Spans  → Distributed tracing
        ├── Schema Audit Trail   → Immutable database log of all IO payloads
        └── Dashboard API        → /api/v1/observability/*
              │
              ▼
        LangGraph StateGraph (compiled DAG)
              │
              ▼
        FastAPI Gateway
          ├── POST /auth/*            (register, login, API keys, members)
          ├── POST /api/v1/workflow/run
          ├── POST /api/v1/workflow/hitl/approve
          ├── GET|POST|PATCH|DELETE /api/v1/workflow/workflows/*
          ├── GET|POST|PATCH|DELETE /api/v1/workflow/tools/*
          ├── GET|POST|PATCH|DELETE /api/v1/workflow/rag-sources/*
          ├── POST /api/v1/workflow/master/generate|compile
          ├── POST|GET|DELETE /api/v1/workflow/integrations/*
          ├── GET  /api/v1/observability/*
          ├── GET  /metrics (Prometheus)
          └── GET|POST /billing/*   (dormant — returns 503 without STRIPE_SECRET_KEY)
```

---

## Package Layout

```
agenticai_sdk/
├── __init__.py                      # version = "0.2.0"
├── client.py                        # AgenticAI(api_key) SDK — run(), run_by_id(), last_message()
├── exceptions.py                    # Domain exception hierarchy (24 exception types)
├── schemas/                         # Pydantic V2 models
│   ├── __init__.py                  # Exports all schema types
│   ├── llm.py                       # LLMConfig + LLMProvider enum
│   ├── tools.py                     # ToolConfig + ToolType (mcp, custom_python, rest, built_in)
│   ├── prompts.py                   # PromptTemplateConfig
│   ├── memory.py                    # MemoryConfig + ExecutionMemoryType + CachingStrategy
│   ├── hitl.py                      # HITLConfig + NotificationChannel enum
│   ├── rag.py                       # RAGConfig + VectorDBProvider + EmbeddingProvider + Universal connector fields
│   ├── topology.py                  # DeepAgentTopologyConfig + OrchestrationMode + FallbackStrategy
│   ├── middleware_config.py         # MiddlewareConfig + Budget/PII/Firewall/Compression/Consensus
│   ├── agent_node.py               # AgentNodeConfig (+ fallback_llms, consensus_config, middleware_config, input/output schema)
│   ├── edges.py                     # EdgeConfig (JSON-based conditional routing)
│   ├── workflow.py                  # WorkflowSchema (root + referential integrity validators)
│   └── integration.py              # IntegrationConfig + IntegrationType enum
├── state/
│   └── workflow_state.py            # WorkflowState TypedDict
├── auth/                            # Authentication & IAM Permission System
│   ├── __init__.py                  # Exports auth_router, get_current_user, require_permission, Permission
│   ├── dependencies.py              # JWT creation/verification, get_current_user, get_current_workspace
│   ├── permissions.py               # Permission enum (106 actions, 22 categories), evaluate_policies(), require_permission(), default policy documents
│   ├── router.py                    # *** BACKWARD-COMPAT STUB — routes moved to gateway/routes/auth.py ***
│   └── schemas.py                   # RegisterRequest, LoginRequest, TokenResponse, ApiKeyResponse, etc.
├── db/                              # Multi-DB Persistence Layer
│   ├── database.py                  # Dynamic DB Router (Postgres/SQLite/ClickHouse), _seed_default_policies()
│   ├── models.py                    # SQLAlchemy Models (16 tables: User, Workspace, WorkspaceMember, ApiKey, Plan, Policy, PolicyAttachment, Workflow, Tool, RAGSource, ActivityLog, WorkflowTrace, SchemaAuditTrail, BillingData, CronJob, IntegrationConnection)
│   └── dal.py                       # Data Access Layer (RelationalDAL, MongoDAL, DALFactory, DALEncryptor)
├── middleware/                       # Execution Safety & Audit Layer
│   ├── __init__.py
│   ├── base.py                      # MiddlewareBase, MiddlewarePipeline
│   ├── budget_guardrails.py         # Token/cost estimation, loop timeouts
│   ├── pii_masking.py               # PII/PHI detection, reversible masking vault
│   ├── prompt_injection_firewall.py # Pattern + semantic injection detection
│   ├── context_compression.py       # Truncation, summarization, schema dropping
│   ├── rate_limiter.py              # Throttling guardrail
│   ├── schema_validation.py         # JSON Schema Auditor (logs to SQL)
│   └── prometheus_metrics.py        # Prometheus metric counters/histograms
├── orchestration/                    # Enterprise Coordination
│   ├── __init__.py
│   ├── schema_mapper.py             # Fuzzy JSON normalization (exact/case-insensitive/fuzzy/LLM)
│   ├── hitl_breakpoints.py          # State freeze/thaw + Slack/Teams webhook dispatch
│   ├── fallback_router.py           # LLM failover with state preservation
│   └── consensus_broker.py          # Multi-instance agreement with similarity scoring
├── deep_agent/
│   ├── __init__.py
│   └── factory.py                   # DeepAgentFactory (model_driven/agent_driven loops)
├── rag/
│   ├── __init__.py
│   ├── vector_db_factory.py         # VectorDBClientFactory (Qdrant, Pinecone, PgVector, ChromaDB, FAISS, Universal, adapter registry)
│   ├── retriever_engine.py          # KnowledgeRetrieverEngine (async retrieval, S3/upload ingestion)
│   ├── context_injector.py          # ContextInjector (document formatting for prompt injection)
│   └── universal_connector.py       # UniversalRAGConnector — generic HTTP connector for any RAG DB
├── runtime/
│   ├── __init__.py
│   ├── orchestrator.py              # Macro-execution engine (compiles WorkflowSchema → LangGraph StateGraph)
│   ├── llm_factory.py               # LLMClientFactory (OpenAI, Anthropic, Ollama)
│   ├── tool_registry.py             # ToolRegistry (MCP, REST API, custom Python, built-in, integration tools)
│   ├── integration_registry.py      # IntegrationRegistry (Slack, Teams, Outlook, WhatsApp)
│   ├── skills_parser.py             # SKILLS.md parser for dynamic config mutation
│   ├── agent_context_loader.py      # Per-agent agent.md / skill.md context loader
│   ├── cron_daemon.py               # CRON scheduling daemon with lease locks
│   └── context_engine.py            # Prompt rendering, system message building, memory window
├── evaluation/
│   ├── __init__.py
│   ├── trace_collector.py           # OTel Bridge + SQL Span Trees
│   ├── metrics.py                   # Latency/token/cost aggregation
│   ├── evaluators.py                # ResponseQualityEvaluator + WorkflowEvaluator
│   └── dashboard.py                 # *** BACKWARD-COMPAT STUB — routes moved to gateway/routes/observability.py ***
├── billing/
│   ├── __init__.py                  # Exports billing_router (via compat stub), PlanEnforcer
│   ├── enforcer.py                  # PlanEnforcer middleware
│   ├── schemas.py                   # Pydantic models for billing
│   └── router.py                    # *** BACKWARD-COMPAT STUB — routes moved to gateway/routes/billing.py ***
├── gateway/
│   ├── __init__.py
│   ├── app.py                       # App factory + structlog + CORS + exception handlers, iterates route_modules
│   ├── auth_middleware.py           # JWT + API key dual auth middleware
│   ├── middleware.py                # ExecutionTrackingMiddleware (request ID, timing)
│   ├── routes/                      # Consolidated route modules
│   │   ├── __init__.py              # Exports route_modules list for app factory
│   │   ├── auth.py                  # Auth routes (register, login, API keys, workspace members)
│   │   ├── workflows.py             # Workflow execution, HITL, SaaS CRUD, master agent
│   │   ├── integrations.py          # Third-party integration management
│   │   ├── observability.py         # Traces, metrics, evaluations, health
│   │   └── billing.py               # Billing routes (dormant — all stripe-dependent endpoints return 503)
│   ├── integration_routes.py        # *** BACKWARD-COMPAT STUB — routes moved to routes/integrations.py ***
│   └── ...routes.py [DELETED]       # Was monolithic — content split into routes/ package
├── master_agent/                     # Upstream natural-language intake (renamed from Master_agent/)
│   ├── __init__.py
│   ├── agent.py                     # StructuredMasterAgent — LLM-based schema synthesis
│   ├── rag.py                       # MasterAgentRAG — keyword-based doc retrieval
│   └── context_loader.py            # Agent context file scanner (agent.md / skill.md)
```

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -e ".[dev]"
```

### 2. Set Environment Variables

```bash
# LLM providers (set whichever you use)
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."

# Vector DB (optional — mock client used if not set)
export QDRANT_API_KEY="your-qdrant-key"

# HITL Webhooks (optional)
export HITL_SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export HITL_TEAMS_WEBHOOK_URL="https://outlook.office.com/webhook/..."
```

### 3. Start the Gateway

```bash
python main.py
# or
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Execute a Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflow/run \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "enterprise-hierarchy-v3",
    "name": "Hierarchical Enterprise Workflow (v0.2)",
    "description": "A complex manager-worker workflow. A '\''Coordinator'\'' agent delegates specific sub-tasks to '\''Researcher'\'' and '\''Writer'\'' specialists using hierarchical tool calls. Includes safety guardrails, fallbacks, and consensus.",
    "agents": [
      {
        "agent_id": "coordinator",
        "role": "Strategic Project Coordinator responsible for high-level planning and delegation",
        "prompt_template": {
          "template_id": "coordinator_prompt",
          "template_string": "You are the central coordinator for this request: {topic}. \n\nYour task is to:\n1. Delegate deep research to the '\''researcher'\'' specialist.\n2. Once research is received, delegate report writing to the '\''writer'\'' specialist.\n3. Review the final report and ensure it meets executive standards.",
          "input_variables": ["topic"]
        },
        "llm": {
          "provider": "openai",
          "model_name": "gpt-4o",
          "temperature": 0.1,
          "api_key_env_var": "OPENAI_API_KEY"
        },
        "sub_agents": ["researcher", "writer"],
        "topology": {
          "orchestration_mode": "model_driven"
        }
      },
      {
        "agent_id": "researcher",
        ...
      }
    ],
    "input_message": "Research the impact of LLMs on software engineering productivity",
    "thread_id": "session-001"
  }'
```

### 5. Resume a HITL-Interrupted Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflow/hitl/approve \
  -H "Content-Type: application/json" \
  -d '{
    "thread_id": "session-001",
    "approved": true,
    "workflow": <contents of example_workflow.json>
  }'
```

---

## New Enterprise Features (v0.3)

### 📊 Multi-DB Performance Routing
Configure different databases for different parts of your system. Use PostgreSQL for workspaces, ClickHouse for massive trace logs, and SQLite for local caching.

```python
init_db(
    core_db_url="postgresql://user:pass@main-db/prod",
    routing_map={
        "workflow_traces": "clickhouse://user:pass@analytics-cluster",
        "schema_audit_trails": "postgresql://user:pass@audit-db/security"
    }
)
```

### 🛡️ Schema-Level Audit Trail
Every agent execution now records the *exact* data that entered and exited, validated against your custom JSON Schemas.
- **Micro-Observability**: See exactly what "hallucinations" caused a schema violation.
- **Compliance**: Immutable history of all LLM inputs/outputs.

### 🔌 Real MCP Integration (JSON-RPC)
Fully compliant with the Model Context Protocol. Connect your agents to any MCP server via standard JSON-RPC over HTTP/SSE.

```json
{
  "tool_id": "weather_mcp",
  "type": "mcp",
  "config": {
    "connection_string": "http://mcp-server:8080",
    "arguments": { "mcp_tool_name": "get_weather" }
  }
}
```

### 📈 Metrics & OpenTelemetry
Integrated with the industry-standard monitoring stack.
- **Prometheus**: Real-time TPM (Tokens Per Minute), RPM, and Latency Histograms.
- **Grafana**: Ready-to-use dashboards via the `/metrics` endpoint.
- **OpenTelemetry**: Distributed spans for every node execution.

---

## Middleware & Safety (v0.3)

### Semantic Budget & Cost Guardrails
Pre-calculates token/dollar estimates before API calls. Enforces per-call token limits, cumulative workflow cost caps, loop iteration guards, and wall-clock timeouts.

### Strict JSON Schema Enforcement
Define `input_schema` and `output_schema` directly in your agent configuration. The middleware blocks invalid data before it hits your LLM and audits the results after.

```json
{
  "agent_id": "data_processor",
  "input_schema": {
    "type": "object",
    "properties": { "id": { "type": "integer" } }
  }
}
```

### Persistent Rate Limiter
Protect your LLM budget and API tiers with a built-in rate limiter middleware.

---

## Observability Suite (v0.3)

| Endpoint | Description |
|----------|-------------|
| `GET /metrics` | Prometheus Metrics Scraper (Latency, Tokens, Errors) |
| `GET /api/v1/observability/traces` | Full SQL Trace detail from the DB |
| `GET /api/v1/observability/health` | Extended health check including DB latency |

### Quality Evaluators
- **Relevance**: Query-response term overlap with TF-IDF weighting
- **Coherence**: Vocabulary richness, sentence structure, structural markers
- **Groundedness**: Response alignment with retrieved RAG source documents

### Dashboard API
| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/observability/traces` | List recent traces |
| `GET /api/v1/observability/traces/{id}` | Full trace detail |
| `GET /api/v1/observability/metrics` | Metrics summary (JSON) |
| `GET /api/v1/observability/metrics/prometheus` | Prometheus export |
| `GET /api/v1/observability/evaluations/{wf_id}` | Quality evaluations |
| `GET /api/v1/observability/health` | Extended health check |

---

## Master Agent (Upstream Intake)

The `master_agent/` module acts as the primary system ingress — it translates natural-language user prompts into valid `WorkflowSchema` JSON without requiring the user to understand the schema format.

```
User Prompt ("Build me a research + writing pipeline...")
       │
       ▼
  MasterAgentRAG (keyword retrieval from reference docs)
       │
       ▼
  StructuredMasterAgent
     ├── OpenAI with_structured_output(WorkflowSchema)  ← LLM-driven synthesis
     └── Rule-based deterministic fallback              ← keyword-triggered templates
       │
       ▼
  Valid WorkflowSchema JSON
```

### StructuredMasterAgent
- **`generate_proposal(user_prompt)`** — Main entry point. Returns a complete `WorkflowSchema`-compatible dict.
- Uses `MasterAgentRAG` to retrieve context from `master_schema_reference.json`, `README.md`, and `docs/implementation_plan.md`.
- Attempts structured LLM output first; falls back to a deterministic rule-based engine that creates single/multi-agent workflows based on keywords (search, python, weather, write, report).

### MasterAgentRAG
- Chunks reference documents by markdown headers and JSON boundaries.
- Scores chunks by keyword overlap with boost for title matches.
- Returns top-k relevant documentation snippets to guide the LLM synthesis.

---

## Frontend Application

A Next.js application (`frontend/` — flattened from the former `Frontend/frontend/` nesting) provides a visual interface for building, monitoring, and managing workflows.

### Tech Stack
- **Framework**: Next.js 16 (App Router), TypeScript 5.7
- **Styling**: Tailwind CSS v4 + shadcn/ui (~45 components)
- **State**: Zustand 5 + SWR for API data fetching
- **Animations**: Framer Motion
- **Graph Editor**: ReactFlow v11
- **Client SDK**: TypeScript `AgenticAI` class (`lib/agenticai-client.ts`)

### Pages
| Route | Description |
|-------|-------------|
| `/` | Landing page (marketing, feature showcases, templates preview) |
| `/agent` | Master Agent chatbot — natural-language prompt → workflow proposal → compile → deploy |
| `/workflows/*` | Visual workflow canvas — drag-and-drop agent graph editor |
| `/activity` | Execution activity log and history |
| `/billing` | Usage metrics and billing data |
| `/rag` | RAG source configuration and document management |
| `/settings` | Global settings and integration configuration |
| `/tools` | Tool registry management |
| `/observability/*` | Trace detail and metrics dashboards |
| `/templates/*` | Pre-built workflow template gallery |
| `/blog/*` | Technical blog posts |
| `/login`, `/register` | Authentication pages |

### Key Components
- **`workflow-proposal-canvas.tsx`** — Drag-and-drop ReactFlow canvas with mini-map, controls, edge condition panel
- **`workflow-builder.tsx`** — Visual / JSON dual-mode editor with MetadataSection, ToolsSection, RagSection
- **`workflow/agent-config-sidebar.tsx`** — Full per-agent configuration (LLM, tools, RAG, sub-agents, consensus, middleware)
- **`workflow/agent-node.tsx`** — Visual node component on the canvas
- **`workflow/registry-drawer.tsx`** — Drawer for browsing tools, RAG sources, and templates
- **`global-sidebar.tsx`** — Main navigation sidebar with user avatar/logout
- **`dashboard-layout.tsx`** — Authenticated layout wrapper
- **`error-boundary.tsx`** — React error boundary wrapping root layout + per-page
- **`ui/`** — 45+ reusable shadcn/ui components (accordion, dialog, chart, form, table, slider, etc.)

### Data Layer & Auth
- `lib/api.ts` — HTTP client for the FastAPI gateway
- `lib/auth-store.ts` — Zustand persist store (token, user, workspace)
- `lib/auth-provider.tsx` — Route guard component (redirects unauthenticated users to /login)
- `lib/rbac.ts` — Role-based access checks (admin / editor / viewer)
- `lib/agenticai-client.ts` — TypeScript `AgenticAI(api_key)` SDK client
- `lib/store.ts` — Zustand state management
- `lib/db/` — Multi-adapter DB layer (PostgreSQL adapter + mock adapter)
- `lib/types.ts` — Shared TypeScript type definitions
- `lib/utils.ts` — Utility functions (cn(), etc.)

---

## Authentication & IAM Permission System

### Dual Auth Middleware

Every request passes through `AuthMiddleware` which supports two authentication methods:

| Method | Credential | Principal | Scope |
|--------|-----------|-----------|-------|
| **JWT** | `Authorization: Bearer <token>` | `user_id` | Full workspace access based on role |
| **API Key (workspace)** | `X-API-Key: agk_<hex>` | workspace-level | Workspace-wide (no user context) |
| **API Key (workflow)** | `X-API-Key: wfk_<hex>` | workspace-level | Single workflow only (key_scope = workflow_id) |

### AWS IAM-Style Policy Engine

The system uses a full AWS IAM-style authorization model (`auth/permissions.py`):

```python
from agenticai_sdk.auth import require_permission, Permission, evaluate_policies

# FastAPI dependency — gates a route
@router.post("/workflows")
async def create_workflow(_: User = Depends(require_permission("workflow:create"))):
    ...

# Programmatic evaluation
result = evaluate_policies(principal_id="user:abc", policies=policy_docs,
                           action="workflow:run", resource="wf:xyz")
# → {"effect": "allow", "matched_statements": [...]}
```

**Decision logic** (AWS IAM semantics):
1. If any statement matches with `Effect: Deny` → **Deny**
2. If any statement matches with `Effect: Allow` → **Allow**
3. Otherwise → **Deny** (implicit)

### Permission Enum (106 Actions, 22 Categories)

| Category | Example Actions | Description |
|----------|----------------|-------------|
| `workflow:*` | create, read, update, delete, run | Workflow lifecycle |
| `apikey:*` | create, read, delete | API key management |
| `member:*` | list, invite, remove, update-role | Team management |
| `tool:*` | create, read, update, delete | Tool registry |
| `rag:*` | create, read, update, delete | RAG sources |
| `approval:*` | approve | HITL approvals |
| `integration:*` | connect, disconnect, read | Third-party integrations |
| `observability:*` | read | Traces & metrics |
| `audit:*` | read | Activity logs |
| `db:*` | read, connect, reset | Database management |
| `billing:*` | read, manage | Billing |
| `workspace:*` | update, delete | Workspace settings |
| `cron:*` | create, read, update, delete, run | Cron jobs |
| `secret:*` | read, write, delete | Secrets |
| `settings:*` | read, update | Global settings |
| `template:*` | create, read, update, delete | Templates |
| `notification:*` | send, configure | Notifications |
| `invite:*` | create, revoke | Invite links |
| `tag:*` | create, read, update, delete | Tags |
| `invitelink:*` | create, revoke | Legacy invite links |
| `admin:*` | superuser | System administration |

### Default Role Policies

Three system policies are seeded in `init_db()` via `_seed_default_policies()`:

| Role | Effect | Scope | Example Denied Actions |
|------|--------|-------|----------------------|
| **admin** | Allow `*` | Everything | — |
| **editor** | Allow `*`, Deny (16 sensitive) | workspace:delete, billing:*, admin:*, cron:* (6), db:reset, secret:*, member:remove, member:update-role, invite:*, invitelink:* |
| **viewer** | Allow (18 read-only) | workflow:read, tool:read, rag:read, observability:read, audit:read, member:list, apikey:read, workspace:read, integration:read, cron:read, secret:read, settings:read, template:read, tag:read, billing:read, notification:read |

### Policy Documents

Policies are JSON documents stored in the `policies` table:

```json
{
  "Version": "2026-05",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["workflow:*", "tool:*", "rag:*"],
      "Resource": ["*"]
    },
    {
      "Effect": "Deny",
      "Action": ["admin:superuser", "workspace:delete"],
      "Resource": ["*"]
    }
  ]
}
```

Actions and resources support wildcard glob patterns (`workflow:*`, `wf:abc-*`).

### Data Models

| Table | Key Fields | Purpose |
|-------|------------|---------|
| `policies` | id, name, description, policy_document (JSON), is_system | IAM policy definition |
| `policy_attachments` | id, policy_id (FK), principal_type (user/role), principal_id | Binds policies to principals |

### Backward-Compatible Route Stubs

The following old module locations still resolve through compat stubs:

| Old Path | Re-exports From |
|----------|----------------|
| `agenticai_sdk.auth.router` | `agenticai_sdk.gateway.routes.auth` |
| `agenticai_sdk.evaluation.dashboard` | `agenticai_sdk.gateway.routes.observability` |
| `agenticai_sdk.gateway.integration_routes` | `agenticai_sdk.gateway.routes.integrations` |
| `agenticai_sdk.billing.router` | `agenticai_sdk.gateway.routes.billing` |

---

## Core Concepts

### WorkflowSchema
The single source of truth. Author a JSON file that defines:
- **Global tools** (MCP, REST API, custom Python, built-in)
- **RAG sources** (Qdrant, Pinecone, PgVector)
- **Agent nodes** with LLM configs, prompts, topology, and memory
- **Edges** with optional condition expressions
- **HITL** interruption points
- **Middleware config** (budget, PII, firewall, compression)
- **Fallback LLMs** and **Consensus config** per agent

### WorkflowState
Every node receives and returns a `WorkflowState` TypedDict:
```python
{
    "messages":             [...],   # Full message history (add_messages accumulator)
    "scratchpad":           {...},   # Cross-agent key-value store
    "retrieved_context":    [...],   # RAG documents pulled across steps
    "inner_thoughts":       [...],   # Chain-of-thought reasoning traces
    "next_step":            "...",   # Routing signal for conditional edges
    "middleware_metadata":  {...},   # Budget/PII/firewall state across nodes
    "trace_id":             "...",   # Active observability trace ID
}
```

### OrchestrationMode
- **`model_driven`** — LLM autonomously decides tool usage (ReAct loop)
- **`agent_driven`** — Follows explicit `reasoning_steps` sequences for structured CoT

### Conditional Edge Routing
Edge conditions are Python expressions evaluated against `state`:
```json
{
  "edges": [
    {
      "source": "coordinator",
      "target": "__end__",
      "condition": null
    }
  ],

  "hitl": {
    "interruption_points": ["coordinator"],
    "approval_timeout": 1800,
    "notification_channel": "slack"
  },

  "entry_point": "coordinator"
}
```

### HITL (Human-in-the-Loop)
List agent IDs in `hitl.interruption_points`. The graph pauses at those nodes.
Resume via `POST /api/v1/workflow/hitl/approve` with `{ "approved": true }`.

---

# 🛠 Configuration & Orchestration Guide

This guide explains how to configure your workflow JSON to leverage the SDK's advanced "switches" for different enterprise scenarios.

## 1. Orchestration Modes: The "Cognitive Switch"
You can control how an agent thinks by toggling `topology.orchestration_mode`.

### 🧠 Model-Driven (ReAct)
**When to use:** For complex, non-linear tasks where the agent needs to "think on its feet."
- **Behavior**: The agent receives tools and a goal. It reasons, calls tools, and loops until it finds the answer.
- **JSON Switch**:
  ```json
  "topology": { "orchestration_mode": "model_driven" }
  ```

### 📋 Agent-Driven (Step-Sequence)
**When to use:** For strict business processes or when you want the agent to follow a high-fidelity reasoning path.
- **Behavior**: The agent is forced to go through specific phases (e.g., *Analyze* → *Plan* → *Execute*).
- **JSON Switch**:
  ```json
  "topology": {
    "orchestration_mode": "agent_driven",
    "reasoning_steps": ["verify_source", "extract_data", "summarize"]
  }
  ```

---

## 2. Hierarchical Delegation (Sub-Agents)
To create a "Manager" agent, use the `sub_agents` field.

- **The Logic**: The parent agent sees every ID in `sub_agents` as a tool it can call (e.g., `delegate_to_researcher`).
- **Scenario**: Use this when a task is too large for one agent. A *Manager* agent can break down a project and delegate pieces to *Specialists*.
- **JSON Setup**:
  ```json
  {
    "agent_id": "manager",
    "sub_agents": ["research_specialist", "coding_specialist"]
  }
  ```

---

## 3. Resilience & Quality Switches

### 🛡 Fallback Routing (The "No-Fail" Switch)
If your primary model (e.g., GPT-4) hits a rate limit or goes down, the SDK can instantly swap to a backup without crashing.
- **JSON Setup**:
  ```json
  "fallback_llms": [
    { "provider": "anthropic", "model_name": "claude-3-haiku-..." }
  ]
  ```

### 🤝 Consensus (The "Truth" Switch)
For high-stakes decisions, spin up multiple instances of the same agent and only proceed if they agree.
- **JSON Setup**:
  ```json
  "consensus_config": {
    "enabled": true,
    "instances": 3,
    "threshold": 0.7
  }
  ```

---

## 4. Safety & Guardrails (Middleware)
Every agent has a `middleware_config` that is **on by default** but can be customized.

- **Budget**: Kill the execution if it spends more than $X or takes more than Y iterations.
- **PII**: Automatically redact emails, SSNs, and names before they hit the LLM.
- **Firewall**: Stop "Prompt Injection" attacks before they reach your logic.

```json
"middleware_config": {
  "budget": { "max_cost_per_workflow": 0.50 },
  "pii": { "enabled": true, "masking_level": "hash" }
}
```

---

## 🚀 Summary Scenario: A Production Setup
| If you want... | Use these settings... |
| :--- | :--- |
| **Highest Accuracy** | `consensus_config` + `model_driven` |
| **Lowest Latency** | `agent_driven` (small steps) + `gpt-4o-mini` |
| **Data Privacy** | `pii: { "enabled": true }` |
| **Complex Projects** | `sub_agents` (Manager/Worker pattern) |

---

## API Reference

### System Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root info with endpoint listing |
| `GET` | `/health` | Simple health check |

### Auth Endpoints (prefix `/auth`)
| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| `POST` | `/auth/register` | — | Register new user + create workspace |
| `POST` | `/auth/login` | — | Login, returns JWT |
| `GET` | `/auth/me` | — | Current user profile |
| `PUT` | `/auth/me/password` | — | Change password |
| `POST` | `/auth/api-keys` | `apikey:create` | Create workspace API key (`agk_`) |
| `GET` | `/auth/api-keys` | `apikey:read` | List all API keys for workspace |
| `POST` | `/auth/api-keys/workflow/{id}` | `apikey:create` | Create/regenerate workflow-scoped key (`wfk_`) |
| `DELETE` | `/auth/api-keys/{id}` | `apikey:delete` | Delete an API key |
| `GET` | `/auth/workspace/members` | `member:list` | List workspace members |
| `POST` | `/auth/workspace/invite` | `member:invite` | Invite a user to workspace |
| `PUT` | `/auth/workspace/members/{id}/role` | `member:update-role` | Change member role |
| `DELETE` | `/auth/workspace/members/{id}` | `member:remove` | Remove member from workspace |

### Workflow Execution
| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| `POST` | `/api/v1/workflow/run` | `workflow:run` | Execute a workflow (full schema or key-scoped) |
| `POST` | `/api/v1/workflow/run/{workflow_id}` | `workflow:run` | Execute a deployed workflow by ID |
| `POST` | `/api/v1/workflow/hitl/approve` | `approval:approve` | Resume or reject an interrupted HITL workflow |

### Master Agent
| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| `POST` | `/api/v1/workflow/master/generate` | `workflow:create` | Generate WorkflowSchema proposal from natural-language prompt |
| `POST` | `/api/v1/workflow/master/compile` | `workflow:create` | Validate, compile, and persist a WorkflowSchema |

### SaaS CRUD
| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| `GET` | `/api/v1/workflow/workflows` | `workflow:read` | List all persisted workflows |
| `POST` | `/api/v1/workflow/workflows` | `workflow:create` | Create a new workflow |
| `GET` | `/api/v1/workflow/workflows/{id}` | `workflow:read` | Get a workflow by ID |
| `PATCH` | `/api/v1/workflow/workflows/{id}` | `workflow:update` | Update a workflow |
| `DELETE` | `/api/v1/workflow/workflows/{id}` | `workflow:delete` | Delete a workflow |
| `DELETE` | `/api/v1/workflow/workspaces/{id}` | `workspace:delete` | Delete a workspace (cascades) |
| `GET` | `/api/v1/workflow/tools` | `tool:read` | List all registered tools |
| `POST` | `/api/v1/workflow/tools` | `tool:create` | Register a new tool |
| `PATCH` | `/api/v1/workflow/tools/{id}` | `tool:update` | Update a tool |
| `DELETE` | `/api/v1/workflow/tools/{id}` | `tool:delete` | Delete a tool |
| `GET` | `/api/v1/workflow/rag-sources` | `rag:read` | List RAG sources |
| `POST` | `/api/v1/workflow/rag-sources` | `rag:create` | Create a RAG source |
| `PATCH` | `/api/v1/workflow/rag-sources/{id}` | `rag:update` | Update a RAG source |
| `DELETE` | `/api/v1/workflow/rag-sources/{id}` | `rag:delete` | Delete a RAG source |
| `GET` | `/api/v1/workflow/activity` | `audit:read` | Recent activity log (last 50 entries) |
| `GET` | `/api/v1/workflow/metrics` | `observability:read` | Prometheus metrics export |

### Database Management
| Method | Endpoint | Permission | Description |
|--------|----------|------------|-------------|
| `GET` | `/api/v1/workflow/db/status` | `db:read` | Database status + collection counts |
| `POST` | `/api/v1/workflow/db/connect` | `db:connect` | Connect to a new database (persisted) |
| `GET` | `/api/v1/workflow/db/config` | `db:read` | View current persisted DB config |
| `POST` | `/api/v1/workflow/db/reset` | `db:reset` | Reset to default SQLite |

### Integration Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflow/integrations/connect` | Register a third-party integration |
| `GET` | `/api/v1/workflow/integrations` | List active connections |
| `DELETE` | `/api/v1/workflow/integrations/{type}` | Disconnect an integration |
| `POST` | `/api/v1/workflow/integrations/{type}/test` | Send test message |

### Observability Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/observability/traces` | List recent traces |
| `GET` | `/api/v1/observability/traces/{id}` | Full trace detail |
| `GET` | `/api/v1/observability/metrics` | Metrics summary (JSON) |
| `GET` | `/api/v1/observability/metrics/prometheus` | Prometheus format export |
| `GET` | `/api/v1/observability/evaluations/{workflow_id}` | Quality evaluations |
| `GET` | `/api/v1/observability/health` | Extended health check |

### Billing Endpoints (dormant — prefix `/billing`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/billing/plans` | List available plans (DB query) |
| `POST` | `/billing/create-checkout-session` | **503 — requires STRIPE_SECRET_KEY** |
| `GET` | `/billing/portal` | **503 — requires STRIPE_SECRET_KEY** |
| `GET` | `/billing/usage` | Usage metrics for current period |
| `POST` | `/billing/webhook` | Logs and returns `{"received": true}` (no-op without Stripe) |

### Key-Scoped Workflow Run (Header: `X-API-Key: wfk_<hex>`)
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflow/run` | Auto-resolves to the workflow the key was issued for; passes `input_message` directly |

---

## Domain Exceptions

| Exception | Trigger |
|-----------|---------|
| `SchemaValidationError` | Pydantic model structural or semantic validation failure |
| `PromptTemplateError` | Prompt template variables mismatch declared `input_variables` |
| `WorkflowCompilationError` | Graph compilation failure |
| `ToolResolutionError` | Unknown `tool_id` reference |
| `ToolExecutionError` | Tool invocation runtime failure |
| `LLMProviderError` | LLM client instantiation failure |
| `RAGFetchException` | Vector DB retrieval failure |
| `VectorDBConnectionError` | Vector database client connection failure |
| `EmbeddingError` | Embedding provider encoding failure |
| `DeepAgentExecutionError` | Inner cognitive loop fatal error |
| `DeepAgentFallbackExhausted` | All fallback strategies exhausted |
| `HITLTimeoutError` | Human approval timeout exceeded |
| `HITLRejectError` | Human reviewer explicitly rejected a step |
| `HITLDispatchError` | Webhook notification dispatch failure |
| `GraphRoutingError` | Conditional edge evaluation failure |
| `BudgetExceededError` | Token or cost budget threshold breached |
| `LoopTimeoutError` | Agent loop exceeded time/iteration limit |
| `PIIMaskingError` | PII vault encryption/masking failure |
| `PromptInjectionDetectedError` | Adversarial prompt detected |
| `ContextCompressionError` | Context compression operation failure |
| `SchemaMapperError` | JSON schema normalization failure |
| `ConsensusNotReachedError` | Agent consensus threshold not met |
| `FallbackExhaustedError` | All fallback LLM providers exhausted |
| `EvaluationError` | Quality evaluation computation failure |

---

## Database Schema

15 SQLAlchemy-backed tables managed in `agenticai_sdk/db/models.py`:

| Table | Key Fields | Purpose |
|-------|------------|---------|
| `users` | id, email, hashed_password, full_name, is_active, default_workspace_id | User accounts |
| `workspaces` | id, name, description, owner_id, plan_id, stripe_customer_id, stripe_subscription_id, subscription_status, created_at, updated_at | Multi-tenant workspace isolation |
| `workspace_members` | workspace_id (FK), user_id (FK), role (admin/editor/viewer) | Membership with RBAC role |
| `api_keys` | id, workspace_id (FK), workflow_id (FK, nullable), key_prefix, key_hash, name, is_active, created_at | API key storage (agk_ / wfk_) |
| `plans` | id, name, stripe_price_id, tokens_per_month, max_workflows, max_api_keys, max_team_members, features (JSON), price_cents, is_active | Subscription plan definitions |
| `policies` | id, name, description, policy_document (JSON), is_system | IAM policy definitions |
| `policy_attachments` | id, policy_id (FK), principal_type, principal_id | Principal-to-policy bindings |
| `workflows` | id, workspace_id (FK), name, description, config (JSON) | Persisted workflow definitions |
| `tools` | id, workspace_id (FK), name, description, tool_type, code_or_url | Registered tool metadata |
| `rag_sources` | id, workspace_id (FK), name, provider, config (JSON) | RAG source configurations |
| `activity_logs` | id, workspace_id, event_type, details (JSON), created_at | Audit trail for all mutations |
| `workflow_traces` | id, workflow_id (FK), trace_id, duration_ms, total_tokens, cost_usd, error_count, span_tree (JSON) | Deep execution traces |
| `schema_audit_trails` | id, agent_id, direction, payload (JSON), schema_definition (JSON), is_valid | Immutable IO payload audit log |
| `billing_data` | id, workspace_id, amount, currency, period_start, period_end, metrics (JSON) | Per-workspace billing records |
| `cron_jobs` | id, cron_expression, target_type, target_id, payload (JSON), last_run_at, next_run_at, status, locked_by, locked_until | Scheduled job definitions with lease-based locking |
| `integration_connections` | id, workspace_id, integration_type, name, auth_state (JSON), rate_limits (JSON), is_active | External service connection store |

### Data Access Layer (`db/dal.py`)
- `RelationalDAL` — CRUD operations for SQLAlchemy models
- `MongoDAL` — MongoDB-compatible operations
- `DALFactory` — Runtime adapter selection
- `DALEncryptor` — Transparent field-level encryption for sensitive data

### Plug-and-Play Database Persistence
The SDK **connects once and persists forever**. Configure your database once — it survives restarts.

**Resolution order**:
1. Explicit `--db-url` CLI argument
2. `.agenticai_db_config` file (persisted from a previous session)
3. `AGENTICAI_DB_URL` environment variable
4. SQLite fallback (`sqlite:///agenticai.db` — zero config, works immediately)

```bash
# First launch — zero config (auto-creates agenticai.db)
python main.py

# Switch to PostgreSQL — saved for all future restarts
curl -X POST http://localhost:8000/api/v1/workflow/db/connect \
  -H "Content-Type: application/json" \
  -d '{"core_db_url": "postgresql://user:pass@host:5432/agenticai"}'

# Or pass at startup
python main.py --db-url postgresql://user:pass@host:5432/agenticai
```

**Management endpoints**:
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/workflow/db/config` | View current persisted config |
| `POST` | `/api/v1/workflow/db/connect` | Connect to a new DB (persisted) |
| `POST` | `/api/v1/workflow/db/reset` | Reset to default SQLite |

---

## Universal RAG Connector

Connect to **any** RAG database via a generic HTTP interface. No SDK-specific client required.

```json
{
  "rag_id": "my_custom_db",
  "vector_db": "universal",
  "universal_base_url": "http://my-rag:8080",
  "universal_search_endpoint": "/v1/query",
  "universal_request_template": {
    "text": "{query}",
    "limit": "{top_k}"
  },
  "universal_response_path": "data.matches",
  "universal_content_field": "text",
  "universal_score_field": "relevance",
  "universal_auth_type": "bearer",
  "universal_auth_value": "your-token"
}
```

### Adapter Registry
For non-REST databases, register custom adapters:
```python
from agenticai_sdk.rag.vector_db_factory import VectorDBClientFactory
VectorDBClientFactory.register_adapter("my_custom_db", MyCustomClient)
```

The factory resolves in this order: **built-in providers → adapter registry → universal connector**.

---

## Enhanced Quality Evaluators

The `ResponseQualityEvaluator` now evaluates **6 dimensions**:

| Dimension | Score Range | Method | Description |
|-----------|-------------|--------|-------------|
| Relevance | 0.0–1.0 | `evaluate_relevance()` | TF-IDF weighted term overlap with query |
| Coherence | 0.0–1.0 | `evaluate_coherence()` | Vocabulary richness, sentence structure, structural markers |
| Groundedness | 0.0–1.0 | `evaluate_groundedness()` | Response alignment with retrieved RAG source documents |
| **Faithfulness** | 0.0–1.0 | `evaluate_faithfulness()` | Claim-level support — what fraction of claims are directly supported by source docs |
| **Completeness** | 0.0–1.0 | `evaluate_completeness()` | Coverage of query facets/key terms in the response |
| **Conciseness** | 0.0–1.0 | `evaluate_conciseness()` | Information density, type-token ratio, filler word penalty |

The composite `overall_score` when documents are available:
```python
overall = (0.20 * relevance + 0.15 * coherence + 0.20 * groundedness
           + 0.20 * faithfulness + 0.15 * completeness + 0.10 * conciseness)
```

---

## Per-Agent Context Files (agent.md / skill.md)

Each agent in a workflow can have its own markdown context files that provide customisation and behavioural guidelines.

### Directory Convention
```
agents/
  coordinator/
    agent.md      # Role definition, behavioural context, YAML frontmatter
    skill.md      # Dynamic IF/THEN skill rules (scoped to this agent)
  researcher/
    agent.md
    skill.md
```

### agent.md
May contain optional YAML frontmatter and markdown body:
```yaml
---
role: "Senior Researcher"
model_preference: "gpt-4o"
temperature: 0.3
---
You are a senior researcher agent. You must always cite sources and
prefer recent publications from 2024 onwards.
```

### skill.md
Dynamic rules that mutate agent configuration at runtime:
```markdown
## Context Rules
IF topic CONTAINS "urgent" THEN temperature = 0.1
IF prompt CONTAINS "creative" THEN temperature = 0.8

## Situational Boundaries
max_tokens = 4096 WHEN priority == "high"
```

### Configuration
Each `AgentNodeConfig` supports two new fields:
```json
{
  "agent_id": "researcher",
  "agent_context_path": "agents/researcher",
  "skill_context_path": "agents/researcher/skill.md"
}
```

---

## Third-Party Integrations

Connect Slack, Teams, Outlook, and WhatsApp once — connections persist in the database and are available as LangChain tools for agents to use in workflows.

### Connect Once, Persist Forever
```bash
# Register a Slack connection
curl -X POST http://localhost:8000/api/v1/workflow/integrations/connect \
  -H "Content-Type: application/json" \
  -d '{
    "integration_type": "slack",
    "name": "My Workspace Slack",
    "auth_state": {"webhook_url": "https://hooks.slack.com/..."}
  }'

# List active connections
curl http://localhost:8000/api/v1/workflow/integrations

# Test a connection
curl -X POST http://localhost:8000/api/v1/workflow/integrations/slack/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello from AgenticAI!"}'

# Disconnect
curl -X DELETE http://localhost:8000/api/v1/workflow/integrations/slack
```

### Available Integrations
| Type | Service | Auth Methods |
|------|---------|-------------|
| `slack` | Slack | Webhook URL, OAuth token |
| `teams` | Microsoft Teams | Office 365 Connector Webhook |
| `outlook` | Microsoft Outlook | Microsoft Graph API OAuth token |
| `whatsapp` | WhatsApp | Meta Cloud API token + Phone Number ID |

### Using Integrations as Agent Tools
Once connected, integrations are automatically available as tools that agents can invoke in workflows. Load them via:
```python
from agenticai_sdk.runtime.tool_registry import ToolRegistry
registry = ToolRegistry()
registry.load_integration_tools(workspace_id="default")
```

Agent can then use tool names like `send_slack_message`, `send_teams_message`, `send_outlook_email`, or `send_whatsapp_message` in their workflow configurations.

---

## Runtime Subsystems

### IntegrationRegistry (`runtime/integration_registry.py`)
Manages third-party communication channels:
- Slack, Microsoft Teams, Outlook, WhatsApp
- OAuth flow management and token refresh
- Per-channel rate limiting
- Template-based message formatting

### SkillsParser (`runtime/skills_parser.py`)
Parses `SKILLS.md` files to dynamically mutate agent configuration at runtime:
- Detects skill definitions, tool requirements, and middleware overrides
- Merges parsed skills into the active `WorkflowSchema` before compilation

### CronDaemon (`runtime/cron_daemon.py`)
A lightweight CRON scheduler embedded in the runtime:
- Expression parsing with `croniter`
- Lease-based distributed locking (avoids duplicate execution in multi-instance deployments)
- Targets: agent execution or workflow compilation
- Status lifecycle: active → paused → terminated

### ContextEngine (`runtime/context_engine.py`)
Manages prompt construction and memory windows:
- System message building from agent roles and middleware constraints
- Memory window management (sliding window, summary-based)
- RAG context injection into prompt templates
- Token-aware truncation before LLM submission

---

## Infrastructure Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Multi-stage build (gunicorn + uvicorn) |
| `.dockerignore` | Docker build context exclusions |
| `docker-compose.yml` | API + PostgreSQL + Redis + Prometheus (9090) + Grafana (3000) |
| `prometheus.yml` | Prometheus scrape config — targets `host.docker.internal:8000` every 5s |
| `pyproject.toml` | Build config (setuptools), Python >=3.12, all dependencies, Ruff linting (line-length=120) |
| `pytest.ini` | Test discovery path (`tests/`) with `asyncio_mode = auto` |
| `.env.example` | API key template for OpenAI, Anthropic, Qdrant, Pinecone |
| `example_workflow.json` | Complete sample hierarchical workflow (coordinator → researcher → writer) |
| `master_schema_reference.json` | Exhaustive reference schema showing every possible configuration option |
| `docs/delivery_summary.md` | Feature coverage matrix and delivery documentation |
| `docs/implementation_plan.md` | Architecture breakdown, 8-domain model, 8-phase build order |

---

## Testing

The test suite lives in `tests/` and covers **~168 tests** across 15 files:

| File | Tests | Scope |
|------|-------|-------|
| `test_schemas.py` | 20 | LLMConfig, PromptTemplate, ToolConfig, RAGConfig, Topology, WorkflowSchema, EdgeConfig validation |
| `test_middleware.py` | 14 | Pipeline ordering, Budget, PII masking, Firewall, Compression |
| `test_orchestration.py` | 12 | SchemaMapper, HITL breakpoints, Consensus |
| `test_evaluation.py` | 11 | TraceCollector, MetricsRegistry, ResponseQuality, WorkflowEvaluator |
| `test_gateway.py` | 5 | Health check, Request-ID, WorkflowRun, HITL approve |
| `test_runtime.py` | 11 | ToolRegistry (built-in, REST API, MCP), ContextEngine |
| `test_rag.py` | 6 | ContextInjector formatting |
| `test_master_agent.py` | 4 | MasterAgentRAG, StructuredMasterAgent, Gateway integration |
| `test_universal_rag.py` | 4 | Universal connector registration and query |
| `test_integration_routes.py` | 5 | Integration connect/list/disconnect/test |
| `test_auth_routes.py` | 21 | Register, login, profile, API keys CRUD, workspace-scoped keys, workspace members CRUD, RBAC |
| `test_client_sdk.py` | 13 | AgenticAI.run(), run_by_id(), last_message() via mock |
| `test_db_models.py` | 16 | User, Workspace, WorkspaceMember, ApiKey, Workflow, RAGSource, Tool, Plan ORM validation |
| `test_permissions.py` | 18 | Policy pattern matching, admin/editor/viewer evaluation, deny-override, resource scoping |

```bash
# Run the full test suite
pytest

# Run with coverage
pytest --cov=agenticai_sdk
```

---

## License

MIT — © AgenticAI SDK Contributors

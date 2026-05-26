# AgenticAI SDK — JSON-to-Workflow Engine

> **Production-grade, enterprise-ready framework** for compiling declarative JSON configurations into async, resilient, stateful multi-agent DAGs powered by **LangGraph** orchestration and **DeepAgent** cognitive loops.

---

## Architecture

```
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
  ├── MiddlewarePipeline (NEW v0.3)
  │     ├── BudgetGuardrails     → token/cost estimation & loop timeouts
  │     ├── PIIMaskingRouter     → PII/PHI detection & reversible masking
  │     ├── InjectionFirewall    → adversarial prompt detection
  │     ├── ContextCompression   → context window management
  │     ├── SchemaValidation     → Strict JSON Schema Input/Output enforcement (Audit Logged)
  │     └── RateLimiter          → Persistent execution throttling
  │
  ├── Enterprise Orchestration (NEW v0.3)
  │     ├── Multi-DB Data Router → Map stages to Postgres/ClickHouse/SQLite
  │     ├── MCP Connector (v1.0) → Standard Model Context Protocol integration
  │     ├── Dynamic Tooling      → Register Python code strings at runtime
  │     ├── HITLBreakpoints      → state freeze/thaw + Slack/Teams webhooks
  │     └── AgentDelegation      → Hierarchical sub-agent management
  │
  └── Evaluation & Observability (NEW v0.3)
        ├── Prometheus Metrics   → Latency/TPM/Error histogram exports
        ├── OpenTelemetry Spans  → Distributed distributed tracing
        ├── Schema Audit Trail   → Immutable database log of all IO payloads
        └── Dashboard API        → /api/v1/observability/*
              │
              ▼
        LangGraph StateGraph (compiled DAG)
              │
              ▼
        FastAPI Gateway
          ├── POST /api/v1/workflow/run
          ├── POST /api/v1/workflow/hitl/approve
          ├── GET  /metrics (Prometheus)
          ├── GET  /api/v1/observability/traces
          └── GET  /api/v1/observability/health
```

---

## Package Layout

```
agenticai_sdk/
├── __init__.py                      # version = "0.2.0"
├── exceptions.py                    # Domain exception hierarchy (21 exception types)
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
│   ├── agent_node.py               # AgentNodeConfig (+ fallback_llms, consensus_config, middleware_config, input/output schema, agent_context_path, skill_context_path)
│   ├── edges.py                     # EdgeConfig (JSON-based conditional routing)
│   ├── workflow.py                  # WorkflowSchema (root + referential integrity validators)
│   └── integration.py              # IntegrationConfig + IntegrationType enum (NEW)
├── state/                           # Shared state type
│   └── workflow_state.py            # WorkflowState TypedDict (messages, scratchpad, retrieved_context, etc.)
├── db/                              # Multi-DB Persistence Layer
│   ├── database.py                  # Dynamic DB Router (Postgres/SQLite/ClickHouse)
│   ├── models.py                    # SQLAlchemy Models (9 tables: Workspace, Workflow, Tool, ActivityLog, WorkflowTrace, SchemaAuditTrail, BillingData, CronJob, IntegrationConnection)
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
├── deep_agent/                       # DeepAgent Cognitive Loop
│   ├── __init__.py
│   └── factory.py                   # DeepAgentFactory (model_driven/agent_driven loops)
├── rag/                              # RAG Subsystem
│   ├── __init__.py
│   ├── vector_db_factory.py         # VectorDBClientFactory (Qdrant, Pinecone, PgVector, ChromaDB, FAISS, Universal, adapter registry)
│   ├── retriever_engine.py          # KnowledgeRetrieverEngine (async retrieval, S3/upload ingestion)
│   ├── context_injector.py          # ContextInjector (document formatting for prompt injection)
│   └── universal_connector.py       # UniversalRAGConnector — generic HTTP connector for any RAG DB (NEW)
├── runtime/                          # Executive Runtime
│   ├── __init__.py                  # Lazy-loads Orchestrator
│   ├── orchestrator.py              # Macro-execution engine (compiles WorkflowSchema -> LangGraph StateGraph)
│   ├── llm_factory.py               # LLMClientFactory (OpenAI, Anthropic, Ollama)
│   ├── tool_registry.py             # ToolRegistry (MCP, REST API, custom Python, built-in, integration tools)
│   ├── integration_registry.py      # IntegrationRegistry (Slack, Teams, Outlook, WhatsApp)
│   ├── skills_parser.py             # SKILLS.md parser for dynamic config mutation (+ parse_directory, parse_agent_md)
│   ├── agent_context_loader.py      # Per-agent agent.md / skill.md context loader (NEW)
│   ├── cron_daemon.py               # CRON scheduling daemon with lease locks
│   └── context_engine.py            # Prompt rendering, system message building, memory window
├── evaluation/                       # Observability Suite
│   ├── __init__.py
│   ├── trace_collector.py           # OTel Bridge + SQL Span Trees
│   ├── metrics.py                   # Latency/token/cost aggregation
│   ├── evaluators.py                # ResponseQualityEvaluator + WorkflowEvaluator
│   └── dashboard.py                 # FastAPI observability API endpoints
├── gateway/                          # FastAPI Gateway
│   ├── __init__.py
│   ├── app.py                       # App factory + structlog config + CORS + exception handlers
│   ├── routes/                      # Consolidated route modules (auth, workflows, integrations, observability, billing)
│   │   ├── __init__.py              # Exports route_modules list for app factory
│   │   ├── auth.py                  # Auth routes (register, login, API keys, workspace members)
│   │   ├── workflows.py             # Workflow execution, HITL, SaaS CRUD, master agent
│   │   ├── integrations.py          # Third-party integration management
│   │   ├── observability.py         # Traces, metrics, evaluations, health
│   │   └── billing.py               # Stripe billing (dormant — stripe dep removed)
│   └── middleware.py                # ExecutionTrackingMiddleware (request ID, timing)
├── master_agent/                     # Upstream natural-language intake
│   ├── __init__.py                  # Exports StructuredMasterAgent, MasterAgentRAG
│   ├── agent.py                     # StructuredMasterAgent — LLM-based schema synthesis (no fallback)
│   ├── rag.py                       # MasterAgentRAG — keyword-based doc retrieval
│   └── context_loader.py            # Agent context file scanner (agent.md / skill.md) (NEW)
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
- Uses `MasterAgentRAG` to retrieve context from `master_schema_reference.json`, `README.md`, and `implementation_plan.md`.
- Attempts structured LLM output first; falls back to a deterministic rule-based engine that creates single/multi-agent workflows based on keywords (search, python, weather, write, report).

### MasterAgentRAG
- Chunks reference documents by markdown headers and JSON boundaries.
- Scores chunks by keyword overlap with boost for title matches.
- Returns top-k relevant documentation snippets to guide the LLM synthesis.

---

## Frontend Application

A Next.js application (`Frontend/frontend/`) provides a visual interface for building, monitoring, and managing workflows.

### Tech Stack
- **Framework**: Next.js (App Router), TypeScript
- **Styling**: Tailwind CSS + shadcn/ui (~45 components)
- **State**: Zustand store
- **DB Adapters**: PostgreSQL (production), Mock adapter (development)

### Pages
| Route | Description |
|-------|-------------|
| `/` | Main workflow canvas — drag-and-drop agent graph editor |
| `/activity` | Execution activity log and history |
| `/billing` | Usage metrics and billing data |
| `/rag` | RAG source configuration and document management |
| `/settings` | Global settings and integration configuration |
| `/tools` | Tool registry management |

### Key Components
- **`workflow/workflow-canvas.tsx`** — Interactive DAG editor for agent nodes and edges
- **`workflow/agent-config-sidebar.tsx`** — Per-agent configuration panel (LLM, tools, middleware)
- **`workflow/agent-node.tsx`** — Visual node component on the canvas
- **`workflow/registry-drawer.tsx`** — Drawer for browsing tools, RAG sources, and templates
- **`global-sidebar.tsx`** — Main navigation sidebar
- **`ui/`** — 45+ reusable shadcn/ui components (accordion, dialog, chart, form, table, etc.)

### Data Layer
- `lib/api.ts` — HTTP client for the FastAPI gateway
- `lib/store.ts` — Zustand state management
- `lib/db/` — Multi-adapter DB layer (PostgreSQL adapter + mock adapter for development)

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

### `POST /api/v1/workflow/run`
| Field | Type | Description |
|-------|------|-------------|
| `workflow` | `WorkflowSchema` | Complete workflow JSON |
| `input_message` | `str` | Initial user task |
| `thread_id` | `str?` | Optional session ID (auto-generated if omitted) |
| `initial_scratchpad` | `dict?` | Pre-populated scratchpad values |

### `POST /api/v1/workflow/hitl/approve`
| Field | Type | Description |
|-------|------|-------------|
| `thread_id` | `str` | ID of interrupted session |
| `approved` | `bool` | True to resume, False to reject |
| `state_updates` | `dict?` | Optional state overrides before resumption |
| `workflow` | `WorkflowSchema` | Original workflow schema |

### Master Agent Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflow/master/generate` | Generate a WorkflowSchema proposal from a natural-language prompt |
| `POST` | `/api/v1/workflow/master/compile` | Validate, compile, and persist a WorkflowSchema |

### SaaS CRUD Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/workflow/workflows` | List all persisted workflows |
| `POST` | `/api/v1/workflow/workflows` | Create a new workflow |
| `GET` | `/api/v1/workflow/workflows/{id}` | Get a workflow by ID |
| `PATCH` | `/api/v1/workflow/workflows/{id}` | Update a workflow |
| `DELETE` | `/api/v1/workflow/workflows/{id}` | Delete a workflow |
| `DELETE` | `/api/v1/workflow/workspaces/{id}` | Delete a workspace (cascades to workflows) |
| `GET` | `/api/v1/workflow/tools` | List all registered tools |
| `POST` | `/api/v1/workflow/tools` | Register a new tool (MCP, custom Python, etc.) |
| `GET` | `/api/v1/workflow/activity` | Recent activity log (last 50 entries) |
| `GET` | `/api/v1/workflow/metrics` | Prometheus metrics export (`/metrics`)

### Database Management Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/workflow/db/status` | Database connection status and collection counts |
| `POST` | `/api/v1/workflow/db/connect` | Connect to a new database (persisted for restarts) |
| `GET` | `/api/v1/workflow/db/config` | View current persisted database configuration |
| `POST` | `/api/v1/workflow/db/reset` | Reset to default SQLite database |

### Integration Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/workflow/integrations/connect` | Register a third-party integration (Slack, Teams, Outlook, WhatsApp) |
| `GET` | `/api/v1/workflow/integrations` | List all active integration connections |
| `DELETE` | `/api/v1/workflow/integrations/{type}` | Disconnect an integration |
| `POST` | `/api/v1/workflow/integrations/{type}/test` | Send a test message to verify connectivity |

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

9 SQLAlchemy-backed tables managed in `agenticai_sdk/db/models.py`:

| Table | Key Fields | Purpose |
|-------|------------|---------|
| `workspaces` | id, name, description, created_at, updated_at | Multi-tenant workspace isolation |
| `workflows` | id, workspace_id (FK), name, description, config (JSON) | Persisted workflow definitions |
| `tools` | id, name, description, tool_type, code_or_url | Registered tool metadata |
| `activity_logs` | id, workspace_id, workflow_id, event_type, details (JSON) | Audit trail for all mutations |
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
| `docker-compose.yml` | Spins up Prometheus (port 9090) + Grafana (port 3000) for metrics dashboards (admin/admin) |
| `prometheus.yml` | Prometheus scrape config — targets `host.docker.internal:8000` every 5s |
| `pyproject.toml` | Build config (setuptools), Python >=3.12, all dependencies (pydantic, langchain, langgraph, fastapi, qdrant, pinecone, chromadb, faiss, sqlalchemy, boto3, prometheus-client, opentelemetry, croniter, cryptography, pymongo), Ruff linting (line-length=120) |
| `pytest.ini` | Test discovery path (`tests/`) with `asyncio_mode = auto` |
| `.env.example` | API key template for OpenAI, Anthropic, Qdrant, Pinecone |
| `example_workflow.json` | Complete sample hierarchical workflow (coordinator → researcher → writer) |
| `master_schema_reference.json` | Exhaustive reference schema showing every possible configuration option |
| `implementation_plan.md` | Architecture breakdown, 8-domain model, 8-phase build order |
| `delivery_summary.md` | Feature coverage matrix and delivery documentation |

---

## Testing

The test suite lives in `tests/` and covers **83+ tests** across 8 files:

| File | Tests | Scope |
|------|-------|-------|
| `test_schemas.py` | 20 | LLMConfig, PromptTemplate, ToolConfig, RAGConfig, Topology, WorkflowSchema, EdgeConfig validation |
| `test_middleware.py` | 14 | Pipeline ordering, Budget, PII masking, Firewall, Compression |
| `test_orchestration.py` | 12 | SchemaMapper, HITL breakpoints, Consensus (similarity/temperatures) |
| `test_evaluation.py` | 11 | TraceCollector, MetricsRegistry, ResponseQuality, WorkflowEvaluator |
| `test_gateway.py` | 5 | Health check, Request-ID header, WorkflowRun, HITL approve |
| `test_runtime.py` | 11 | ToolRegistry (built-in, REST API, MCP), ContextEngine |
| `test_rag.py` | 6 | ContextInjector formatting |
| `test_master_agent.py` | 4 | MasterAgentRAG, StructuredMasterAgent, Gateway integration |

```bash
# Run the full test suite
pytest

# Run with coverage
pytest --cov=agenticai_sdk
```

---

## License

MIT — © AgenticAI SDK Contributors

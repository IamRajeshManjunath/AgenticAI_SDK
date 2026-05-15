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
  ├── ToolRegistry       → MCP / REST API / Custom Python / Built-in
  ├── VectorDBClientFactory → Qdrant / Pinecone / PgVector
  ├── KnowledgeRetrieverEngine → async semantic retrieval
  └── DeepAgentFactory
        ├── model_driven  → ReAct-style autonomous tool use
        └── agent_driven  → explicit reasoning step sequences
              │
              ▼
        LangGraph StateGraph (compiled DAG)
              │
              ▼
        FastAPI Gateway
          ├── POST /api/v1/workflow/run
          └── POST /api/v1/workflow/hitl/approve
```

---

## Package Layout

```
agenticai_sdk/
├── __init__.py
├── exceptions.py               # Domain exception hierarchy
├── schemas/                    # Pydantic V2 models
│   ├── llm.py                  # LLMConfig + LLMProvider enum
│   ├── tools.py                # ToolConfig + ToolType enum
│   ├── prompts.py              # PromptTemplateConfig (compile-time var validation)
│   ├── memory.py               # MemoryConfig + enums
│   ├── hitl.py                 # HITLConfig + NotificationChannel enum
│   ├── rag.py                  # RAGConfig + VectorDB/Embedding enums
│   ├── topology.py             # DeepAgentTopologyConfig + OrchestrationMode enum
│   ├── agent_node.py           # AgentNodeConfig (composite)
│   ├── edges.py                # EdgeConfig (conditional routing)
│   └── workflow.py             # WorkflowSchema (root + referential integrity)
├── state/
│   └── workflow_state.py       # WorkflowState TypedDict
├── rag/
│   ├── vector_db_factory.py    # VectorDBClientFactory
│   ├── retriever_engine.py     # KnowledgeRetrieverEngine
│   └── context_injector.py     # ContextInjector
├── deep_agent/
│   └── factory.py              # DeepAgentFactory + create_deep_agent
├── runtime/
│   ├── llm_factory.py          # LLMClientFactory
│   ├── tool_registry.py        # ToolRegistry
│   ├── context_engine.py       # ContextEngine
│   └── orchestrator.py         # Orchestrator (core compilation engine)
└── gateway/
    ├── middleware.py            # ExecutionTrackingMiddleware
    ├── routes.py               # FastAPI route handlers
    └── app.py                  # App factory + structlog config
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
    "workflow": <contents of example_workflow.json>,
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

## Core Concepts

### WorkflowSchema
The single source of truth. Author a JSON file that defines:
- **Global tools** (MCP, REST API, custom Python, built-in)
- **RAG sources** (Qdrant, Pinecone, PgVector)
- **Agent nodes** with LLM configs, prompts, topology, and memory
- **Edges** with optional condition expressions
- **HITL** interruption points

### WorkflowState
Every node receives and returns a `WorkflowState` TypedDict:
```python
{
    "messages":          [...],   # Full message history (add_messages accumulator)
    "scratchpad":        {...},   # Cross-agent key-value store
    "retrieved_context": [...],   # RAG documents pulled across steps
    "inner_thoughts":    [...],   # Chain-of-thought reasoning traces
    "next_step":         "..."    # Routing signal for conditional edges
}
```

### OrchestrationMode
- **`model_driven`** — LLM autonomously decides tool usage (ReAct loop)
- **`agent_driven`** — Follows explicit `reasoning_steps` sequences for structured CoT

### Conditional Edge Routing
Edge conditions are Python expressions evaluated against `state`:
```json
{ "condition": "state[\"next_step\"] == \"review\"" }
{ "condition": "len(state[\"messages\"]) > 10" }
{ "condition": "\"error\" in state[\"scratchpad\"]" }
```

### HITL (Human-in-the-Loop)
List agent IDs in `hitl.interruption_points`. The graph pauses at those nodes.
Resume via `POST /api/v1/workflow/hitl/approve` with `{ "approved": true }`.

---

## API Reference

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

---

## Domain Exceptions

| Exception | Trigger |
|-----------|---------|
| `WorkflowCompilationError` | Graph compilation failure |
| `ToolResolutionError` | Unknown `tool_id` reference |
| `LLMProviderError` | LLM client instantiation failure |
| `RAGFetchException` | Vector DB retrieval failure |
| `DeepAgentExecutionError` | Inner cognitive loop fatal error |
| `DeepAgentFallbackExhausted` | All fallback strategies exhausted |
| `HITLTimeoutError` | Human approval timeout exceeded |
| `GraphRoutingError` | Conditional edge evaluation failure |

---

## License

MIT — © AgenticAI SDK Contributors

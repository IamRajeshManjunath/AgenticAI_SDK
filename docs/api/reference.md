# AgenticAI SDK v0.3 - API Reference

## Table of Contents

1. [Configuration](#configuration)
2. [Plugin Registry](#plugin-registry)
3. [Chat Models](#chat-models)
4. [Tools](#tools)
5. [Database Routes](#database-routes)
6. [RAG Pipeline](#rag-pipeline)
7. [Middleware](#middleware)
8. [Backends](#backends)
9. [Security & IAM](#security--iam)
10. [Observability](#observability)
11. [Governance](#governance)
12. [Skills](#skills)

---

## Configuration

### `AgenticAIConfig`
Main configuration class for the SDK.

```python
from agenticai_sdk.config.schemas import AgenticAIConfig, PlatformConfig, ChatModelConfig

config = AgenticAIConfig(
    platform=PlatformConfig(
        default_chat_model="primary",
        default_embedding="openai",
        enable_telemetry=True,
    ),
    chat_models={
        "primary": ChatModelConfig(
            type=IntegrationType.OPENAI,
            provider="openai",
            model="gpt-4o",
            api_key_env="OPENAI_API_KEY",
        )
    },
    database_routes={...},
)
```

### `load_config()`
Load configuration with YAML + JSON merge and env var interpolation.

```python
from agenticai_sdk.config.loader import load_config

# Load from agenticai.yaml + runtime JSON overrides
config = load_config(
    config_path="agenticai.yaml",
    runtime_overrides={"chat_models": {"primary": {"model": "gpt-4o-mini"}}}
)
```

### Environment Variable Interpolation
```yaml
# agenticai.yaml
chat_models:
  primary:
    api_key_env: "${OPENAI_API_KEY}"
    model: "${MODEL:-gpt-4o}"
```

---

## Plugin Registry

### `IntegrationRegistry`
Central registry for all integration plugins.

```python
from agenticai_sdk.plugins import get_global_registry

registry = get_global_registry()
registry.load_entry_points()  # Auto-discovers pip-installed plugins

# List all plugins
plugins = registry.list_plugins()

# Get specific plugin
plugin = registry.get_plugin("chat_model", "openai")

# Create instance with config
instance = registry.create_instance("chat_model", "openai", config={"model": "gpt-4o"})
```

### Plugin Types
- `chat_model` - LLM providers (25+)
- `embedding` - Embedding providers (8+)
- `vector_store` - Vector databases (6+)
- `tool` - Tools & toolkits (10+)
- `sandbox` - Code execution sandboxes (4)
- `checkpointer` - LangGraph checkpointers (3)
- `store` - LangGraph stores (3)
- `middleware` - Request/response middleware
- `backend` - Execution backends

---

## Chat Models

### Supported Providers
| Provider | Models | Features |
|----------|--------|----------|
| OpenAI | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo | Stream, Tools, Structured, Multimodal |
| Anthropic | claude-3.5-sonnet, claude-3-opus, claude-3-haiku | Stream, Tools, Structured, Multimodal |
| Google | gemini-1.5-pro, gemini-1.5-flash | Stream, Tools, Structured, Multimodal |
| Groq | llama-3.1-70b, llama-3.1-8b, mixtral-8x7b | Stream, Tools, Structured |
| Mistral | mistral-large, mistral-small, codestral | Stream, Tools, Structured |
| Cohere | command-r-plus, command-r | Stream, Tools, Structured |
| ...and 19 more | | |

### Usage
```python
from agenticai_sdk.plugins import get_global_registry

registry = get_global_registry()
registry.load_entry_points()

# Create chat model
llm = registry.create_instance(
    "chat_model", 
    "openai",
    config={
        "model": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 2000,
    }
)

# Use with LangChain
response = await llm.ainvoke("Hello, world!")
```

---

## Tools

### Supported Tools
| Tool | Category | Description |
|------|----------|-------------|
| Tavily | Search | AI-powered web search |
| Composio | Integration | 500+ tools (GitHub, Slack, Jira, Notion, Salesforce) |
| Exa | Search | Neural web search |
| Google Search | Search | Custom search API |
| Python REPL | Code | Code execution |
| Requests | HTTP | HTTP requests |
| Shell | System | Shell commands |
| File Operations | Files | Read/write files |

### Usage
```python
from agenticai_sdk.plugins import get_global_registry

registry = get_global_registry()
registry.load_entry_points()

# Create tool
tavily = registry.create_instance(
    "tool",
    "tavily",
    config={"api_key_env": "TAVILY_API_KEY", "max_results": 10}
)

# Use with LangChain agent
tools = [tavily]
agent = create_agent(llm, tools)
```

---

## Database Routes

### Purpose-Bound Architecture
Each database route is bound to a specific purpose with strict schema validation.

```python
from agenticai_sdk.config.schemas import DatabaseRouteConfig, DatabasePurpose

route = DatabaseRouteConfig(
    purpose=DatabasePurpose.VECTOR_STORE,
    provider="qdrant",
    config={"url": "http://localhost:6333", "collection": "documents"},
    schema_contract={
        "purpose": "vector_store",
        "collections": {
            "documents": {
                "columns": {
                    "vector": {"type": "vector", "dimension": 1536},
                    "content": {"type": "text"},
                    "metadata": {"type": "json"},
                }
            }
        }
    }
)
```

### Purposes
| Purpose | Description | Schema Requirements |
|---------|-------------|---------------------|
| `vector_store` | Document embeddings for RAG | Collections with vector columns |
| `checkpointer` | LangGraph workflow state | Standard LangGraph tables |
| `store` | Long-term key-value memory | Standard LangGraph store table |
| `analytics` | Custom analytics/metrics | Events table with timestamp |
| `audit_log` | Immutable governance events | Append-only audit table |
| `cache` | Ephemeral caching with TTL | Key-value with expiration |
| `rate_limit` | Rate limiting counters | Counter with window |

### DynamicDatabaseFactory
```python
from agenticai_sdk.db.factory import DynamicDatabaseFactory

factory = DynamicDatabaseFactory()

# Purpose-bound creation - ONLY works for matching purpose
vector_store = factory.create_vector_store(route_config)  # Requires VECTOR_STORE purpose
checkpointer = factory.create_checkpointer(route_config)  # Requires CHECKPOINTER purpose
store = factory.create_store(route_config)  # Requires STORE purpose

# Schema validation at creation
factory.validate_schema(route_config)  # Raises if schema doesn't match
```

---

## RAG Pipeline

### Factories
```python
from agenticai_sdk.rag.factories import (
    EmbeddingFactory,
    VectorStoreFactory,
    RetrieverFactory,
    TextSplitterFactory,
    DocumentLoaderFactory,
    RAGPipeline,
)

# Create components
embeddings = EmbeddingFactory.create("openai", config={"model": "text-embedding-3-large"})
vector_store = VectorStoreFactory.create("qdrant", config={"url": "http://localhost:6333"})
retriever = RetrieverFactory.create("similarity", vector_store=vector_store, k=5)
splitter = TextSplitterFactory.create("recursive", chunk_size=1000, chunk_overlap=200)
loader = DocumentLoaderFactory.create("pdf", file_path="doc.pdf")

# Full pipeline
pipeline = RAGPipeline(
    embeddings=embeddings,
    vector_store=vector_store,
    retriever=retriever,
    text_splitter=splitter,
    document_loader=loader,
)

# Index documents
await pipeline.aindex_documents(["doc1.pdf", "doc2.pdf"])

# Query
results = await pipeline.aquery("What is AgenticAI?")
```

---

## Middleware

### Built-in Middleware
```python
from agenticai_sdk.middleware.registry import MiddlewareRegistry, create_default_pipeline

registry = MiddlewareRegistry()

# Built-in middleware
registry.register("logging", LoggingMiddleware())
registry.register("tracing", TracingMiddleware())
registry.register("rate_limit", RateLimitMiddleware())
registry.register("auth", AuthMiddleware())
registry.register("cost_tracking", CostTrackingMiddleware())

# Create pipeline
pipeline = create_default_pipeline()
```

### Custom Middleware
```python
from agenticai_sdk.middleware.base import BaseMiddleware

class CustomMiddleware(BaseMiddleware):
    async def process_request(self, request):
        # Pre-processing
        return request
    
    async def process_response(self, response):
        # Post-processing
        return response

registry.register("custom", CustomMiddleware())
```

---

## Backends

### Backend Types
| Backend | Type | Use Case |
|---------|------|----------|
| `STATE` | In-memory | Development/testing |
| `FILESYSTEM` | Local files | Persistent local state |
| `STORE` | LangGraph Store | Long-term memory |
| `CONTEXT_HUB` | Context hub | Shared context |
| `SANDBOX` | Code execution | Secure code running |
| `LOCAL_SHELL` | Shell commands | System operations |
| `COMPOSITE` | Multi-backend | Production orchestration |

### Usage
```python
from agenticai_sdk.runtime.backend_registry import BackendRegistry, BackendType

registry = BackendRegistry()

# Create backend
backend = registry.create_backend(
    BackendType.COMPOSITE,
    config={
        "backends": [
            {"type": "state", "config": {}},
            {"type": "filesystem", "config": {"path": "./data"}},
        ]
    }
)

# Execute
result = await backend.execute(agent, input_data)
```

---

## Security & IAM

### Permissions
```python
from agenticai_sdk.auth.permissions import (
    PERMISSION_INTEGRATION_CHAT_MODEL_READ,
    PERMISSION_INTEGRATION_CHAT_MODEL_WRITE,
    PERMISSION_DATABASE_ROUTE_READ,
    PERMISSION_DATABASE_ROUTE_WRITE,
    PERMISSION_AGENT_EXECUTE,
    PERMISSION_TRACE_READ,
    PERMISSION_COST_READ,
    PERMISSION_GOVERNANCE_READ,
    PERMISSION_APIKEY_READ,
    PERMISSION_APIKEY_WRITE,
    # ... 50+ more
)

# Check permission
if user.has_permission(PERMISSION_DATABASE_ROUTE_WRITE):
    # Allow database route creation
```

### API Key Scopes
```python
from agenticai_sdk.auth.schemas import ApiKeyCreateRequest

request = ApiKeyCreateRequest(
    name="Production Key",
    scopes=[
        "chat_model:read",
        "chat_model:write",
        "embedding:read",
        "vector_store:read",
        "vector_store:write",
        "tool:execute",
        "database:read",
        "database:write",
    ],
    expires_in_days=90,
)
```

### Roles
- **Admin**: Full system access, manage users/roles, all permissions
- **Editor**: Create/edit agents, configure integrations, view traces/costs
- **Viewer**: Read-only access to dashboards, traces, costs

---

## Observability

### UnifiedTelemetry
```python
from agenticai_sdk.observability.unified import UnifiedTelemetry

telemetry = UnifiedTelemetry()

# Trace operations
with telemetry.trace("rag_query") as span:
    span.set_attribute("query", user_query)
    result = await rag_pipeline.aquery(user_query)
    span.set_attribute("tokens", result.tokens_used)
```

### CostGovernance
```python
from agenticai_sdk.observability.unified import CostGovernance

governance = CostGovernance(
    monthly_budget=500.0,
    alert_threshold=0.8,
    block_threshold=1.0,
)

# Check budget
if governance.check_budget(current_spend):
    # Allow request
    pass
else:
    # Block request
    raise BudgetExceededError()
```

### HealthMonitor
```python
from agenticai_sdk.observability.unified import HealthMonitor

monitor = HealthMonitor()

# Register health checks
monitor.register_check("postgres", check_postgres_connection)
monitor.register_check("qdrant", check_qdrant_connection)
monitor.register_check("openai", check_openai_api)

# Get health status
health = await monitor.get_health_status()
# Returns: {"postgres": "healthy", "qdrant": "healthy", "openai": "degraded"}
```

---

## Governance

### GovernanceEventTracker
```python
from agenticai_sdk.observability.unified import GovernanceEventTracker

tracker = GovernanceEventTracker()

# Track events
tracker.track_event(
    event_type="COMPLIANCE_CHECK",
    severity="info",
    message="Data retention policy validated",
    workspace="prod",
    user="system",
)
```

### ComplianceManager
```python
from agenticai_sdk.observability.unified import ComplianceManager

compliance = ComplianceManager()

# Define policies
compliance.create_policy(
    name="Data Retention",
    type="RETENTION",
    config={"retention_days": 90, "action": "delete"},
    workspaces=["prod", "staging"],
)

# Check compliance
violations = compliance.check_compliance(workspace="prod")
```

---

## Frontend API Routes

### Integrations
```
GET    /api/v1/integrations              # List all plugins
POST   /api/v1/integrations              # Install plugin
GET    /api/v1/integrations/[provider]   # Get plugin details
PUT    /api/v1/integrations/[provider]   # Configure plugin
DELETE /api/v1/integrations/[provider]   # Uninstall plugin
```

### Database Routes
```
GET    /api/v1/database-routes           # List routes
POST   /api/v1/database-routes           # Create route
GET    /api/v1/database-routes/[id]      # Get route
PUT    /api/v1/database-routes/[id]      # Update route
DELETE /api/v1/database-routes/[id]      # Delete route
POST   /api/v1/database-routes/[id]?action=test           # Test connection
POST   /api/v1/database-routes/[id]?action=validate-schema # Validate schema
```

### Observability
```
GET /api/v1/observability?type=summary     # Dashboard summary
GET /api/v1/observability?type=traces      # Request traces
GET /api/v1/observability?type=costs       # Cost breakdown
GET /api/v1/observability?type=health      # Component health
```

### Governance
```
GET /api/v1/governance?type=events     # Audit events
GET /api/v1/governance?type=policies   # Compliance policies
GET /api/v1/governance?type=api-keys   # API keys
GET /api/v1/governance?type=summary    # Governance summary
POST /api/v1/governance?type=policy    # Create policy
POST /api/v1/governance?type=api-key   # Create API key
```

### Auth
```
GET  /api/v1/auth?type=me           # Current user
GET  /api/v1/auth?type=users        # List users
GET  /api/v1/auth?type=permissions  # Role permissions
GET  /api/v1/auth?type=api-keys     # User API keys
POST /api/v1/auth?action=create-api-key  # Create API key
POST /api/v1/auth?action=revoke-api-key  # Revoke API key
```

---

## Skills

### Overview

Deep Agent Skills are file-based capabilities that follow the [Agent Skills specification](https://agentskills.io/). Each skill is a directory containing a `SKILL.md` file with YAML frontmatter and markdown instructions. Skills are loaded with progressive disclosure: name and description are loaded at startup, full content only when activated.

### Skills Models

```python
from agenticai_sdk.skills import (
    SkillFrontmatter,
    SkillManifest,
    SkillFile,
    SkillFileType,
    SkillSource,
    SkillMetadata,
    RemoteSkillSource,
    SkillsConfig,
    SkillValidationError,
)
```

### SkillFrontmatter
YAML frontmatter for SKILL.md per Agent Skills specification:
- `name`: Skill name (lowercase, hyphens, max 64 chars)
- `description`: What the skill does and when to use it (1-1024 chars)
- `license`: Optional license name
- `compatibility`: Environment requirements
- `metadata`: Arbitrary key-value metadata
- `allowed_tools`: Space-separated pre-approved tools

### SkillManifest
Complete skill manifest with frontmatter, content, and supporting files:
```python
manifest = SkillManifest(
    frontmatter=SkillFrontmatter(...),
    content="# Skill content...",
    path=Path("skills/my-skill"),
    files=[SkillFile(path="scripts/run.py", content="...", type=SkillFileType.SCRIPT)],
    source=SkillSource.LOCAL,
)
```

### SkillsConfig
Configuration for the skills system:
```python
from agenticai_sdk.config.schemas import SkillsConfig, RemoteSkillSource

skills_config = SkillsConfig(
    enabled=True,
    skills_dir="skills",
    auto_discover=True,
    watch_for_changes=True,
    deep_agent_model="anthropic:claude-sonnet-4-6",
    remote_sources=[
        RemoteSkillSource(type="git", url="https://github.com/org/skills.git", branch="main"),
    ],
    validation_mode="strict",
)
```

### SkillsLoader
Disk-based skill discovery and loading:
```python
from agenticai_sdk.skills import create_skills_loader, SkillsConfig
from pathlib import Path

config = SkillsConfig(skills_dir="skills")
loader = create_skills_loader(config, Path.cwd())

# Discover all skills
skills = loader.discover_skills()

# Load specific skill
skill = loader.load_skill("web-research")

# Validate skill
errors = loader.validate_skill(skill)
```

### SkillsRegistry
Central registry with caching, hot reload, and deepagents integration:
```python
from agenticai_sdk.skills import get_skills_registry, SkillsConfig
from pathlib import Path

config = SkillsConfig(skills_dir="skills")
registry = get_skills_registry(config, Path.cwd())

# Initialize (discovers all skills)
skills = registry.initialize()

# List skills for system prompt
metadata = registry.list_skills()

# Get deepagents source paths
sources = registry.get_deepagents_sources()
# Returns: ['/path/to/skills/web-research', ...]

# Hot reload on file changes
registry.start_watching()  # Automatic via watchdog

# CRUD operations
manifest = registry.create_skill(name, frontmatter, content, files)
manifest = registry.update_skill(name, frontmatter=..., content=...)
registry.delete_skill(name)

# Validate
errors = registry.validate_skill("web-research")
```

### DeepAgents Integration
Create Deep Agents with skills using the `deepagents` package:
```python
from agenticai_sdk.skills import create_agentic_deep_agent, DeepAgentsIntegration
from agenticai_sdk.config.schemas import AgenticAIConfig
from pathlib import Path

config = AgenticAIConfig()  # Your AgenticAI config

# High-level factory
agent = create_agentic_deep_agent(
    config=config,
    project_root=Path.cwd(),
    model="anthropic:claude-sonnet-4-6",
    checkpointer=checkpointer,
    store=store,
)

# Or use integration directly
integration = DeepAgentsIntegration(config, Path.cwd())
agent_node = integration.create_deep_agent(
    agent_config=agent_config,
    rag_retriever_map=rag_map,
    schema_config=workflow_schema,
    checkpointer=checkpointer,
    store=store,
)
```

### Built-in Skills
The SDK includes 7 built-in skills in `skills/`:
| Skill | Description |
|-------|-------------|
| `web-research` | Search web and synthesize findings |
| `code-generation` | Generate code from specifications |
| `document-analysis` | Analyze documents for insights |
| `data-processing` | Transform, clean, analyze data |
| `api-integration` | Connect to external APIs |
| `reasoning` | Multi-step reasoning (CoT, ToT, Reflexion) |
| `planning` | Create execution plans for complex tasks |

### Skill Structure
Each skill is a directory with:
```
skill-name/
├── SKILL.md              # Required: frontmatter + instructions
├── scripts/              # Optional: executable code
├── references/           # Optional: documentation
├── assets/               # Optional: templates, resources
└── templates/            # Optional: document templates
```

### SKILL.md Format
```markdown
---
name: my-skill
description: What this skill does and when to use it.
license: MIT
compatibility: Requires Python 3.11+
metadata:
  author: my-org
  version: "1.0"
allowed_tools: PythonREPL TavilySearch
---

# My Skill

## Overview
Description of the skill.

## Instructions

### 1. Step One
Do something.

### 2. Step Two
Do something else.

## Examples
### Example 1
**Input**: Example input
**Output**: Expected output
```

### Frontend API Routes
```
GET    /api/v1/skills                    # List all skills
POST   /api/v1/skills                    # Create new skill
GET    /api/v1/skills/{name}             # Get full skill content
PUT    /api/v1/skills/{name}             # Update skill
DELETE /api/v1/skills/{name}             # Delete skill
POST   /api/v1/skills/{name}/validate    # Validate SKILL.md
POST   /api/v1/skills/reload             # Trigger hot reload
POST   /api/v1/skills/sync               # Sync remote sources
GET    /api/v1/skills/{name}/files       # List supporting files
POST   /api/v1/skills/{name}/files       # Upload supporting file
```

### Frontend Pages
- `/skills` - Skills Dashboard (searchable grid with actions)
- `/skills/new` - Skill Editor (create new skill)
- `/skills/[name]` - Skill Viewer (rendered markdown + files)
- `/skills/[name]/edit` - Skill Editor (edit existing skill)

### Permissions
```python
from agenticai_sdk.auth.permissions import (
    PERMISSION_SKILL_READ,
    PERMISSION_SKILL_WRITE,
    PERMISSION_SKILL_EXECUTE,
    PERMISSION_SKILL_DELETE,
    PERMISSION_SKILL_UPLOAD,
    PERMISSION_SKILL_SYNC,
)
```

### Default Policy Updates
- **Editor**: Can read skills, denied create/update/delete/execute
- **Viewer**: Can read skills only
- **Admin**: Full access to all skill operations
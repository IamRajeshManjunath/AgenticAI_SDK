# AgenticAI SDK v0.3 - Getting Started Guide

## Overview

AgenticAI SDK is a self-hosted, plugin-agnostic orchestration engine for building AI agents. It provides:

- **50+ Chat Model Integrations** - OpenAI, Anthropic, Google, AWS, Groq, Mistral, and more
- **20+ Tools & Toolkits** - Tavily, Composio (500+ tools), Exa, Google Search
- **Purpose-Bound Database Architecture** - Strict schema enforcement for 7 database purposes
- **RAG Pipeline** - Complete retrieval-augmented generation stack
- **Security & Governance** - IAM, API key scoping, compliance policies, audit logs
- **Observability** - Traces, costs, health monitoring, real-time dashboards
- **Modern Frontend** - Next.js/React UI for configuration and monitoring

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL (for checkpointer/store)
- Redis (for cache/rate_limit)
- Qdrant/Pinecone (for vector_store)
- Node.js 18+ (for frontend)

### Installation

```bash
# Clone repository
git clone https://github.com/yourorg/agenticai-sdk
cd agenticai-sdk

# Install Python SDK
pip install -e .

# Install with all integrations
pip install -e ".[all]"

# Or install specific integration groups
pip install -e ".[openai,anthropic,groq,qdrant,postgresql]"

# Install skills support (deepagents, watchdog)
pip install -e ".[skills]"
```

### Configuration

Create `agenticai.yaml`:

```yaml
platform:
  default_chat_model: "gpt4"
  default_embedding: "openai"
  enable_telemetry: true
  enable_cost_tracking: true
  enable_skills: true
  skills:
    skills_dir: "skills"
    deep_agent_model: "anthropic:claude-sonnet-4-6"
    auto_discover: true
    watch_for_changes: true
    remote_sources: []

chat_models:
  gpt4:
    type: "openai"
    provider: "openai"
    model: "gpt-4o"
    api_key_env: "OPENAI_API_KEY"
    temperature: 0.7
    features:
      stream: true
      tools: true
      structured_output: true

database_routes:
  primary_vector:
    purpose: "vector_store"
    provider: "qdrant"
    config:
      url: "http://localhost:6333"
      collection: "documents"
    schema_contract:
      purpose: "vector_store"
      collections:
        documents:
          columns:
            vector:
              type: "vector"
              dimension: 1536
            content:
              type: "text"
            metadata:
              type: "json"

  langgraph_checkpointer:
    purpose: "checkpointer"
    provider: "postgresql"
    config:
      connectionString: "postgresql://user:pass@localhost:5432/langgraph"
    schema_contract:
      purpose: "checkpointer"
      tables:
        checkpoints: "langgraph_standard"
        checkpoint_blobs: "langgraph_standard"
        checkpoint_writes: "langgraph_standard"

tools:
  tavily:
    api_key_env: "TAVILY_API_KEY"
    max_results: 5

features:
  rag_enabled: true
  observability_enabled: true
  governance_enabled: true
```

Set environment variables:
```bash
export OPENAI_API_KEY="sk-..."
export TAVILY_API_KEY="tvly-..."
```

### Basic Usage

```python
from agenticai_sdk.config.loader import load_config
from agenticai_sdk.plugins import get_global_registry
from agenticai_sdk.db.factory import DynamicDatabaseFactory
from agenticai_sdk.rag.factories import RAGPipeline
from agenticai_sdk.skills import get_skills_registry, create_agentic_deep_agent
from pathlib import Path

# 1. Load configuration
config = load_config("agenticai.yaml")

# 2. Initialize plugin registry
registry = get_global_registry()
registry.load_entry_points()

# 3. Initialize skills registry
skills_registry = get_skills_registry(config.platform.skills, Path.cwd())
skills_registry.initialize()

# 3. Create chat model
llm = registry.create_instance("chat_model", "openai", config=config.chat_models["gpt4"].model_dump())

# 4. Create database connections
factory = DynamicDatabaseFactory()
vector_store = factory.create_vector_store(config.database_routes["primary_vector"])
checkpointer = factory.create_checkpointer(config.database_routes["langgraph_checkpointer"])

# 5. Build RAG pipeline
from agenticai_sdk.rag.factories import (
    EmbeddingFactory, VectorStoreFactory, RetrieverFactory
)

embeddings = EmbeddingFactory.create("openai", config={"model": "text-embedding-3-large"})
retriever = RetrieverFactory.create("similarity", vector_store=vector_store, k=5)

pipeline = RAGPipeline(
    embeddings=embeddings,
    vector_store=vector_store,
    retriever=retriever,
)

# 6. Index documents
await pipeline.aindex_documents(["docs/guide.pdf", "docs/api.md"])

# 7. Query
result = await pipeline.aquery("How do I configure database routes?")
print(result.answer)

# 8. Create Deep Agent with Skills
from agenticai_sdk.skills import create_agentic_deep_agent

agent = create_agentic_deep_agent(
    config=config,
    project_root=Path.cwd(),
    model="anthropic:claude-sonnet-4-6",
)
```

```
## Skills Quick Start

### Using Built-in Skills

The SDK includes 7 built-in skills in the `skills/` directory:

```python
from agenticai_sdk.skills import get_skills_registry

# Initialize and list skills
skills_registry = get_skills_registry(config.platform.skills, Path.cwd())
skills = skills_registry.initialize()

for skill in skills_registry.list_skills():
    print(f"{skill.name}: {skill.description}")

# Get skill for deepagents
sources = skills_registry.get_deepagents_sources()
# Returns paths like ['skills/web-research', 'skills/code-generation', ...]

# Use with deepagents
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[...],
    skills=sources,  # Pass skill directory paths
)

result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Research the latest AI trends and write a summary"}]
})
```

The agent will automatically load skill descriptions at startup and read full skill content when needed (progressive disclosure).

### Creating Custom Skills

Create a skill directory with `SKILL.md`:

```bash
mkdir -p skills/my-custom-skill/scripts
```

Create `skills/my-custom-skill/SKILL.md`:

```markdown
---
name: my-custom-skill
description: Custom skill for processing customer feedback
license: MIT
compatibility: Requires Python 3.11+
metadata:
  author: my-team
  version: "1.0"
allowed_tools: PythonREPL TavilySearch
---

# My Custom Skill

## Overview
Process and categorize customer feedback from multiple sources.

## Instructions

### 1. Fetch Feedback
Use Tavily to search for recent feedback or load from database.

### 2. Categorize
Classify feedback into: bug, feature-request, praise, question.

### 3. Prioritize
Score by impact, frequency, and sentiment.

### 4. Report
Generate summary with top themes and action items.
```

Add supporting scripts in `scripts/`:
```python
# skills/my-custom-skill/scripts/analyze.py
def analyze_feedback(feedback_list):
    # Your analysis logic
    return categorized_results
```

The skill will be auto-discovered on startup (or use the frontend at `/skills/new`).

### Using Skills in Deep Agents

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="anthropic:claude-sonnet-4-6",
    tools=[tavily, python_repl],
    skills=["skills/web-research", "skills/code-generation", "skills/my-custom-skill"],
)

result = await agent.ainvoke({
    "messages": [{"role": "user", "content": "Research the latest AI trends and write a summary"}]
})
```

The agent will automatically load skill descriptions at startup and read full skill content when needed (progressive disclosure).

## Frontend Setup

```bash
cd Frontend
npm install
npm run dev
```

Access at `http://localhost:3000` - redirects to `/dashboard`

### Frontend Pages
- `/dashboard` - Overview with stats, quick actions, system health
- `/integrations` - Plugin marketplace (browse, install, configure)
- `/skills` - Skills Dashboard (browse, create, edit, validate skills)
- `/settings/database-routes` - Database route wizard with schema validation
- `/observability` - Traces, costs, health, governance tabs
- `/governance` - Audit events, compliance policies, API keys, RBAC
- `/settings` - Profile, preferences, notifications, security
- `/activity` - Filterable activity log with export

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                      │
│  Dashboard | Integrations | Skills | DB Routes | Observ... │
└──────────────────────────┬──────────────────────────────────┘
                           │ REST API
┌──────────────────────────▼──────────────────────────────────┐
│                    Gateway API Routes                         │
│  /api/v1/integrations | /skills | /database-routes | ...  │
└──────────────────────────┬──────────────────────────────────┘
                           │ Python SDK
┌──────────────────────────▼──────────────────────────────────┐
│                      AgenticAI SDK Core                       │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐  │
│  │ Config  │ │ Plugins │ │  DB     │ │  RAG    │ │ Auth  │  │
│  │ Loader  │ │ Registry│ │ Factory │ │Pipeline │ │/IAM   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐  │
│  │Middleware│ │Backends │ │Sandboxes│ │Observab.│ │Gov.   │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘  │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────┐  │
│  │ Skills  │ │ DeepAg. │ │         │ │         │ │       │  │
│  │ Registry│ │ Integ.  │ │         │ │         │ │       │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └───────┘  │
└─────────────────────────────────────────────────────────────┘
         │              │              │              │
     ┌────▼────┐    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
     │Postgres │    │  Qdrant │    │  Redis  │    │  LLMs   │
     │(Checkpt/│    │ (Vector)│    │(Cache/  │    │(25+     │
     │ Store)  │    │         │    │ RateLmt)│    │ providers)│
     └─────────┘    └─────────┘    └─────────┘    └─────────┘
```

## Key Concepts

### Purpose-Bound Databases
Each database route is strictly bound to a purpose. You cannot use a vector_store route as a checkpointer.

```python
# This works
vector_store = factory.create_vector_store(vector_route_config)

# This raises ValidationError
checkpointer = factory.create_checkpointer(vector_route_config)  # ERROR!
```

### JSON-First Runtime Config
Frontend sends JSON overrides that merge with YAML defaults:

```json
// Frontend sends at runtime
{
  "chat_models": {
    "gpt4": {
      "model": "gpt-4o-mini",
      "temperature": 0.5
    }
  }
}
```

### Plugin Discovery
Plugins auto-discover via PyPI entry points:

```toml
# pyproject.toml
[project.entry-points."agenticai.plugins"]
openai = "agenticai_sdk.integrations.plugins.openai:OpenAIPlugin"
anthropic = "agenticai_sdk.integrations.plugins.anthropic:AnthropicPlugin"
# ... 40+ more
```

## Next Steps

1. [API Reference](../api/reference.md) - Complete API documentation
2. [Configuration Guide](configuration.md) - Advanced config options
3. [Plugin Development](plugins.md) - Build custom integrations
4. [Deployment Guide](deployment.md) - Production deployment
5. [Security Guide](security.md) - IAM, encryption, compliance
# Database Schemas — Full System Inventory

> Complete reference of every data store, table, column, and relationship used by the AgenticAI SDK platform.

---

## Table of Contents

1. [Primary Database (PostgreSQL / SQLite)](#1-primary-database-postgresql--sqlite)
   - [workspaces](#workspaces)
   - [users](#users)
   - [workspace_members](#workspace_members)
   - [api_keys](#api_keys)
   - [plans](#plans)
   - [policies](#policies)
   - [policy_attachments](#policy_attachments)
   - [workflows](#workflows)
   - [tools](#tools)
   - [rag_sources](#rag_sources)
   - [secrets](#secrets)
   - [activity_logs](#activity_logs)
   - [workflow_traces](#workflow_traces)
   - [schema_audit_trails](#schema_audit_trails)
   - [cron_jobs](#cron_jobs)
   - [integration_connections](#integration_connections)
   - [billing_data](#billing_data)
   - [skills](#skills)
   - [skill_files](#skill_files)
   - [skill_versions](#skill_versions)
2. [Redis (Rate Limiter)](#2-redis-rate-limiter)
3. [Prometheus (In-Process Metrics)](#3-prometheus-in-process-metrics)
4. [File-Based DB Config Persistence](#4-file-based-db-config-persistence)
5. [Environment Variables](#5-environment-variables)

---

## 1. Primary Database (PostgreSQL / SQLite)

**Driver**: SQLAlchemy (`agenticai_sdk/db/database.py`)  
**Production**: PostgreSQL 16 via docker-compose  
**Development**: SQLite fallback (`sqlite:///agenticai.db` — zero config)  
**Connection resolution order**:
1. Explicit `--db-url` CLI argument
2. `.agenticai_db_config` file (persisted from a previous session)
3. `AGENTICAI_DB_URL` environment variable
4. SQLite fallback (`sqlite:///agenticai.db`)

**Total tables**: 20

---

### `workspaces`

Multi-tenant workspace isolation. Each user gets a workspace on registration; members are invited into workspaces.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `name` | `VARCHAR` | index | Display name, set during registration |
| `description` | `VARCHAR` | nullable | Free-text description |
| `owner_id` | `VARCHAR` | FK → `users.id`, ON DELETE SET NULL | The user who created the workspace |
| `plan_id` | `VARCHAR` | FK → `plans.id`, ON DELETE SET NULL | Current subscription plan |
| `stripe_customer_id` | `VARCHAR` | nullable | Stripe customer reference |
| `stripe_subscription_id` | `VARCHAR` | nullable | Stripe subscription reference |
| `subscription_status` | `VARCHAR` | default `'inactive'` | `active`, `past_due`, `canceled`, `inactive` |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | onupdate `now()` | |

**Relationships**:
- `owner` → `users` (one-to-one, via `owner_id`)
- `plan` → `plans` (many-to-one, via `plan_id`)
- `workflows` → `workflows` (one-to-many, cascade delete)
- `members` → `workspace_members` (one-to-many)
- `api_keys` → `api_keys` (one-to-many)
- `tools` → `tools` (one-to-many)
- `rag_sources` → `rag_sources` (one-to-many)
- `secrets` → `secrets` (one-to-many)

---

### `users`

User accounts. Created at registration; must exist before being invited to a workspace.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `email` | `VARCHAR` | **UNIQUE**, index, NOT NULL | Login identifier |
| `hashed_password` | `VARCHAR` | NOT NULL | bcrypt hash (via passlib) |
| `full_name` | `VARCHAR` | nullable | Display name |
| `is_active` | `INTEGER` | default `1` | Boolean — soft disable |
| `is_superuser` | `INTEGER` | default `0` | Cross-workspace admin |
| `default_workspace_id` | `VARCHAR` | FK → `workspaces.id`, ON DELETE SET NULL | Primary workspace context |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | onupdate `now()` | |

**Relationships**:
- `owned_workspaces` → `workspaces` (one-to-many, via `owner_id`)
- `memberships` → `workspace_members` (one-to-many)

---

### `workspace_members`

Many-to-many join table linking users to workspaces with an RBAC role. Composite primary key.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `workspace_id` | `VARCHAR` | **PK**, FK → `workspaces.id`, ON DELETE CASCADE | |
| `user_id` | `VARCHAR` | **PK**, FK → `users.id`, ON DELETE CASCADE | |
| `role` | `VARCHAR` | NOT NULL, default `'editor'` | One of: `admin`, `editor`, `viewer` |
| `invited_by` | `VARCHAR` | FK → `users.id`, ON DELETE SET NULL | Who added this member |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

**Role → IAM mapping**:
| Role | Policy ID | Effect |
|------|-----------|--------|
| `admin` | `policy_admin` | Allow `*` (unrestricted) |
| `editor` | `policy_editor` | Allow `*`, Deny 16 sensitive actions |
| `viewer` | `policy_viewer` | Allow 18 read-only actions |

---

### `api_keys`

API key storage for programmatic access. Two key types determined by `workflow_id`:
- **`agk_<hex>`** — workspace key (`workflow_id IS NULL`), full workspace access via `require_permission()`
- **`wfk_<hex>`** — workflow-scoped key (`workflow_id IS SET`), scoped to a single workflow

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `workspace_id` | `VARCHAR` | FK → `workspaces.id`, ON DELETE CASCADE, NOT NULL | Owning workspace |
| `workflow_id` | `VARCHAR` | FK → `workflows.id`, ON DELETE CASCADE, nullable, index | `NULL` = workspace key |
| `key_prefix` | `VARCHAR` | NOT NULL | First 12 chars of raw key (visible in UI) |
| `key_hash` | `VARCHAR` | NOT NULL | bcrypt hash of full raw key |
| `name` | `VARCHAR` | NOT NULL | Human-readable label |
| `is_active` | `INTEGER` | default `1` | Soft-delete / deactivate |
| `last_used_at` | `TIMESTAMPTZ` | nullable | Updated on every auth |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

**Auth flow** (`gateway/auth_middleware.py`):
1. `X-API-Key: <raw_key>` header received
2. Iterates all active keys, `pwd_context.verify(raw_key, key_hash)`
3. On match: sets `request.state.workspace_id`, `request.state.auth_method = "api_key"`
4. If `workflow_id` is set, also sets `request.state.workflow_key_scope`

**Unique constraint per workflow**: Only one active (`is_active = 1`) key per `workflow_id` at a time — generating a new key deactivates the old one.

---

### `plans`

Subscription plan definitions. Seeded manually (no seed data currently — needs pre-population before billing re-enable).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | |
| `name` | `VARCHAR` | NOT NULL | e.g. `"Free"`, `"Pro"`, `"Enterprise"` |
| `stripe_price_id` | `VARCHAR` | nullable | Stripe Price ID for checkout |
| `tokens_per_month` | `INTEGER` | default `100000` | Monthly token allowance |
| `max_workflows` | `INTEGER` | default `5` | Max concurrent workflows |
| `max_api_keys` | `INTEGER` | default `2` | Max API keys per workspace |
| `max_team_members` | `INTEGER` | default `1` | Max workspace members |
| `features` | `JSON` | default `{}` | Feature flag object |
| `price_cents` | `INTEGER` | default `0` | Price in cents (USD) |
| `is_active` | `BOOLEAN` | default `True` | Soft-disable a plan |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

### `policies`

IAM policy documents — the authorization rule definitions. Analogous to AWS IAM policies.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | e.g. `"policy_admin"` |
| `name` | `VARCHAR` | NOT NULL | Display name |
| `description` | `VARCHAR` | nullable | Human-readable purpose |
| `policy_document` | `JSON` | NOT NULL | See format below |
| `is_system` | `INTEGER` | default `0` | System policies cannot be deleted via API |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

**Policy document format**:
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

**Default seeded policies** (`db/database.py:_seed_default_policies`):
| ID | Name | Effect |
|----|------|--------|
| `policy_admin` | Admin Policy | Allow `*` |
| `policy_editor` | Editor Policy | Allow `*`, Deny 16 sensitive (member:remove, billing:*, cron:*, db:reset, secret:read-value, admin:*, etc.) |
| `policy_viewer` | Viewer Policy | Allow 18 read-only (workflow:read, tool:read, rag:read, observability:read, etc.) |

**Evaluation engine** (`auth/permissions.py`):
1. Explicit `Deny` → **Deny** (short-circuits)
2. Explicit `Allow` → **Allow**
3. No match → **Deny** (implicit deny)

Actions and resources support wildcard glob patterns: `workflow:*`, `wf:abc-*`.

---

### `policy_attachments`

Binds a policy to a principal (user, role, or workspace). Many-to-many join.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `policy_id` | `VARCHAR` | FK → `policies.id`, ON DELETE CASCADE, index, NOT NULL | |
| `principal_type` | `VARCHAR` | index, NOT NULL | One of: `"user"`, `"role"`, `"workspace"` |
| `principal_id` | `VARCHAR` | index, NOT NULL | User UUID / role name (`"admin"`) / workspace UUID |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

**Resolution at runtime**:
1. Get user's role from `workspace_members`
2. Query `policy_attachments` WHERE `principal_type = 'role' AND principal_id = '<role>'`
3. Also query `principal_type = 'user' AND principal_id = '<user_id>'` (user-specific overrides)
4. Union all matched `policy_document` JSON blobs
5. Evaluate against requested action

---

### `workflows`

Persisted workflow definitions. Created via the SaaS CRUD API or the Master Agent compile flow.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | |
| `workspace_id` | `VARCHAR` | FK → `workspaces.id`, ON DELETE CASCADE | |
| `name` | `VARCHAR` | index | Display name |
| `description` | `VARCHAR` | nullable | Free-text |
| `config` | `JSON` | nullable | Full `WorkflowSchema` JSON |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | onupdate `now()` | |

**Relationships**:
- `workspace` → `workspaces` (many-to-one)
- `api_keys` → `api_keys` (one-to-many — workflow-scoped keys)

---

### `tools`

Registered tool metadata. Tools can be custom Python code, MCP endpoints, or built-in system tools.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | |
| `workspace_id` | `VARCHAR` | FK → `workspaces.id`, ON DELETE CASCADE, nullable | `NULL` for global/system tools |
| `name` | `VARCHAR` | index | Tool name (referenced in WorkflowSchema) |
| `description` | `VARCHAR` | nullable | |
| `tool_type` | `VARCHAR` | | `"mcp"`, `"custom_python"`, `"system"` |
| `code_or_url` | `VARCHAR` | | Python code string or MCP endpoint URL |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

### `rag_sources`

RAG (Retrieval-Augmented Generation) source configurations.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | |
| `workspace_id` | `VARCHAR` | FK → `workspaces.id`, ON DELETE CASCADE, nullable | |
| `name` | `VARCHAR` | index | Display name |
| `provider` | `VARCHAR` | default `"qdrant"` | `qdrant`, `pinecone`, `pgvector`, `chromadb`, `faiss`, `universal` |
| `config` | `JSON` | default `{}` | Provider-specific connection config |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

### `activity_logs`

Immutable audit trail for all workspace mutations. Written by `_log_activity()` helper used across all route handlers.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `workspace_id` | `VARCHAR` | index, nullable | |
| `workflow_id` | `VARCHAR` | index, nullable | |
| `event_type` | `VARCHAR` | | e.g. `"workflow.created"`, `"tool.deleted"` |
| `details` | `JSON` | | Arbitrary context: `{resource_type, resource_id, resource_name, ...}` |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

**Event types emitted**:
- `workflow.created`, `workflow.updated`, `workflow.deleted`, `workflow.master_compiled`
- `tool.created`, `tool.deleted`
- `workspace.deleted`

---

### `workflow_traces`

Deep execution observability. Written by the OpenTelemetry bridge after each workflow run.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | |
| `workflow_id` | `VARCHAR` | FK → `workflows.id`, ON DELETE CASCADE, index | |
| `trace_id` | `VARCHAR` | index | OpenTelemetry trace ID |
| `duration_ms` | `FLOAT` | | Total execution time |
| `total_tokens` | `INTEGER` | | Sum of all LLM tokens used |
| `cost_usd` | `FLOAT` | | Estimated cost |
| `error_count` | `INTEGER` | | Number of errors encountered |
| `span_tree` | `JSON` | | Full serialized trace tree with span hierarchy |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

### `schema_audit_trails`

Immutable IO payload audit log. Records every data payload entering and exiting agent nodes, along with the schema it was validated against.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | |
| `agent_id` | `VARCHAR` | index | Agent node ID |
| `direction` | `VARCHAR` | | `"incoming"` or `"outgoing"` |
| `payload` | `JSON` | | The exact data that was validated |
| `schema_definition` | `JSON` | | The schema used for validation |
| `is_valid` | `INTEGER` | | `1` = valid, `0` = violation |
| `violation_error` | `VARCHAR` | nullable | Description of schema violation |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

### `cron_jobs`

Scheduled job definitions with lease-based distributed locking. Avoids duplicate execution in multi-instance deployments.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | |
| `cron_expression` | `VARCHAR` | NOT NULL | Standard cron syntax, e.g. `"*/5 * * * *"` |
| `target_type` | `VARCHAR` | NOT NULL | `"agent"` or `"workflow"` |
| `target_id` | `VARCHAR` | NOT NULL | The workflow_id or agent_id to execute |
| `payload` | `JSON` | nullable | Input state for execution |
| `last_run_at` | `TIMESTAMPTZ` | nullable | Timestamp of last execution |
| `next_run_at` | `TIMESTAMPTZ` | index, NOT NULL | Computed from cron expression |
| `status` | `VARCHAR` | default `"active"` | `"active"`, `"paused"`, `"terminated"` |
| `locked_by` | `VARCHAR` | nullable | Instance name holding the execution lease |
| `locked_until` | `TIMESTAMPTZ` | nullable | Lease expiration timestamp |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

### `integration_connections`

External service connection store for third-party integrations (Slack, Teams, Outlook, WhatsApp).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | Convention: `"{workspace_id}:{integration_type}"` |
| `workspace_id` | `VARCHAR` | index, NOT NULL | |
| `integration_type` | `VARCHAR` | NOT NULL | `"slack"`, `"outlook"`, `"teams"`, `"whatsapp"` |
| `name` | `VARCHAR` | NOT NULL | Human label |
| `auth_state` | `JSON` | NOT NULL | Encrypted credentials: `{webhook_url, access_token, ...}` |
| `rate_limits` | `JSON` | nullable | `{max_calls_per_minute: 60}` |
| `is_active` | `INTEGER` | default `1` | `1` = active, `0` = disconnected |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | onupdate `now()` | |

---

### `secrets`

Encrypted secret storage. Values are Fernet-encrypted at rest and decrypted on-demand for users with the `secret:read-value` permission.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `workspace_id` | `VARCHAR` | FK → `workspaces.id`, ON DELETE CASCADE, index, NOT NULL | Workspace scope |
| `name` | `VARCHAR` | index, NOT NULL | Human-readable name (e.g. `OPENAI_API_KEY`) |
| `encrypted_value` | `VARCHAR` | NOT NULL | Fernet-encrypted ciphertext (base64 token) |
| `description` | `VARCHAR` | nullable | Free-text description |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | onupdate `now()` | |

**Relationships**:
- `workspace` → `workspaces` (many-to-one)

**Encryption details**:
- Algorithm: Fernet (AES-128-CBC + HMAC-SHA256, authenticated encryption)
- Key derivation: `base64(SHA256(secret_key))` where `secret_key` = `SECRETS_ENCRYPTION_KEY` env var, or falls back to `SECRET_KEY`
- Module: `agenticai_sdk/auth/secrets.py`

---

### `billing_data`

Per-workspace billing records. Written by Stripe webhook handlers when Stripe is configured.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `INTEGER` | **PK**, index, AUTOINCREMENT | |
| `workspace_id` | `VARCHAR` | index | |
| `amount` | `FLOAT` | | Amount charged |
| `currency` | `VARCHAR` | default `"USD"` | |
| `period_start` | `TIMESTAMPTZ` | | Billing period start |
| `period_end` | `TIMESTAMPTZ` | | Billing period end |
| `metrics` | `JSON` | | Usage breakdown: `{tokens: 5000, ...}` |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

### `skills`

Registered skill metadata for the Deep Agents Skills system. Each skill is a file-based capability with a SKILL.md file.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `workspace_id` | `VARCHAR` | FK → `workspaces.id`, ON DELETE CASCADE, NOT NULL | Workspace scope |
| `name` | `VARCHAR` | index, NOT NULL | Skill name (lowercase, hyphens) |
| `description` | `TEXT` | nullable | Human-readable description |
| `source` | `VARCHAR` | NOT NULL | `local`, `git`, `s3`, `fleet` |
| `path` | `VARCHAR` | NOT NULL | Path to skill directory |
| `frontmatter` | `JSON` | NOT NULL | Parsed YAML frontmatter from SKILL.md |
| `content` | `TEXT` | nullable | Full markdown content |
| `source_url` | `VARCHAR` | nullable | Remote source URL (git repo, S3 bucket) |
| `source_branch` | `VARCHAR` | nullable | Git branch for remote sources |
| `source_path` | `VARCHAR` | nullable | Path within remote source |
| `is_active` | `INTEGER` | default `1` | Soft-delete / deactivate |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | onupdate `now()` | |

**Relationships**:
- `workspace` → `workspaces` (many-to-one)
- `files` → `skill_files` (one-to-many)
- `versions` → `skill_versions` (one-to-many)

---

### `skill_files`

Supporting files for skills (scripts, references, assets, templates).

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `skill_id` | `VARCHAR` | FK → `skills.id`, ON DELETE CASCADE, NOT NULL | Parent skill |
| `path` | `VARCHAR` | NOT NULL | Relative path from skill root |
| `content` | `TEXT` | NOT NULL | File content |
| `type` | `VARCHAR` | NOT NULL | `script`, `reference`, `asset`, `template` |
| `size_bytes` | `INTEGER` | default `0` | File size in bytes |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |
| `updated_at` | `TIMESTAMPTZ` | onupdate `now()` | |

---

### `skill_versions`

Version history for skills to support rollback and audit.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` | `VARCHAR` | **PK**, index | UUID v4 |
| `skill_id` | `VARCHAR` | FK → `skills.id`, ON DELETE CASCADE, NOT NULL | Parent skill |
| `version` | `VARCHAR` | NOT NULL | Semantic version (e.g., "1.0.0") |
| `frontmatter` | `JSON` | NOT NULL | Frontmatter at this version |
| `content` | `TEXT` | nullable | Content at this version |
| `files` | `JSON` | nullable | Supporting files at this version |
| `created_by` | `VARCHAR` | FK → `users.id`, ON DELETE SET NULL | User who created version |
| `created_at` | `TIMESTAMPTZ` | server_default `now()` | |

---

## 2. Redis (Rate Limiter)

**Purpose**: Distributed sliding-window rate limiting across multiple API instances  
**Config**: `REDIS_URL` env var (e.g. `redis://redis:6379/0`)  
**Module**: `agenticai_sdk/middleware/rate_limiter.py`  
**Fallback**: In-memory `defaultdict[list[float]]` token bucket when Redis is unavailable

### Data structure

| Key | Type | TTL | Value |
|-----|------|-----|-------|
| `ratelimit:{target_id}` | String (counter) | 60s | Incremented integer count |

**Target IDs**: `"global"`, or per-workflow/per-agent IDs.  
**Behavior**:
1. `INCR ratelimit:{target_id}`
2. If `== 1`: `EXPIRE ratelimit:{target_id} 60`
3. If `> max_requests_per_minute`: raise `PermissionError`

---

## 3. Prometheus (In-Process Metrics)

**Purpose**: Real-time performance telemetry — latency, token usage, error rates  
**Library**: `prometheus_client` Python library  
**Module**: `agenticai_sdk/middleware/prometheus_metrics.py`  
**Exposed at**: `GET /metrics` (Prometheus text format)  
**Volatility**: All metrics are in-memory and reset on process restart

### Metrics catalog

| Metric Name | Type | Labels | Description |
|-------------|------|--------|-------------|
| `workflow_runs_total` | Counter | `status` (`success`/`error`) | Total workflow executions |
| `workflow_duration_seconds` | Histogram | (buckets: 0.1, 0.5, 1, 2, 5, 10, 30, 60, 120) | Execution duration |
| `llm_calls_total` | Counter | `provider`, `model` | Total LLM invocations |
| `llm_tokens_total` | Counter | `provider`, `type` (`prompt`/`completion`) | Token consumption |
| `cost_usd_total` | Counter | `provider` | Accumulated cost |
| `rag_queries_total` | Counter | `provider`, `status` | RAG retrieval calls |
| `middleware_actions_total` | Counter | `middleware`, `action` | Middleware events |
| `active_executions` | Gauge | — | Currently executing workflows |

**Export format** (`evaluation/metrics.py:export_prometheus`):
```
# HELP workflow_runs_total Total workflow executions
# TYPE workflow_runs_total counter
workflow_runs_total{status="success"} 42
workflow_runs_total{status="error"} 3
```

---

## 4. File-Based DB Config Persistence

**File**: `.agenticai_db_config` in the application working directory  
**Format**: JSON  
**Purpose**: Persists the database connection URL between restarts — "connect once, persist forever"

```json
{
  "core_db_url": "postgresql://agenticai:password@postgres:5432/agenticai",
  "routing_map": {
    "workflow_traces": "clickhouse://user:pass@analytics-cluster:8123/default",
    "schema_audit_trails": "postgresql://user:pass@audit-db:5432/security"
  }
}
```

**Read/written by**: `agenticai_sdk/db/database.py`
- `_save_config()` — persists after successful `POST /db/connect`
- `_load_config()` — loads at startup
- `_clear_config()` — clears on `POST /db/reset`

---

## 5. Environment Variables

| Variable | Used By | Purpose | Default |
|----------|---------|---------|---------|
| `AGENTICAI_DB_URL` | `db/database.py` | Primary database connection string | `sqlite:///agenticai.db` |
| `SECRET_KEY` | `auth/dependencies.py`, `gateway/auth_middleware.py` | JWT signing/verification | `"dev-secret-key-change-in-production"` |
| `REDIS_URL` | `middleware/rate_limiter.py` | Redis connection for distributed rate limiting | (unset → in-memory fallback) |
| `STRIPE_SECRET_KEY` | `gateway/routes/billing.py` | Stripe API authentication | (unset → billing returns 503) |
| `STRIPE_WEBHOOK_SECRET` | `gateway/routes/billing.py` | Stripe webhook signature verification | (unset → webhook is no-op) |
| `DOMAIN` | `gateway/routes/billing.py` | Frontend domain for billing portal redirects | `http://localhost:3000` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `auth/router.py`, `gateway/routes/auth.py` | JWT token lifetime | `10080` (7 days) |
| `LOG_LEVEL` | `gateway/app.py` | Logging verbosity | `INFO` |
| `SECRETS_ENCRYPTION_KEY` | `auth/secrets.py` | Fernet key for encrypting secret values | Derived from `SECRET_KEY` via SHA-256 |

---

## Entity Relationship Summary

```
users ──┬── workspaces (owner)
        └── workspace_members ── workspaces
                │
                └── role ──→ policy_attachments ── policies

workspaces ──┬── workflows ──┬── workflow_traces
             │               └── api_keys (wfk_)
             ├── api_keys (agk_)
             ├── tools
             ├── rag_sources
             ├── activity_logs
             ├── billing_data
             ├── integration_connections
             ├── secrets
             ├── plans
             └── skills ──┬── skill_files
                          └── skill_versions

cron_jobs ──→ workflows (target)

schema_audit_trails (standalone, referenced by agent_id)
```

---

## Docker Compose Infrastructure

From `docker-compose.yml`:

| Service | Image | Port | Data Volume | Purpose |
|---------|-------|------|-------------|---------|
| `postgres` | postgres:16-alpine | 5432 | `pgdata` | Primary database (20 tables) |
| `redis` | redis:7-alpine | 6379 | `redisdata` | Rate limiter backend |
| `prometheus` | prom/prometheus:latest | 9090 | `promdata` | Metrics scraping (15d retention) |
| `grafana` | grafana/grafana:latest | 3000 | `grafanadata` | Metrics dashboards |
| `api` | (Dockerfile build) | 8000 | `agenticai_data` | FastAPI gateway |

# AgenticAI SDK API Reference

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication

### API Key
```http
Authorization: Bearer akai_xxxxxxxxxxxx
```

### JWT Token
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

## Endpoints

### System

#### GET /health
Basic health check.

**Response:**
```json
{
  "status": "healthy",
  "service": "agenticai-sdk",
  "version": "0.3.0",
  "database": {
    "status": "connected",
    "provider": "postgresql",
    "latency_ms": 5
  }
}
```

#### GET /health/live
Kubernetes liveness probe.

**Response:**
```json
{"status": "alive", "service": "agenticai-sdk"}
```

#### GET /health/ready
Kubernetes readiness probe.

**Response:**
```json
{
  "status": "ready",
  "service": "agenticai-sdk",
  "database": {"status": "connected", "provider": "postgresql"},
  "redis": {"status": "connected"}
}
```

### Workflow Execution

#### POST /api/v1/workflow/run
Execute a workflow.

**Request:**
```json
{
  "workflow": "basic_qa",
  "input": {"question": "What is...?"},
  "workflow_id": "optional-custom-id",
  "thread_id": "optional-thread-id",
  "scratchpad": {}
}
```

**Response:**
```json
{
  "workflow_id": "uuid",
  "thread_id": "uuid",
  "status": "completed",
  "output": {"answer": "..."},
  "cost_usd": 0.001,
  "tokens_used": 150,
  "latency_ms": 1200
}
```

#### GET /api/v1/workflow/run/{workflow_id}
Get workflow run status.

#### POST /api/v1/workflow/hitl/approve
Approve or reject a HITL request.

**Request:**
```json
{
  "approval_id": "uuid",
  "approved": true,
  "feedback": "Optional feedback"
}
```

### Observability

#### GET /api/v1/observability/traces
List recent traces.

**Query Parameters:**
- `limit` (default: 20)

#### GET /api/v1/observability/traces/{trace_id}
Get trace detail.

#### GET /api/v1/observability/metrics
Current metrics summary.

#### GET /api/v1/observability/metrics/prometheus
Prometheus-format metrics export.

#### GET /api/v1/observability/evaluations/{workflow_id}
Quality evaluations for workflow.

#### GET /api/v1/observability/health
Extended health with components.

### Configuration

#### GET /api/v1/config
Get current configuration.

#### PATCH /api/v1/config
Update configuration (JSON Merge Patch).

**Request:**
```json
{
  "chat_models": {
    "primary": {"temperature": 0.5}
  }
}
```

#### GET /api/v1/config/history
Get configuration revision history.

#### POST /api/v1/config/rollback
Rollback to previous revision.

### Skills

#### GET /api/v1/skills
List available skills.

#### GET /api/v1/skills/{skill_name}
Get skill details.

#### POST /api/v1/skills/validate
Validate SKILL.md file.

#### POST /api/v1/skills/reload
Trigger skill reload.

#### GET /api/v1/skills/pipelines
List registered pipelines.

#### POST /api/v1/skills/pipelines
Register a pipeline.

#### POST /api/v1/skills/pipelines/{name}/execute
Execute a pipeline.

### Integrations

#### GET /api/v1/integrations
List available integrations.

#### POST /api/v1/integrations/connect
Connect an integration.

#### DELETE /api/v1/integrations/{integration_id}
Disconnect integration.

#### POST /api/v1/integrations/{integration_id}/test
Test integration connection.

## Error Responses

All errors follow RFC 7807 format:

```json
{
  "type": "https://agenticai.io/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "Invalid workflow input",
  "instance": "/api/v1/workflow/run",
  "errors": [
    {"field": "workflow", "message": "Workflow not found"}
  ]
}
```

Common error types:
- `validation-error` (422)
- `not-found` (404)
- `unauthorized` (401)
- `forbidden` (403)
- `rate-limited` (429)
- `budget-exceeded` (429)
- `timeout` (408)
- `internal-error` (500)

## Rate Limits

- Default: 60 requests/minute per API key
- Workflow execution: 10 concurrent per workspace
- Config updates: 5/minute

## Webhooks

### Workflow Completed
```json
{
  "event": "workflow.completed",
  "timestamp": "2024-01-15T10:30:00Z",
  "workflow_id": "uuid",
  "status": "completed",
  "output": {...}
}
```

### HITL Required
```json
{
  "event": "hitl.required",
  "timestamp": "2024-01-15T10:30:00Z",
  "approval_id": "uuid",
  "workflow_id": "uuid",
  "request": {...}
}
```
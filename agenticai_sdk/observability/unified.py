"""Unified telemetry for platform + all integrations."""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from opentelemetry import trace, metrics
from opentelemetry.trace import Status, StatusCode

import structlog

logger = structlog.get_logger(__name__)


class UnifiedTelemetry:
    """Single telemetry interface for platform + all integrations."""

    def __init__(self, workspace_id: str = "default"):
        self.workspace_id = workspace_id
        self.tracer = trace.get_tracer("agenticai.unified")
        self.meter = metrics.get_meter("agenticai.unified")
        
        # Platform metrics
        self.workflow_runs = self.meter.create_counter(
            "workflow.runs.total",
            description="Total workflow executions",
        )
        self.workflow_duration = self.meter.create_histogram(
            "workflow.duration.ms",
            description="Workflow execution duration in milliseconds",
        )
        self.workflow_errors = self.meter.create_counter(
            "workflow.errors.total",
            description="Total workflow errors",
        )
        
        # Integration metrics
        self.integration_calls = self.meter.create_counter(
            "integration.calls.total",
            description="Total integration calls",
        )
        self.integration_latency = self.meter.create_histogram(
            "integration.latency.ms",
            description="Integration call latency in milliseconds",
        )
        self.integration_errors = self.meter.create_counter(
            "integration.errors.total",
            description="Total integration errors",
        )
        
        # Token/Cost metrics
        self.token_usage = self.meter.create_counter(
            "tokens.used.total",
            description="Total tokens used",
        )
        self.cost_usd = self.meter.create_counter(
            "cost.usd.total",
            description="Total cost in USD",
        )
        
        # Database metrics
        self.db_queries = self.meter.create_counter(
            "db.queries.total",
            description="Total database queries",
        )
        self.db_latency = self.meter.create_histogram(
            "db.latency.ms",
            description="Database query latency in milliseconds",
        )
    
    @contextmanager
    def trace_workflow(self, workflow_id: str, workflow_name: str):
        """Trace a workflow execution."""
        with self.tracer.start_as_current_span(f"workflow.{workflow_name}") as span:
            span.set_attribute("workspace_id", self.workspace_id)
            span.set_attribute("workflow_id", workflow_id)
            span.set_attribute("workflow_name", workflow_name)
            start = time.perf_counter()
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                self.workflow_errors.add(1, {"workflow_id": workflow_id, "error": type(e).__name__})
                raise
            finally:
                duration_ms = (time.perf_counter() - start) * 1000
                self.workflow_duration.record(duration_ms, {"workflow_id": workflow_id})
                self.workflow_runs.add(1, {"workflow_id": workflow_id})
    
    @contextmanager
    def trace_integration(self, integration_type: str, provider: str, operation: str):
        """Trace an integration call."""
        with self.tracer.start_as_current_span(f"{integration_type}.{provider}.{operation}") as span:
            span.set_attribute("workspace_id", self.workspace_id)
            span.set_attribute("integration_type", integration_type)
            span.set_attribute("provider", provider)
            span.set_attribute("operation", operation)
            start = time.perf_counter()
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                self.integration_errors.add(1, {"integration_type": integration_type, "provider": provider, "error": type(e).__name__})
                raise
            finally:
                latency_ms = (time.perf_counter() - start) * 1000
                self.integration_latency.record(latency_ms, {"integration_type": integration_type, "provider": provider})
                self.integration_calls.add(1, {"integration_type": integration_type, "provider": provider})
    
    @contextmanager
    def trace_db(self, operation: str, table: str):
        """Trace a database operation."""
        with self.tracer.start_as_current_span(f"db.{operation}") as span:
            span.set_attribute("workspace_id", self.workspace_id)
            span.set_attribute("db.operation", operation)
            span.set_attribute("db.table", table)
            start = time.perf_counter()
            try:
                yield span
            except Exception as e:
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise
            finally:
                latency_ms = (time.perf_counter() - start) * 1000
                self.db_latency.record(latency_ms, {"operation": operation, "table": table})
                self.db_queries.add(1, {"operation": operation, "table": table})
    
    def record_tokens(self, model: str, provider: str, input_tokens: int, output_tokens: int, cost_usd: float):
        """Record token usage and cost."""
        self.token_usage.add(input_tokens + output_tokens, {"model": model, "provider": provider, "direction": "input"})
        self.token_usage.add(output_tokens, {"model": model, "provider": provider, "direction": "output"})
        self.cost_usd.add(cost_usd, {"model": model, "provider": provider})
    
    def record_workflow_run(self, workflow_id: str, workflow_name: str, status: str, duration_ms: float, tokens: int = 0, cost_usd: float = 0.0):
        """Record a workflow run summary."""
        self.workflow_runs.add(1, {"workflow_id": workflow_id, "status": status})
        self.workflow_duration.record(duration_ms, {"workflow_id": workflow_id})
        if tokens > 0:
            self.token_usage.add(tokens, {"workflow_id": workflow_id})
        if cost_usd > 0:
            self.cost_usd.add(cost_usd, {"workflow_id": workflow_id})


class CostGovernance:
    """Tracks token usage, costs, and enforces budget limits per workspace."""

    def __init__(self, workspace_id: str = "default", db_session=None):
        self.workspace_id = workspace_id
        self.db = db_session
    
    async def track_usage(self, usage_record: Dict[str, Any]):
        """Record usage and check against budget limits."""
        # Record to platform DB for billing
        # Check against workspace budget limits
        # Trigger alerts at 80%, 95%, 100%
        # Enforce hard limits if configured
        pass
    
    async def get_cost_breakdown(self, period: str = "month") -> Dict[str, Any]:
        """Returns cost breakdown by integration, workflow, user, model."""
        return {
            "by_integration": {},
            "by_workflow": {},
            "by_user": {},
            "by_model": {},
            "total_usd": 0.0,
            "period": period,
        }
    
    async def check_budget_alerts(self) -> List[Dict[str, Any]]:
        """Check for budget threshold crossings (80%, 95%, 100%)."""
        return []


class HealthMonitor:
    """Health monitoring for all integrations and platform components."""

    def __init__(self, workspace_id: str = "default", db_session=None):
        self.workspace_id = workspace_id
        self.db = db_session
    
    async def check_all(self) -> Dict[str, Any]:
        """Run comprehensive health checks."""
        results = {
            "platform": await self._check_platform(),
            "integrations": await self._check_integrations(),
            "databases": await self._check_databases(),
            "overall": "healthy",
        }
        
        # Determine overall status
        if any(r.get("status") == "error" for r in results.values() if isinstance(r, dict)):
            results["overall"] = "degraded"
        elif any(r.get("status") == "degraded" for r in results.values() if isinstance(r, dict)):
            results["overall"] = "degraded"
        
        return results
    
    async def _check_platform(self) -> Dict[str, Any]:
        """Check platform health."""
        return {"status": "healthy", "components": {}}
    
    async def _check_integrations(self) -> Dict[str, Any]:
        """Check all configured integrations."""
        from agenticai_sdk.plugins import get_global_registry, IntegrationType
        
        registry = get_global_registry()
        results = {}
        
        for int_type in [IntegrationType.CHAT_MODEL, IntegrationType.TOOL, IntegrationType.VECTOR_STORE]:
            plugins = registry.list_available(int_type)
            for plugin in plugins:
                # Would run actual health check here
                results[f"{int_type.value}:{plugin.provider}"] = {"status": "healthy"}
        
        return results
    
    async def _check_databases(self) -> Dict[str, Any]:
        """Check all configured database routes."""
        # Would check each database route
        return {"status": "healthy", "routes": {}}


class GovernanceEventTracker:
    """Track governance events for audit and compliance."""
    
    def __init__(self, workspace_id: str, db_session):
        self.workspace_id = workspace_id
        self.db = db_session
    
    async def record_event(
        self,
        event_category: str,
        event_type: str,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        severity: str = "info",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Record a governance event."""
        from agenticai_sdk.db.models import GovernanceEvent
        import uuid
        
        event = GovernanceEvent(
            id=str(uuid.uuid4()),
            workspace_id=self.workspace_id,
            user_id=user_id,
            event_category=event_category,
            event_type=event_type,
            severity=severity,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(event)
        self.db.commit()
    
    async def get_audit_log(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get filtered audit log entries."""
        from agenticai_sdk.db.models import GovernanceEvent
        from sqlalchemy import desc
        
        query = self.db.query(GovernanceEvent).filter(
            GovernanceEvent.workspace_id == self.workspace_id
        ).order_by(desc(GovernanceEvent.created_at))
        
        if filters:
            if "event_category" in filters:
                query = query.filter(GovernanceEvent.event_category == filters["event_category"])
            if "event_type" in filters:
                query = query.filter(GovernanceEvent.event_type == filters["event_type"])
            if "user_id" in filters:
                query = query.filter(GovernanceEvent.user_id == filters["user_id"])
            if "severity" in filters:
                query = query.filter(GovernanceEvent.severity == filters["severity"])
            if "start_date" in filters:
                query = query.filter(GovernanceEvent.created_at >= filters["start_date"])
            if "end_date" in filters:
                query = query.filter(GovernanceEvent.created_at <= filters["end_date"])
        
        events = query.offset(offset).limit(limit).all()
        return [e.__dict__ for e in events]


class ComplianceManager:
    """Manage compliance policies for data retention, encryption, access control."""
    
    def __init__(self, workspace_id: str, db_session):
        self.workspace_id = workspace_id
        self.db = db_session
    
    async def get_policies(self) -> List[Dict[str, Any]]:
        """Get all compliance policies for workspace."""
        from agenticai_sdk.db.models import CompliancePolicy
        policies = self.db.query(CompliancePolicy).filter(
            CompliancePolicy.workspace_id == self.workspace_id,
            CompliancePolicy.is_active == 1
        ).all()
        return [p.__dict__ for p in policies]
    
    async def create_policy(
        self,
        policy_type: str,
        config: Dict[str, Any],
    ) -> Any:
        """Create a new compliance policy."""
        from agenticai_sdk.db.models import CompliancePolicy
        import uuid
        
        policy = CompliancePolicy(
            id=str(uuid.uuid4()),
            workspace_id=self.workspace_id,
            policy_type=policy_type,
            config=config,
            is_active=1,
        )
        self.db.add(policy)
        self.db.commit()
        return policy
    
    async def check_compliance(self) -> Dict[str, Any]:
        """Run compliance checks against policies."""
        policies = await self.get_policies()
        results = {"compliant": True, "violations": []}
        
        for policy in policies:
            # Would implement specific compliance checks
            pass
        
        return results
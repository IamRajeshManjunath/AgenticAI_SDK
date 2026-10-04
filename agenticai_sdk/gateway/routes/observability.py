"""
Observability Dashboard API — FastAPI routes for traces, metrics,
evaluations, and detailed health checks.

Endpoints:
  GET /api/v1/observability/traces              — List recent traces
  GET /api/v1/observability/traces/{trace_id}   — Full trace detail
  GET /api/v1/observability/metrics             — Current metrics summary
  GET /api/v1/observability/metrics/prometheus  — Prometheus-format export
  GET /api/v1/observability/evaluations/{workflow_id} — Quality evaluations
  GET /api/v1/observability/health              — Extended health with components
"""

from __future__ import annotations

import math
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import User, WorkflowJob, WorkflowTrace
from agenticai_sdk.evaluation.metrics import MetricsSummary
from sqlalchemy.orm import Session

logger = structlog.get_logger(__name__)

observability_router = APIRouter(
    prefix="/api/v1/observability",
    tags=["observability"],
)


class TraceListResponse(BaseModel):
    traces: list[dict[str, Any]] = Field(default_factory=list)
    total: int = 0


class HealthDetailResponse(BaseModel):
    status: str = "healthy"
    version: str = "0.2.0"
    components: dict[str, dict[str, Any]] = Field(default_factory=dict)
    active_traces: int = 0
    metrics_summary: dict[str, Any] = Field(default_factory=dict)


@observability_router.get("/traces", response_model=TraceListResponse)
async def list_traces(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("observability:read")),
) -> TraceListResponse:
    workspace_id = _workspace_id(request)
    rows = (
        db.query(WorkflowTrace)
        .filter(WorkflowTrace.workspace_id == workspace_id)
        .order_by(WorkflowTrace.created_at.desc())
        .limit(limit)
        .all()
    )
    traces = [_trace_summary(row) for row in rows]
    return TraceListResponse(traces=traces, total=len(traces))


@observability_router.get("/traces/{trace_id}")
async def get_trace(
    trace_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("observability:read")),
) -> dict[str, Any]:
    row = db.query(WorkflowTrace).filter(
        WorkflowTrace.trace_id == trace_id,
        WorkflowTrace.workspace_id == _workspace_id(request),
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Trace '{trace_id}' not found.")
    return {
        **_trace_summary(row),
        "span_tree": row.span_tree,
        "total_tokens": row.total_tokens or 0,
        "total_cost_usd": row.cost_usd or 0.0,
        "error_count": row.error_count or 0,
    }


@observability_router.get("/metrics", response_model=MetricsSummary)
async def get_metrics(
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("observability:read")),
) -> MetricsSummary:
    rows = _workspace_traces(db, _workspace_id(request))
    durations = sorted(row.duration_ms or 0.0 for row in rows)
    return MetricsSummary(
        total_requests=len(rows),
        total_tokens=sum(row.total_tokens or 0 for row in rows),
        total_cost_usd=round(sum(row.cost_usd or 0.0 for row in rows), 6),
        total_errors=sum(row.error_count or 0 for row in rows),
        avg_latency_ms=round(sum(durations) / len(durations), 2) if durations else 0.0,
        p95_latency_ms=_percentile(durations, 0.95),
        p99_latency_ms=_percentile(durations, 0.99),
    )


@observability_router.get("/metrics/prometheus")
async def get_prometheus_metrics(
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("observability:read")),
) -> Any:
    from starlette.responses import PlainTextResponse
    rows = _workspace_traces(db, _workspace_id(request))
    total_tokens = sum(row.total_tokens or 0 for row in rows)
    total_cost = sum(row.cost_usd or 0.0 for row in rows)
    text = (
        "# HELP agenticai_workflow_runs_total Persisted workflow runs for the selected workspace.\n"
        "# TYPE agenticai_workflow_runs_total counter\n"
        f"agenticai_workflow_runs_total {len(rows)}\n"
        "# HELP agenticai_workflow_tokens_total Persisted workflow token usage.\n"
        "# TYPE agenticai_workflow_tokens_total counter\n"
        f"agenticai_workflow_tokens_total {total_tokens}\n"
        "# HELP agenticai_workflow_cost_usd_total Persisted workflow cost in USD.\n"
        "# TYPE agenticai_workflow_cost_usd_total counter\n"
        f"agenticai_workflow_cost_usd_total {total_cost}\n"
    )
    return PlainTextResponse(content=text, media_type="text/plain; version=0.0.4")


@observability_router.get("/evaluations/{workflow_id}")
async def get_evaluations(
    workflow_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("observability:read")),
) -> dict[str, Any]:
    from agenticai_sdk.evaluation.evaluators import WorkflowEvaluator
    from agenticai_sdk.evaluation.trace_collector import TraceReport

    rows = db.query(WorkflowTrace).filter(
        WorkflowTrace.workspace_id == _workspace_id(request),
        WorkflowTrace.workflow_id == workflow_id,
    ).order_by(WorkflowTrace.created_at.desc()).limit(100).all()
    matching = [
        TraceReport(
            trace_id=row.trace_id,
            workflow_id=row.workflow_id or "",
            total_duration_ms=row.duration_ms or 0.0,
            total_tokens=row.total_tokens or 0,
            total_cost_usd=row.cost_usd or 0.0,
            error_count=row.error_count or 0,
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
        for row in rows
    ]
    if not matching:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No traces found for workflow '{workflow_id}'.")
    evaluator = WorkflowEvaluator()
    evaluations = []
    for report in matching:
        result = evaluator.evaluate_workflow_run(report)
        evaluations.append(result.model_dump())
    return {"workflow_id": workflow_id, "evaluation_count": len(evaluations), "evaluations": evaluations}


@observability_router.get("/health", response_model=HealthDetailResponse)
async def health_detailed(
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("observability:read")),
) -> HealthDetailResponse:
    workspace_id = _workspace_id(request)
    rows = _workspace_traces(db, workspace_id)
    durations = sorted(row.duration_ms or 0.0 for row in rows)
    total_errors = sum(row.error_count or 0 for row in rows)
    total_requests = len(rows)
    queue_counts = {
        job_status: db.query(WorkflowJob).filter(
            WorkflowJob.workspace_id == workspace_id,
            WorkflowJob.status == job_status,
        ).count()
        for job_status in ("pending", "running", "failed")
    }
    components: dict[str, dict[str, Any]] = {
        "persisted_traces": {"status": "healthy", "count": total_requests},
        "workflow_queue": {"status": "healthy", **queue_counts},
    }
    overall_status = "healthy"
    if total_errors > 0 and total_requests > 0:
        error_rate = total_errors / total_requests
        if error_rate > 0.5:
            overall_status = "degraded"
    return HealthDetailResponse(
        status=overall_status,
        components=components,
        active_traces=queue_counts["running"],
        metrics_summary={
            "total_requests": total_requests,
            "total_tokens": sum(row.total_tokens or 0 for row in rows),
            "total_cost_usd": round(sum(row.cost_usd or 0.0 for row in rows), 6),
            "avg_latency_ms": round(sum(durations) / len(durations), 2) if durations else 0.0,
        },
    )


def _workspace_id(request: Request) -> str:
    workspace_id = getattr(request.state, "workspace_id", None)
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No workspace context found")
    return workspace_id


def _workspace_traces(db: Session, workspace_id: str) -> list[WorkflowTrace]:
    return db.query(WorkflowTrace).filter(WorkflowTrace.workspace_id == workspace_id).all()


def _trace_summary(row: WorkflowTrace) -> dict[str, Any]:
    created_at = row.created_at.isoformat() if row.created_at else None
    span_tree = row.span_tree or {}
    run_status = span_tree.get("status", "completed") if isinstance(span_tree, dict) else "completed"
    return {
        "trace_id": row.trace_id,
        "workflow_id": row.workflow_id,
        "workflow_name": row.workflow_id,
        "status": "failed" if (row.error_count or 0) else run_status,
        "total_cost": row.cost_usd or 0.0,
        "total_tokens": row.total_tokens or 0,
        "latency_ms": row.duration_ms or 0.0,
        "started_at": created_at,
        "completed_at": created_at,
    }


def _percentile(sorted_values: list[float], quantile: float) -> float:
    if not sorted_values:
        return 0.0
    index = max(0, math.ceil(quantile * len(sorted_values)) - 1)
    return round(sorted_values[index], 2)

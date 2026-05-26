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

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from agenticai_sdk.evaluation.metrics import MetricsRegistry, MetricsSummary
from agenticai_sdk.evaluation.trace_collector import TraceCollector, TraceReport

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
async def list_traces(request: Request, limit: int = 20) -> TraceListResponse:
    collector = TraceCollector()
    reports = collector.get_recent_reports(limit=limit)
    traces = []
    for report in reports:
        traces.append({
            "trace_id": report.trace_id,
            "workflow_id": report.workflow_id,
            "thread_id": report.thread_id,
            "total_duration_ms": report.total_duration_ms,
            "total_tokens": report.total_tokens,
            "total_cost_usd": report.total_cost_usd,
            "error_count": report.error_count,
            "span_count": report.span_count,
            "created_at": report.created_at,
        })
    return TraceListResponse(traces=traces, total=len(traces))


@observability_router.get("/traces/{trace_id}")
async def get_trace(trace_id: str, request: Request) -> dict[str, Any]:
    collector = TraceCollector()
    report = collector.get_report_by_id(trace_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Trace '{trace_id}' not found.")
    return report.model_dump()


@observability_router.get("/metrics", response_model=MetricsSummary)
async def get_metrics(request: Request) -> MetricsSummary:
    registry = MetricsRegistry()
    return registry.get_summary()


@observability_router.get("/metrics/prometheus")
async def get_prometheus_metrics(request: Request) -> Any:
    from starlette.responses import PlainTextResponse
    registry = MetricsRegistry()
    text = registry.export_prometheus()
    return PlainTextResponse(content=text, media_type="text/plain; version=0.0.4")


@observability_router.get("/evaluations/{workflow_id}")
async def get_evaluations(workflow_id: str, request: Request) -> dict[str, Any]:
    from agenticai_sdk.evaluation.evaluators import WorkflowEvaluator
    collector = TraceCollector()
    reports = collector.get_recent_reports(limit=100)
    matching = [r for r in reports if r.workflow_id == workflow_id]
    if not matching:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No traces found for workflow '{workflow_id}'.")
    evaluator = WorkflowEvaluator()
    evaluations = []
    for report in matching:
        result = evaluator.evaluate_workflow_run(report)
        evaluations.append(result.model_dump())
    return {"workflow_id": workflow_id, "evaluation_count": len(evaluations), "evaluations": evaluations}


@observability_router.get("/health", response_model=HealthDetailResponse)
async def health_detailed(request: Request) -> HealthDetailResponse:
    collector = TraceCollector()
    registry = MetricsRegistry()
    summary = registry.get_summary()
    components: dict[str, dict[str, Any]] = {
        "trace_collector": {"status": "healthy", "active_traces": collector.active_trace_count},
        "metrics_registry": {"status": "healthy", "total_requests": summary.total_requests, "uptime_seconds": summary.uptime_seconds},
        "middleware_pipeline": {"status": "healthy", "events_recorded": sum(summary.middleware_events.values())},
        "orchestrator": {"status": "healthy", "total_errors": summary.total_errors},
    }
    overall_status = "healthy"
    if summary.total_errors > 0 and summary.total_requests > 0:
        error_rate = summary.total_errors / summary.total_requests
        if error_rate > 0.5:
            overall_status = "degraded"
    return HealthDetailResponse(
        status=overall_status,
        components=components,
        active_traces=collector.active_trace_count,
        metrics_summary={
            "total_requests": summary.total_requests,
            "total_tokens": summary.total_tokens,
            "total_cost_usd": summary.total_cost_usd,
            "avg_latency_ms": summary.avg_latency_ms,
        },
    )

"""
Distributed Trace Collector — captures hierarchical span trees for every
workflow execution, agent node, tool call, middleware pass, and RAG retrieval.

Provides a singleton collector that builds structured trace reports with
timing, token counts, costs, and error attribution.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# ── Trace models ─────────────────────────────────────────────────────────────


class TraceSpan(BaseModel):
    """A single span in the trace tree.

    Attributes:
        span_id: Unique span identifier.
        parent_id: ID of the parent span (None for root).
        name: Human-readable span name.
        span_type: Category (workflow, agent, tool, middleware, rag).
        start_time: Epoch timestamp when the span started.
        end_time: Epoch timestamp when the span ended (None if still running).
        duration_ms: Computed duration in milliseconds.
        metadata: Arbitrary key-value metadata.
        error: Error message if the span failed.
        children: Nested child spans.
    """

    span_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    parent_id: str | None = None
    name: str = ""
    span_type: str = "generic"
    start_time: float = 0.0
    end_time: float | None = None
    duration_ms: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    children: list["TraceSpan"] = Field(default_factory=list)


class TraceReport(BaseModel):
    """Complete trace report for a workflow execution.

    Attributes:
        trace_id: Unique trace identifier.
        workflow_id: ID of the executed workflow.
        thread_id: Session thread ID.
        root_span: The root span of the trace tree.
        total_duration_ms: Total wall-clock duration.
        total_tokens: Aggregate token count across all spans.
        total_cost_usd: Aggregate estimated cost.
        error_count: Number of spans that recorded errors.
        span_count: Total number of spans in the tree.
        created_at: ISO timestamp when the trace was created.
    """

    trace_id: str
    workflow_id: str = ""
    thread_id: str = ""
    root_span: TraceSpan | None = None
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    error_count: int = 0
    span_count: int = 0
    created_at: str = ""


class TraceContext:
    """Mutable context for building a trace during execution."""

    def __init__(self, trace_id: str, workflow_id: str = "", thread_id: str = "") -> None:
        self.trace_id = trace_id
        self.workflow_id = workflow_id
        self.thread_id = thread_id
        self._spans: dict[str, TraceSpan] = {}
        self._root_span_id: str | None = None
        self._start_time = time.perf_counter()
        
        # OTel dictionary to keep track of active OTel spans alongside our SQL spans
        self._otel_spans = {}
        try:
            from opentelemetry import trace
            self._tracer = trace.get_tracer(__name__)
        except ImportError:
            self._tracer = None

    def add_span(self, name: str, span_type: str = "generic",
                 parent_id: str | None = None, metadata: dict | None = None) -> str:
        """Add a new span to the trace."""
        span = TraceSpan(
            parent_id=parent_id or self._root_span_id,
            name=name,
            span_type=span_type,
            start_time=time.perf_counter(),
            metadata=metadata or {},
        )
        self._spans[span.span_id] = span

        if self._root_span_id is None:
            self._root_span_id = span.span_id

        # Start OTel Span
        if self._tracer:
            # We don't have explicit context propagation here, so we just start a span
            otel_span = self._tracer.start_span(name)
            otel_span.set_attribute("span_type", span_type)
            otel_span.set_attribute("trace_id", self.trace_id)
            for k, v in (metadata or {}).items():
                otel_span.set_attribute(f"meta.{k}", str(v))
            self._otel_spans[span.span_id] = otel_span

        return span.span_id

    def end_span(self, span_id: str, result: dict | None = None, error: str | None = None) -> None:
        """Close a span with result and timing."""
        if span_id not in self._spans:
            return
        span = self._spans[span_id]
        span.end_time = time.perf_counter()
        span.duration_ms = round((span.end_time - span.start_time) * 1000, 2)
        span.error = error
        if result:
            span.metadata.update(result)

        # End OTel Span
        if span_id in self._otel_spans:
            otel_span = self._otel_spans.pop(span_id)
            if error:
                try:
                    from opentelemetry.trace.status import Status, StatusCode
                    otel_span.set_status(Status(StatusCode.ERROR, description=error))
                except ImportError:
                    pass
            for k, v in (result or {}).items():
                otel_span.set_attribute(f"result.{k}", str(v))
            otel_span.end()

    def build_report(self) -> TraceReport:
        """Build the final trace report with computed aggregates."""
        root = self._build_tree()
        total_duration = round((time.perf_counter() - self._start_time) * 1000, 2)

        total_tokens = 0
        total_cost = 0.0
        error_count = 0

        for span in self._spans.values():
            total_tokens += span.metadata.get("tokens", 0)
            total_cost += span.metadata.get("cost_usd", 0.0)
            if span.error:
                error_count += 1

        return TraceReport(
            trace_id=self.trace_id,
            workflow_id=self.workflow_id,
            thread_id=self.thread_id,
            root_span=root,
            total_duration_ms=total_duration,
            total_tokens=total_tokens,
            total_cost_usd=round(total_cost, 6),
            error_count=error_count,
            span_count=len(self._spans),
            created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )

    def _build_tree(self) -> TraceSpan | None:
        """Assemble spans into a parent-child tree."""
        if not self._spans:
            return None

        # Build children relationships
        for span in self._spans.values():
            if span.parent_id and span.parent_id in self._spans:
                parent = self._spans[span.parent_id]
                if span not in parent.children:
                    parent.children.append(span)

        if self._root_span_id and self._root_span_id in self._spans:
            return self._spans[self._root_span_id]

        # Fallback: return first span
        return next(iter(self._spans.values())) if self._spans else None


# ── Singleton Trace Collector ────────────────────────────────────────────────


class TraceCollector:
    """Singleton trace collector managing multiple concurrent traces.

    Usage::

        collector = TraceCollector()
        ctx = collector.start_trace("wf-123", "thread-456")
        span_id = ctx.add_span("agent_execution", "agent", metadata={...})
        ctx.end_span(span_id, result={"tokens": 500})
        report = collector.end_trace(ctx.trace_id)
    """

    _instance: TraceCollector | None = None
    _traces: dict[str, TraceContext] = {}
    _completed_reports: list[TraceReport] = []
    _max_completed: int = 100

    def __new__(cls) -> TraceCollector:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._traces = {}
            cls._completed_reports = []
        return cls._instance

    def start_trace(self, workflow_id: str = "", thread_id: str = "") -> TraceContext:
        """Create a new trace context."""
        trace_id = f"trace_{uuid.uuid4().hex[:12]}"
        ctx = TraceContext(trace_id=trace_id, workflow_id=workflow_id, thread_id=thread_id)
        self._traces[trace_id] = ctx

        logger.debug("trace_started", trace_id=trace_id, workflow_id=workflow_id)
        return ctx

    def get_trace(self, trace_id: str) -> TraceContext | None:
        """Retrieve an active trace context."""
        return self._traces.get(trace_id)

    def end_trace(self, trace_id: str) -> TraceReport | None:
        """Finalize a trace and generate the report."""
        ctx = self._traces.pop(trace_id, None)
        if ctx is None:
            return None

        report = ctx.build_report()

        # Store completed report (with bounded size)
        self._completed_reports.append(report)
        if len(self._completed_reports) > self._max_completed:
            self._completed_reports = self._completed_reports[-self._max_completed:]

        logger.info(
            "trace_completed",
            trace_id=trace_id,
            duration_ms=report.total_duration_ms,
            span_count=report.span_count,
            error_count=report.error_count,
        )

        return report

    def get_recent_reports(self, limit: int = 20) -> list[TraceReport]:
        """Return the most recent completed trace reports."""
        return list(reversed(self._completed_reports[-limit:]))

    def get_report_by_id(self, trace_id: str) -> TraceReport | None:
        """Find a completed report by trace ID."""
        for report in self._completed_reports:
            if report.trace_id == trace_id:
                return report
        return None

    @property
    def active_trace_count(self) -> int:
        """Number of currently active traces."""
        return len(self._traces)

    def reset(self) -> None:
        """Reset all traces and reports (for testing)."""
        self._traces.clear()
        self._completed_reports.clear()

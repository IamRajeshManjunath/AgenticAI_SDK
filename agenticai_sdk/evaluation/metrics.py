"""
Metrics Registry — aggregates latency, token usage, cost, error counts,
and middleware events across the entire SDK runtime.

Supports export to Prometheus exposition format and structured JSON summaries.
"""

from __future__ import annotations

import time
import threading
from typing import Any

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class LatencyRecord(BaseModel):
    """A single latency observation."""
    component: str
    operation: str
    duration_ms: float
    timestamp: float


class MetricsSummary(BaseModel):
    """Aggregated metrics snapshot.

    Attributes:
        total_requests: Total workflow executions.
        total_tokens: Aggregate token usage.
        total_cost_usd: Aggregate estimated cost.
        total_errors: Total error count.
        avg_latency_ms: Average latency across all operations.
        p95_latency_ms: 95th percentile latency.
        p99_latency_ms: 99th percentile latency.
        tokens_by_agent: Token breakdown per agent.
        costs_by_provider: Cost breakdown per LLM provider.
        errors_by_type: Error count breakdown per error type.
        middleware_events: Middleware event summaries.
        uptime_seconds: Time since metrics collection started.
    """

    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_errors: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    tokens_by_agent: dict[str, int] = Field(default_factory=dict)
    costs_by_provider: dict[str, float] = Field(default_factory=dict)
    errors_by_type: dict[str, int] = Field(default_factory=dict)
    middleware_events: dict[str, int] = Field(default_factory=dict)
    uptime_seconds: float = 0.0


class MetricsRegistry:
    """Thread-safe metrics aggregation registry.

    Collects and aggregates runtime metrics across all SDK components.
    Supports JSON summary export and Prometheus text format.

    Usage::

        registry = MetricsRegistry()
        registry.record_latency("orchestrator", "compile", 150.3)
        registry.record_tokens("researcher", 1200, 800, "gpt-4o")
        summary = registry.get_summary()
    """

    _instance: MetricsRegistry | None = None

    def __new__(cls) -> MetricsRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self) -> None:
        """Initialize internal state."""
        self._lock = threading.Lock()
        self._start_time = time.perf_counter()
        self._latencies: list[LatencyRecord] = []
        self._total_requests = 0
        self._total_tokens = 0
        self._total_cost = 0.0
        self._total_errors = 0
        self._tokens_by_agent: dict[str, int] = {}
        self._costs_by_provider: dict[str, float] = {}
        self._errors_by_type: dict[str, int] = {}
        self._middleware_events: dict[str, int] = {}

    def record_request(self) -> None:
        """Increment the total request counter."""
        with self._lock:
            self._total_requests += 1

    def record_latency(self, component: str, operation: str, duration_ms: float) -> None:
        """Record a latency observation.

        Args:
            component: Component name (e.g., "orchestrator", "deep_agent").
            operation: Operation name (e.g., "compile", "invoke").
            duration_ms: Duration in milliseconds.
        """
        with self._lock:
            self._latencies.append(LatencyRecord(
                component=component,
                operation=operation,
                duration_ms=duration_ms,
                timestamp=time.perf_counter(),
            ))
            # Keep bounded
            if len(self._latencies) > 10000:
                self._latencies = self._latencies[-5000:]

    def record_tokens(self, agent_id: str, prompt_tokens: int,
                      completion_tokens: int, model: str = "") -> None:
        """Record token usage for an agent invocation.

        Args:
            agent_id: Agent node identifier.
            prompt_tokens: Input tokens consumed.
            completion_tokens: Output tokens generated.
            model: Model name (for logging).
        """
        total = prompt_tokens + completion_tokens
        with self._lock:
            self._total_tokens += total
            self._tokens_by_agent[agent_id] = (
                self._tokens_by_agent.get(agent_id, 0) + total
            )

    def record_cost(self, agent_id: str, cost_usd: float, provider: str = "") -> None:
        """Record estimated cost for an LLM invocation.

        Args:
            agent_id: Agent node identifier.
            cost_usd: Estimated cost in USD.
            provider: LLM provider name.
        """
        with self._lock:
            self._total_cost += cost_usd
            if provider:
                self._costs_by_provider[provider] = (
                    self._costs_by_provider.get(provider, 0.0) + cost_usd
                )

    def record_error(self, component: str, error_type: str, error_msg: str = "") -> None:
        """Record an error event.

        Args:
            component: Component where the error occurred.
            error_type: Exception class name.
            error_msg: Error message (for logging).
        """
        with self._lock:
            self._total_errors += 1
            key = f"{component}:{error_type}"
            self._errors_by_type[key] = self._errors_by_type.get(key, 0) + 1

    def record_middleware_event(self, middleware_name: str, event_type: str,
                                details: dict[str, Any] | None = None) -> None:
        """Record a middleware-specific event.

        Args:
            middleware_name: Name of the middleware.
            event_type: Event category (e.g., "pii_masked", "injection_blocked").
            details: Optional event details.
        """
        with self._lock:
            key = f"{middleware_name}:{event_type}"
            self._middleware_events[key] = self._middleware_events.get(key, 0) + 1

    def get_summary(self) -> MetricsSummary:
        """Compute and return an aggregated metrics snapshot."""
        with self._lock:
            durations = [r.duration_ms for r in self._latencies]
            avg_latency = sum(durations) / len(durations) if durations else 0.0

            sorted_durations = sorted(durations)
            p95 = self._percentile(sorted_durations, 0.95)
            p99 = self._percentile(sorted_durations, 0.99)

            return MetricsSummary(
                total_requests=self._total_requests,
                total_tokens=self._total_tokens,
                total_cost_usd=round(self._total_cost, 6),
                total_errors=self._total_errors,
                avg_latency_ms=round(avg_latency, 2),
                p95_latency_ms=round(p95, 2),
                p99_latency_ms=round(p99, 2),
                tokens_by_agent=dict(self._tokens_by_agent),
                costs_by_provider={k: round(v, 6) for k, v in self._costs_by_provider.items()},
                errors_by_type=dict(self._errors_by_type),
                middleware_events=dict(self._middleware_events),
                uptime_seconds=round(time.perf_counter() - self._start_time, 2),
            )

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text exposition format."""
        summary = self.get_summary()
        lines: list[str] = [
            "# HELP agenticai_requests_total Total workflow execution requests.",
            "# TYPE agenticai_requests_total counter",
            f"agenticai_requests_total {summary.total_requests}",
            "",
            "# HELP agenticai_tokens_total Total tokens consumed.",
            "# TYPE agenticai_tokens_total counter",
            f"agenticai_tokens_total {summary.total_tokens}",
            "",
            "# HELP agenticai_cost_usd_total Total estimated cost in USD.",
            "# TYPE agenticai_cost_usd_total counter",
            f"agenticai_cost_usd_total {summary.total_cost_usd}",
            "",
            "# HELP agenticai_errors_total Total errors.",
            "# TYPE agenticai_errors_total counter",
            f"agenticai_errors_total {summary.total_errors}",
            "",
            "# HELP agenticai_latency_avg_ms Average latency in ms.",
            "# TYPE agenticai_latency_avg_ms gauge",
            f"agenticai_latency_avg_ms {summary.avg_latency_ms}",
            "",
            "# HELP agenticai_latency_p95_ms P95 latency in ms.",
            "# TYPE agenticai_latency_p95_ms gauge",
            f"agenticai_latency_p95_ms {summary.p95_latency_ms}",
            "",
            "# HELP agenticai_latency_p99_ms P99 latency in ms.",
            "# TYPE agenticai_latency_p99_ms gauge",
            f"agenticai_latency_p99_ms {summary.p99_latency_ms}",
            "",
            "# HELP agenticai_uptime_seconds SDK uptime in seconds.",
            "# TYPE agenticai_uptime_seconds gauge",
            f"agenticai_uptime_seconds {summary.uptime_seconds}",
        ]

        # Per-agent token metrics
        for agent_id, tokens in summary.tokens_by_agent.items():
            lines.append(f'agenticai_tokens_by_agent{{agent_id="{agent_id}"}} {tokens}')

        # Per-provider cost metrics
        for provider, cost in summary.costs_by_provider.items():
            lines.append(f'agenticai_cost_by_provider{{provider="{provider}"}} {cost}')

        # Error breakdown
        for error_key, count in summary.errors_by_type.items():
            lines.append(f'agenticai_errors_by_type{{type="{error_key}"}} {count}')

        # Middleware events
        for event_key, count in summary.middleware_events.items():
            lines.append(f'agenticai_middleware_events{{event="{event_key}"}} {count}')

        return "\n".join(lines) + "\n"

    @staticmethod
    def _percentile(sorted_data: list[float], p: float) -> float:
        """Compute the p-th percentile of sorted data."""
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * p
        f = int(k)
        c = f + 1
        if c >= len(sorted_data):
            return sorted_data[-1]
        d0 = sorted_data[f] * (c - k)
        d1 = sorted_data[c] * (k - f)
        return d0 + d1

    def reset(self) -> None:
        """Reset all metrics (for testing)."""
        self._init_state()

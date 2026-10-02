"""
OpenTelemetry GenAI Instrumentation — provides GenAI semantic conventions
for spans, metrics, and context propagation.

Implements OpenTelemetry GenAI Semantic Conventions:
- https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-spans.md
- https://github.com/open-telemetry/semantic-conventions/blob/main/docs/gen-ai/gen-ai-metrics.md
"""

from __future__ import annotations

import contextvars
import time
import uuid
from typing import Any, Optional

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.metrics import CallbackOptions, Observation, get_meter
from opentelemetry.propagate import extract, inject
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from opentelemetry.trace import SpanKind, Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = structlog.get_logger(__name__)

# Context variable for current trace context
_current_trace_context: contextvars.ContextVar[dict] = contextvars.ContextVar("_current_trace_context", default={})

# GenAI Semantic Convention Attributes (from OpenTelemetry GenAI Semantic Conventions)
GENAI_SYSTEM = "gen_ai.system"
GENAI_REQUEST_MODEL = "gen_ai.request.model"
GENAI_REQUEST_TEMPERATURE = "gen_ai.request.temperature"
GENAI_REQUEST_MAX_TOKENS = "gen_ai.request.max_tokens"
GENAI_REQUEST_TOP_P = "gen_ai.request.top_p"
GENAI_RESPONSE_MODEL = "gen_ai.response.model"
GENAI_RESPONSE_FINISH_REASON = "gen_ai.response.finish_reason"
GENAI_USAGE_INPUT_TOKENS = "gen_ai.usage.input_tokens"
GENAI_USAGE_OUTPUT_TOKENS = "gen_ai.usage.output_tokens"
GENAI_AGENT_ID = "gen_ai.agent.id"
GENAI_AGENT_NAME = "gen_ai.agent.name"
GENAI_TOOL_NAME = "gen_ai.tool.name"
GENAI_TOOL_CALL_ID = "gen_ai.tool.call_id"
GENAI_TOOL_PARAMETERS = "gen_ai.tool.parameters"
GENAI_OPERATION_NAME = "gen_ai.operation.name"
GENAI_ERROR_TYPE = "gen_ai.error.type"
GENAI_ERROR_MESSAGE = "gen_ai.error.message"


class GenAITracer:
    """Wrapper around OpenTelemetry tracer with GenAI semantic conventions."""

    def __init__(self, tracer_name: str = "agenticai"):
        self._tracer = trace.get_tracer(tracer_name)
        self._propagator = TraceContextTextMapPropagator()

    def start_gen_ai_span(
        self,
        name: str,
        system: str,
        model: str,
        operation: str = "chat",
        agent_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        metadata: Optional[dict] = None,
        parent_context: Optional[trace.Context] = None,
    ) -> trace.Span:
        """Start a span with GenAI semantic conventions."""
        span = self._tracer.start_span(
            name=name,
            kind=SpanKind.CLIENT,
            context=parent_context,
            attributes={
                GENAI_SYSTEM: system,
                GENAI_REQUEST_MODEL: model,
                GENAI_OPERATION_NAME: operation,
                GENAI_REQUEST_TEMPERATURE: temperature,
                GENAI_REQUEST_MAX_TOKENS: max_tokens,
                GENAI_REQUEST_TOP_P: top_p,
                GENAI_AGENT_ID: agent_id,
                GENAI_AGENT_NAME: agent_name,
                **(metadata or {}),
            },
        )
        return span

    def start_agent_span(
        self,
        agent_id: str,
        agent_name: str,
        model: str,
        system: str,
        temperature: Optional[float] = None,
        metadata: Optional[dict] = None,
        parent_context: Optional[trace.Context] = None,
    ) -> trace.Span:
        """Start a span for agent execution."""
        return self.start_gen_ai_span(
            name=f"agent.{agent_id}.execute",
            system=system,
            model=model,
            operation="agent_execution",
            agent_id=agent_id,
            agent_name=agent_name,
            temperature=temperature,
            metadata=metadata,
            parent_context=parent_context,
        )

    def start_llm_span(
        self,
        model: str,
        system: str,
        operation: str = "chat",
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        metadata: Optional[dict] = None,
        parent_context: Optional[trace.Context] = None,
    ) -> trace.Span:
        """Start a span for LLM inference."""
        return self.start_gen_ai_span(
            name=f"llm.{operation}",
            system=system,
            model=model,
            operation=operation,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            metadata=metadata,
            parent_context=parent_context,
        )

    def start_tool_span(
        self,
        tool_name: str,
        tool_call_id: str,
        parameters: dict,
        metadata: Optional[dict] = None,
        parent_context: Optional[trace.Context] = None,
    ) -> trace.Span:
        """Start a span for tool execution."""
        span = self._tracer.start_span(
            name=f"tool.{tool_name}",
            kind=SpanKind.CLIENT,
            context=parent_context,
            attributes={
                GENAI_TOOL_NAME: tool_name,
                GENAI_TOOL_CALL_ID: tool_call_id,
                GENAI_TOOL_PARAMETERS: str(parameters),
                **(metadata or {}),
            },
        )
        return span

    def start_middleware_span(
        self,
        middleware_name: str,
        agent_id: Optional[str] = None,
        metadata: Optional[dict] = None,
        parent_context: Optional[trace.Context] = None,
    ) -> trace.Span:
        """Start a span for middleware execution."""
        span = self._tracer.start_span(
            name=f"middleware.{middleware_name}",
            kind=SpanKind.INTERNAL,
            context=parent_context,
            attributes={
                "middleware.name": middleware_name,
                GENAI_AGENT_ID: agent_id,
                **(metadata or {}),
            },
        )
        return span

    def end_span(
        self,
        span: trace.Span,
        output_tokens: Optional[int] = None,
        input_tokens: Optional[int] = None,
        finish_reason: Optional[str] = None,
        response_model: Optional[str] = None,
        error: Optional[Exception] = None,
    ) -> None:
        """End a span with GenAI response attributes."""
        if output_tokens is not None:
            span.set_attribute(GENAI_USAGE_OUTPUT_TOKENS, output_tokens)
        if input_tokens is not None:
            span.set_attribute(GENAI_USAGE_INPUT_TOKENS, input_tokens)
        if finish_reason:
            span.set_attribute(GENAI_RESPONSE_FINISH_REASON, finish_reason)
        if response_model:
            span.set_attribute(GENAI_RESPONSE_MODEL, response_model)
        
        if error:
            span.set_status(Status(StatusCode.ERROR, str(error)))
            span.set_attribute(GENAI_ERROR_TYPE, type(error).__name__)
            span.set_attribute(GENAI_ERROR_MESSAGE, str(error))
        else:
            span.set_status(Status(StatusCode.OK))
        
        span.end()


class GenAIMetrics:
    """OpenTelemetry metrics with GenAI semantic conventions."""

    def __init__(self, meter_name: str = "agenticai"):
        self._meter = get_meter(meter_name)
        self._init_metrics()

    def _init_metrics(self) -> None:
        """Initialize GenAI metrics."""
        # Token usage metrics
        self._input_tokens = self._meter.create_counter(
            name="gen_ai.client.token.usage.input",
            unit="1",
            description="Number of input tokens consumed",
        )
        
        self._output_tokens = self._meter.create_counter(
            name="gen_ai.client.token.usage.output",
            unit="1",
            description="Number of output tokens generated",
        )
        
        # Latency metrics
        self._latency = self._meter.create_histogram(
            name="gen_ai.client.operation.duration",
            unit="ms",
            description="Duration of GenAI operations",
        )
        
        # Cost metrics
        self._cost = self._meter.create_counter(
            name="gen_ai.client.cost",
            unit="USD",
            description="Estimated cost of GenAI operations in USD",
        )
        
        # Error metrics
        self._errors = self._meter.create_counter(
            name="gen_ai.client.errors",
            unit="1",
            description="Number of GenAI operation errors",
        )
        
        # Active requests gauge
        self._active_requests = self._meter.create_up_down_counter(
            name="gen_ai.client.active_requests",
            unit="1",
            description="Number of active GenAI requests",
        )

    def record_llm_call(
        self,
        system: str,
        model: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        latency_ms: float,
        cost_usd: float,
        agent_id: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Record an LLM call with GenAI semantic conventions."""
        attributes = {
            "gen_ai.system": system,
            "gen_ai.request.model": model,
            "gen_ai.operation.name": operation,
        }
        
        if agent_id:
            attributes["gen_ai.agent.id"] = agent_id
        
        # Record metrics
        self._input_tokens.add(input_tokens, attributes)
        self._output_tokens.add(output_tokens, attributes)
        self._latency.record(latency_ms, attributes)
        self._cost.add(cost_usd, attributes)
        
        if error:
            self._errors.add(1, {**attributes, "error.type": type(error).__name__})

    def record_tool_call(
        self,
        tool_name: str,
        tool_call_id: str,
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record a tool call with GenAI semantic conventions."""
        attributes = {
            "gen_ai.tool.name": tool_name,
            "gen_ai.tool.call_id": tool_call_id,
        }
        
        self._latency.record(latency_ms, attributes)
        
        if not success:
            self._errors.add(1, {**attributes, "error.type": type(Exception).__name__ if error else "unknown"})

    def record_middleware_execution(
        self,
        middleware_name: str,
        agent_id: Optional[str],
        latency_ms: float,
        success: bool,
        error: Optional[str] = None,
    ) -> None:
        """Record middleware execution."""
        attributes = {
            "middleware.name": middleware_name,
        }
        if agent_id:
            attributes["gen_ai.agent.id"] = agent_id
        
        self._latency.record(latency_ms, attributes)
        
        if not success and error:
            self._errors.add(1, {**attributes, "error.type": type(Exception).__name__ if error else "unknown"})

    def increment_active_requests(self, agent_id: Optional[str] = None) -> None:
        """Increment active requests gauge."""
        attributes = {}
        if agent_id:
            attributes["gen_ai.agent.id"] = agent_id
        self._active_requests.add(1, attributes)

    def decrement_active_requests(self, agent_id: Optional[str] = None) -> None:
        """Decrement active requests gauge."""
        attributes = {}
        if agent_id:
            attributes["gen_ai.agent.id"] = agent_id
        self._active_requests.add(-1, attributes)


class TraceContextManager:
    """Manages trace context propagation through the SDK."""
    
    _propagator = TraceContextTextMapPropagator()
    
    @classmethod
    def inject(cls, carrier: dict) -> None:
        """Inject current trace context into carrier."""
        ctx = trace.get_current_span().get_span_context()
        if ctx and ctx.is_valid:
            trace.set_span_in_context(trace.get_current_span())
            cls._propagator.inject(carrier)
    
    @classmethod
    def extract(cls, carrier: dict) -> trace.Context:
        """Extract trace context from carrier."""
        return cls._propagator.extract(carrier)
    
    @classmethod
    def get_current_context(cls) -> dict:
        """Get current trace context as dict."""
        ctx = trace.get_current_span().get_span_context()
        if ctx and ctx.is_valid:
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
                "trace_flags": ctx.trace_flags,
            }
        return {}
    
    @classmethod
    def set_current_context(cls, context: trace.Context) -> None:
        """Set current trace context."""
        trace.set_span_in_context(trace.get_current_span(), context)
    
    @classmethod
    def get_current_span_id(cls) -> Optional[str]:
        """Get current span ID."""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, "016x")
        return None
    
    @classmethod
    def get_current_trace_id(cls) -> Optional[str]:
        """Get current trace ID."""
        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
        return None


def setup_opentelemetry(
    service_name: str = "agenticai",
    otlp_endpoint: Optional[str] = None,
    trace_sample_rate: float = 1.0,
    metrics_export_interval: int = 60000,
) -> tuple[TracerProvider, MeterProvider]:
    """Set up OpenTelemetry with GenAI semantic conventions."""
    
    # Resource
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "0.3.0",
    })
    
    # Tracer Provider
    trace_provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(trace_sample_rate),
    )
    
    if otlp_endpoint:
        trace_exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
        trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    
    trace.set_tracer_provider(trace_provider)
    
    # Meter Provider
    metric_readers = []
    if otlp_endpoint:
        metric_readers = [
            PeriodicExportingMetricReader(
                OTLPMetricExporter(endpoint=otlp_endpoint),
                export_interval_millis=metrics_export_interval,
            )
        ]
    else:
        # Use in-memory reader when no OTLP endpoint
        from opentelemetry.sdk.metrics.export import ConsoleMetricExporter
        metric_readers = [
            PeriodicExportingMetricReader(
                ConsoleMetricExporter(),
                export_interval_millis=metrics_export_interval,
            )
        ]
    
    meter_provider = MeterProvider(
        resource=resource,
        metric_readers=metric_readers,
    )
    
    return trace_provider, meter_provider


def get_genai_tracer(name: str = "agenticai") -> GenAITracer:
    """Get a GenAI tracer instance."""
    return GenAITracer(name)


def get_genai_metrics(name: str = "agenticai") -> GenAIMetrics:
    """Get GenAI metrics instance."""
    return GenAIMetrics(name)


# Initialize global instances
_genai_tracer: Optional[GenAITracer] = None
_genai_metrics: Optional[GenAIMetrics] = None


def init_otel(service_name: str = "agenticai", otlp_endpoint: Optional[str] = None) -> None:
    """Initialize OpenTelemetry with GenAI instrumentation."""
    global _genai_tracer, _genai_metrics
    
    setup_opentelemetry(service_name, otlp_endpoint)
    _genai_tracer = GenAITracer("agenticai")
    _genai_metrics = GenAIMetrics("agenticai")
    logger.info("opentelemetry_initialized", service_name=service_name)


def get_tracer() -> GenAITracer:
    """Get the global GenAI tracer."""
    global _genai_tracer
    if _genai_tracer is None:
        init_otel()
    return _genai_tracer


def get_metrics() -> GenAIMetrics:
    """Get the global GenAI metrics."""
    global _genai_metrics
    if _genai_metrics is None:
        init_otel()
    return _genai_metrics


# Context propagation helpers
def inject_trace_context(carrier: dict) -> None:
    """Inject current trace context into carrier."""
    TraceContextManager.inject(carrier)


def extract_trace_context(carrier: dict) -> trace.Context:
    """Extract trace context from carrier."""
    return TraceContextManager.extract(carrier)


def get_current_trace_context() -> dict:
    """Get current trace context as dict."""
    return TraceContextManager.get_current_context()


# Export public API
__all__ = [
    "GenAITracer",
    "GenAIMetrics",
    "TraceContextManager",
    "setup_opentelemetry",
    "init_otel",
    "get_genai_tracer",
    "get_metrics",
    "inject_trace_context",
    "extract_trace_context",
    "get_current_trace_context",
    "GENAI_SYSTEM",
    "GENAI_REQUEST_MODEL",
    "GENAI_REQUEST_TEMPERATURE",
    "GENAI_REQUEST_MAX_TOKENS",
    "GENAI_REQUEST_TOP_P",
    "GENAI_RESPONSE_MODEL",
    "GENAI_RESPONSE_FINISH_REASON",
    "GENAI_USAGE_INPUT_TOKENS",
    "GENAI_USAGE_OUTPUT_TOKENS",
    "GENAI_AGENT_ID",
    "GENAI_AGENT_NAME",
    "GENAI_TOOL_NAME",
    "GENAI_TOOL_CALL_ID",
    "GENAI_TOOL_PARAMETERS",
    "GENAI_OPERATION_NAME",
    "GENAI_ERROR_TYPE",
    "GENAI_ERROR_MESSAGE",
]
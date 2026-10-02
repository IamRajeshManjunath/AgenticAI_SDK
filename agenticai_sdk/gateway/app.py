"""
FastAPI application factory for the AgenticAI SDK gateway.

Creates and configures the FastAPI app with:
  - Execution tracking middleware
  - Structured logging (structlog)
  - API routes (/api/v1/workflow/...)
  - Health check endpoint
  - Global exception handlers
  - OpenAPI documentation metadata
"""

from __future__ import annotations

import logging

import structlog
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from agenticai_sdk.exceptions import (
    AgenticSDKError,
    BudgetExceededError,
    LoopTimeoutError,
    PromptInjectionDetectedError,
)
from agenticai_sdk.gateway.auth_middleware import AuthMiddleware
from agenticai_sdk.gateway.middleware import ExecutionTrackingMiddleware
from agenticai_sdk.gateway.routes import route_modules

# ── Structlog configuration ───────────────────────────────────────────────────


def _add_logger_name_safe(logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    if hasattr(logger, "name"):
        event_dict["logger"] = logger.name
    return event_dict


def _configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON output."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            _add_logger_name_safe,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


# ── OpenTelemetry configuration ───────────────────────────────────────────────

def _configure_opentelemetry() -> None:
    """Configure OpenTelemetry Tracer Provider and exporters."""
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME

        resource = Resource.create({SERVICE_NAME: "agenticai-sdk-gateway"})
        provider = TracerProvider(resource=resource)
        # For simplicity, we just export to console right now. 
        # In a real environment, this would export to Tempo/Jaeger via OTLP.
        processor = BatchSpanProcessor(ConsoleSpanExporter())
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        structlog.get_logger(__name__).info("opentelemetry_configured")
    except ImportError:
        structlog.get_logger(__name__).warning("opentelemetry_not_installed")


# ── App factory ───────────────────────────────────────────────────────────────


from contextlib import asynccontextmanager
from agenticai_sdk.db import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _configure_opentelemetry()
    yield

def create_app(*, log_level: str = "INFO", cors_origins: list[str] | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Args:
        log_level: Logging verbosity level (DEBUG, INFO, WARNING, ERROR).
        cors_origins: Allowed CORS origins. Defaults to all origins in development.

    Returns:
        Configured FastAPI application instance.
    """
    _configure_logging(log_level)

    app = FastAPI(
        title="AgenticAI SDK — JSON-to-Workflow Engine",
        description=(
            "Production-grade, enterprise-ready SDK for compiling declarative JSON "
            "configurations into async, resilient, stateful multi-agent DAGs using "
            "LangGraph and DeepAgent cognitive loops."
        ),
        version="0.3.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "HARPY.AI Team",
            "url": "https://harpy.ai",
        },
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(AuthMiddleware)  # Must be first — validates before execution tracking
    app.add_middleware(ExecutionTrackingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
    except ImportError:
        pass

    # ── Routes ───────────────────────────────────────────────────────────
    for rm in route_modules:
        app.include_router(rm)

    # ── Health check ──────────────────────────────────────────────────────
    @app.get(
        "/health",
        tags=["system"],
        summary="Health check",
        description="Returns the current health status of the gateway with DB info.",
    )
    async def health_check() -> dict:
        from agenticai_sdk.db.database import get_db_status as _db_status
        db = _db_status()
        return {
            "status": "healthy",
            "service": "agenticai-sdk",
            "version": "0.3.0",
            "database": db,
        }

    @app.get(
        "/health/live",
        tags=["system"],
        summary="Liveness probe",
        description="Kubernetes liveness probe - returns 200 if process is alive.",
    )
    async def liveness_check() -> dict:
        return {"status": "alive", "service": "agenticai-sdk"}

    @app.get(
        "/health/ready",
        tags=["system"],
        summary="Readiness probe",
        description="Kubernetes readiness probe - returns 200 if ready to serve traffic.",
    )
    async def readiness_check() -> dict:
        from agenticai_sdk.db.database import get_db_status as _db_status
        db = _db_status()
        redis_ok = False
        try:
            from agenticai_sdk.db.database import get_redis_client
            redis = get_redis_client()
            if redis:
                redis_ok = redis.ping()
        except Exception:
            redis_ok = False

        ready = db.get("status") == "connected" and redis_ok
        status_code = 200 if ready else 503

        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=status_code,
            content={
                "status": "ready" if ready else "not_ready",
                "service": "agenticai-sdk",
                "database": db,
                "redis": {"status": "connected" if redis_ok else "disconnected"},
            },
        )

    @app.get(
        "/",
        tags=["system"],
        summary="Root",
        description="Gateway root — redirects to /docs.",
    )
    async def root() -> dict:
        return {
            "service": "AgenticAI SDK Gateway",
            "version": "0.3.0",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "run_workflow": "POST /api/v1/workflow/run",
                "hitl_approve": "POST /api/v1/workflow/hitl/approve",
                "traces": "GET /api/v1/observability/traces",
                "metrics": "GET /api/v1/observability/metrics",
                "prometheus": "GET /api/v1/observability/metrics/prometheus",
                "evaluations": "GET /api/v1/observability/evaluations/{workflow_id}",
                "health_detailed": "GET /api/v1/observability/health",
            },
        }

    # ── Global exception handlers ─────────────────────────────────────────
    @app.exception_handler(BudgetExceededError)
    async def budget_exceeded_handler(request: Request, exc: BudgetExceededError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"error": "BudgetExceeded", "message": str(exc), "detail": exc.detail},
        )

    @app.exception_handler(LoopTimeoutError)
    async def loop_timeout_handler(request: Request, exc: LoopTimeoutError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            content={"error": "LoopTimeout", "message": str(exc), "detail": exc.detail},
        )

    @app.exception_handler(PromptInjectionDetectedError)
    async def injection_handler(request: Request, exc: PromptInjectionDetectedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"error": "PromptInjectionDetected", "message": str(exc), "detail": exc.detail},
        )

    @app.exception_handler(AgenticSDKError)
    async def agentic_sdk_error_handler(request: Request, exc: AgenticSDKError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": type(exc).__name__,
                "message": str(exc),
                "detail": exc.detail,
            },
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"error": "ValidationError", "message": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        structlog.get_logger(__name__).error(
            "unhandled_exception",
            error=str(exc),
            error_type=type(exc).__name__,
            path=str(request.url),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "InternalServerError", "message": "An unexpected error occurred."},
        )

    return app


app = create_app()

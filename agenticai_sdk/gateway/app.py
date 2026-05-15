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

from agenticai_sdk.exceptions import AgenticSDKError
from agenticai_sdk.gateway.middleware import ExecutionTrackingMiddleware
from agenticai_sdk.gateway.routes import router

# ── Structlog configuration ───────────────────────────────────────────────────


def _configure_logging(log_level: str = "INFO") -> None:
    """Configure structlog for structured JSON output."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
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


# ── App factory ───────────────────────────────────────────────────────────────


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
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        contact={
            "name": "AgenticAI SDK Team",
            "url": "https://github.com/agenticai-sdk",
        },
        license_info={
            "name": "MIT",
            "url": "https://opensource.org/licenses/MIT",
        },
    )

    # ── Middleware ────────────────────────────────────────────────────────
    app.add_middleware(ExecutionTrackingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins or ["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Routes ───────────────────────────────────────────────────────────
    app.include_router(router)

    # ── Health check ──────────────────────────────────────────────────────
    @app.get(
        "/health",
        tags=["system"],
        summary="Health check",
        description="Returns the current health status of the gateway.",
    )
    async def health_check() -> dict:
        return {"status": "healthy", "service": "agenticai-sdk", "version": "0.1.0"}

    @app.get(
        "/",
        tags=["system"],
        summary="Root",
        description="Gateway root — redirects to /docs.",
    )
    async def root() -> dict:
        return {
            "service": "AgenticAI SDK Gateway",
            "version": "0.1.0",
            "docs": "/docs",
            "health": "/health",
            "endpoints": {
                "run_workflow": "POST /api/v1/workflow/run",
                "hitl_approve": "POST /api/v1/workflow/hitl/approve",
            },
        }

    # ── Global exception handlers ─────────────────────────────────────────
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

"""
Execution tracking middleware for the AgenticAI SDK gateway.

Monitors:
  - Workflow execution duration (wall-clock time per request)
  - Step counts (via state inspection)
  - Error logs with structured metadata
  - Request/response correlation via X-Request-ID header
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class ExecutionTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware that records per-request execution metadata.

    Attaches a unique ``X-Request-ID`` to every response and emits
    structured log entries capturing method, path, status code, and
    elapsed duration for every request processed by the gateway.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        start_time = time.perf_counter()

        # Bind request context to all log entries within this request
        bound_logger = logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )
        bound_logger.info("request_received")

        # Attach request_id to request state for downstream handlers
        request.state.request_id = request_id

        try:
            response = await call_next(request)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            bound_logger.info(
                "request_complete",
                status_code=response.status_code,
                elapsed_ms=elapsed_ms,
            )
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Execution-Time-Ms"] = str(elapsed_ms)
            return response

        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            bound_logger.error(
                "request_failed",
                error=str(exc),
                error_type=type(exc).__name__,
                elapsed_ms=elapsed_ms,
            )
            raise

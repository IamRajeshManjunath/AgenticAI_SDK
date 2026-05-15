"""
Middleware base classes — abstract protocol, context carrier, and pipeline executor.

The middleware pipeline intercepts payloads at node boundaries:
  - ``before()`` hooks run in order before the agent node executes
  - ``after()`` hooks run in reverse order after the node completes
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class Direction(str, Enum):
    """Direction of payload flow through the middleware."""

    INBOUND = "inbound"    # Payload entering a node (before execution)
    OUTBOUND = "outbound"  # Payload leaving a node (after execution)


@dataclass
class MiddlewareContext:
    """Context carrier passed through every middleware hook.

    Attributes:
        payload: The mutable data dict flowing through the pipeline (typically
            a WorkflowState subset or tool call arguments).
        metadata: Middleware-specific metadata accumulated across hooks —
            budget tracker, PII vault references, firewall events, etc.
        state: Reference to the full WorkflowState for read access.
        agent_id: ID of the agent node being intercepted.
        direction: Whether this is an inbound (before) or outbound (after) pass.
        workflow_id: ID of the current workflow execution.
        trace_id: Active observability trace ID (may be None).
    """

    payload: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)
    agent_id: str = ""
    direction: Direction = Direction.INBOUND
    workflow_id: str = ""
    trace_id: str | None = None


class MiddlewareBase(abc.ABC):
    """Abstract base class for all execution middlewares.

    Subclasses must implement ``before()`` and ``after()`` hooks.
    Both receive a ``MiddlewareContext`` and must return the (possibly
    mutated) context to the next middleware in the pipeline.
    """

    @property
    def name(self) -> str:
        """Human-readable middleware name for logging."""
        return self.__class__.__name__

    @abc.abstractmethod
    async def before(self, context: MiddlewareContext) -> MiddlewareContext:
        """Intercept payload BEFORE the agent node executes.

        Args:
            context: Middleware context with inbound payload.

        Returns:
            The (possibly modified) middleware context.
        """

    @abc.abstractmethod
    async def after(self, context: MiddlewareContext) -> MiddlewareContext:
        """Intercept payload AFTER the agent node has executed.

        Args:
            context: Middleware context with outbound payload.

        Returns:
            The (possibly modified) middleware context.
        """


class MiddlewarePipeline:
    """Ordered chain executor for middleware hooks.

    Runs ``before()`` hooks in registration order before node execution,
    then runs ``after()`` hooks in *reverse* order after node completion
    (unwinding stack style).

    Usage::

        pipeline = MiddlewarePipeline([budget_mw, pii_mw, firewall_mw, compression_mw])
        ctx = await pipeline.run_before(context)
        # ... execute node ...
        ctx = await pipeline.run_after(context)
    """

    def __init__(self, middlewares: list[MiddlewareBase] | None = None) -> None:
        self._middlewares: list[MiddlewareBase] = middlewares or []

    def add(self, middleware: MiddlewareBase) -> "MiddlewarePipeline":
        """Append a middleware to the pipeline (fluent API)."""
        self._middlewares.append(middleware)
        return self

    async def run_before(self, context: MiddlewareContext) -> MiddlewareContext:
        """Execute all ``before()`` hooks in order.

        Args:
            context: Initial middleware context.

        Returns:
            The context after all before-hooks have processed it.
        """
        context.direction = Direction.INBOUND
        for mw in self._middlewares:
            logger.debug(
                "middleware_before_start",
                middleware=mw.name,
                agent_id=context.agent_id,
            )
            context = await mw.before(context)
            logger.debug(
                "middleware_before_complete",
                middleware=mw.name,
                agent_id=context.agent_id,
            )
        return context

    async def run_after(self, context: MiddlewareContext) -> MiddlewareContext:
        """Execute all ``after()`` hooks in reverse order.

        Args:
            context: Middleware context with outbound payload.

        Returns:
            The context after all after-hooks have processed it.
        """
        context.direction = Direction.OUTBOUND
        for mw in reversed(self._middlewares):
            logger.debug(
                "middleware_after_start",
                middleware=mw.name,
                agent_id=context.agent_id,
            )
            context = await mw.after(context)
            logger.debug(
                "middleware_after_complete",
                middleware=mw.name,
                agent_id=context.agent_id,
            )
        return context

    @property
    def middleware_names(self) -> list[str]:
        """Return ordered list of registered middleware names."""
        return [mw.name for mw in self._middlewares]

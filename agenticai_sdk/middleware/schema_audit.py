"""
Schema Audit Middleware — records every middleware pass payload to
schema_audit_trails for compliance and debugging.

One row per before/after pass per agent node.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

from agenticai_sdk.db.database import get_session
from agenticai_sdk.db.models import SchemaAuditTrail
from agenticai_sdk.middleware.base import MiddlewareBase, MiddlewareContext

logger = structlog.get_logger(__name__)


class SchemaAuditMiddleware(MiddlewareBase):
    """Records every inbound/outbound middleware payload to the audit trail.

    Inserts one row per ``before()`` and ``after()`` call, capturing the
    full payload, agent ID, direction, and a placeholder schema definition.

    Uses a short-lived session per write to avoid coupling with the caller's
    transaction lifecycle.
    """

    def __init__(self, session_factory: Any | None = None) -> None:
        self._session_factory = session_factory or get_session

    async def before(self, context: MiddlewareContext) -> MiddlewareContext:
        self._audit(
            agent_id=context.agent_id,
            direction="incoming",
            payload=context.payload,
            is_valid=True,
        )
        return context

    async def after(self, context: MiddlewareContext) -> MiddlewareContext:
        self._audit(
            agent_id=context.agent_id,
            direction="outgoing",
            payload=context.payload,
            is_valid=True,
        )
        return context

    def _audit(
        self,
        agent_id: str,
        direction: str,
        payload: dict[str, Any],
        is_valid: bool,
        violation_error: str | None = None,
    ) -> None:
        db = next(self._session_factory())
        try:
            record = SchemaAuditTrail(
                id=uuid.uuid4().hex[:12],
                agent_id=agent_id,
                direction=direction,
                payload=payload,
                schema_definition={},
                is_valid=int(is_valid),
                violation_error=violation_error,
            )
            db.add(record)
            db.commit()
        except Exception:
            db.rollback()
            logger.warning(
                "schema_audit_write_failed",
                agent_id=agent_id,
                direction=direction,
                exc_info=True,
            )
        finally:
            db.close()

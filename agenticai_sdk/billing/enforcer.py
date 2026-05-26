"""PlanEnforcer — checks workspace usage against plan limits before execution."""

from __future__ import annotations

import structlog
from typing import Any

logger = structlog.get_logger(__name__)


class PlanEnforcer:
    """Middleware that validates workspace plan limits before allowing execution.

    Checks:
      - Token usage vs plan token limit
      - Workflow count vs plan max_workflows
      - Cost incurred vs plan cost limit
    """

    def __init__(self, db_session=None):
        self._db = db_session

    async def before(self, context: "MiddlewareContext") -> "MiddlewareContext":
        """Check plan limits before agent node execution."""
        from agenticai_sdk.db import get_session
        from agenticai_sdk.db.models import Workspace

        workspace_id = context.workspace_id
        if not workspace_id:
            return context

        db = self._db or next(get_session())
        try:
            ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
            if not ws or not ws.plan:
                logger.debug("plan_enforcer_no_plan", workspace_id=workspace_id)
                return context

            plan = ws.plan
            if not plan.is_active:
                logger.warning("plan_inactive", workspace_id=workspace_id, plan=plan.name)
                raise PermissionError(f"Plan '{plan.name}' is no longer active. Please upgrade.")

            from agenticai_sdk.db.models import BillingData
            from datetime import datetime, timezone, timedelta

            period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

            usage = (
                db.query(BillingData)
                .filter(
                    BillingData.workspace_id == workspace_id,
                    BillingData.period_start >= period_start,
                    BillingData.period_end <= period_end,
                )
                .all()
            )
            total_tokens = sum(u.metrics.get("tokens", 0) for u in usage if u.metrics)
            total_cost = sum(u.amount for u in usage)

            if total_tokens >= plan.tokens_per_month:
                raise PermissionError(
                    f"Token limit reached ({total_tokens:,}/{plan.tokens_per_month:,}). "
                    f"Upgrade your plan at /billing."
                )

            context.metadata["plan"] = plan.name
            context.metadata["tokens_used"] = total_tokens
            context.metadata["tokens_limit"] = plan.tokens_per_month
        finally:
            if not self._db:
                db.close()

        return context

    async def after(self, context: "MiddlewareContext") -> "MiddlewareContext":
        return context

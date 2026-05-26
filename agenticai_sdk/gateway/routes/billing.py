"""Billing routes — plan listing, usage (stripe removed, endpoints return 503)."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from agenticai_sdk.auth.dependencies import get_current_user
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import BillingData, Plan, User, Workflow, Workspace

from agenticai_sdk.billing.schemas import (
    BillingPortalResponse,
    CreateCheckoutSessionResponse,
    PlanResponse,
    UsageResponse,
)

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[PlanResponse])
async def list_plans(db: Session = Depends(get_session)):
    plans = db.query(Plan).filter(Plan.is_active == True).all()
    return [PlanResponse.model_validate(p) for p in plans]


@router.post("/create-checkout-session", response_model=CreateCheckoutSessionResponse)
async def create_checkout_session(
    current_user: User = Depends(get_current_user),
):
    raise HTTPException(status_code=503, detail="Billing not configured. Set STRIPE_SECRET_KEY to enable.")


@router.get("/portal", response_model=BillingPortalResponse)
async def billing_portal(current_user: User = Depends(get_current_user)):
    raise HTTPException(status_code=503, detail="Billing not configured.")


@router.get("/usage", response_model=UsageResponse)
async def get_usage(current_user: User = Depends(get_current_user), db: Session = Depends(get_session)):
    workspace_id = current_user.default_workspace_id
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    plan = db.query(Plan).filter(Plan.id == ws.plan_id).first() if ws and ws.plan_id else None
    period_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    period_end = (period_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    usage_records = db.query(BillingData).filter(
        BillingData.workspace_id == workspace_id,
        BillingData.period_start >= period_start,
        BillingData.period_end <= period_end,
    ).all()
    total_tokens = sum(u.metrics.get("tokens", 0) for u in usage_records if u.metrics)
    total_cost = sum(u.amount for u in usage_records)
    workflows_count = db.query(Workflow).filter(Workflow.workspace_id == workspace_id).count()
    return UsageResponse(
        plan=plan.name if plan else "Free", tokens_used=total_tokens,
        tokens_limit=plan.tokens_per_month if plan else 100000,
        workflows_count=workflows_count, workflows_limit=plan.max_workflows if plan else 5,
        cost_incurred=total_cost, cost_limit=0.0,
        period_start=period_start.isoformat(), period_end=period_end.isoformat(),
    )


@router.post("/webhook")
async def stripe_webhook(request: Request):
    logger.info("stripe_webhook_received (ignored — billing not configured)")
    return {"received": True}

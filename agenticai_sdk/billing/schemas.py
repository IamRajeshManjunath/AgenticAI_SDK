from pydantic import BaseModel, Field
from typing import Optional


class CreateCheckoutSessionRequest(BaseModel):
    price_id: str = Field(..., description="Stripe Price ID")
    success_url: str = Field(default="http://localhost:3000/billing?success=true")
    cancel_url: str = Field(default="http://localhost:3000/billing?canceled=true")


class CreateCheckoutSessionResponse(BaseModel):
    url: str
    session_id: str


class BillingPortalResponse(BaseModel):
    url: str


class UsageResponse(BaseModel):
    plan: str
    tokens_used: int
    tokens_limit: int
    workflows_count: int
    workflows_limit: int
    cost_incurred: float
    cost_limit: float
    period_start: str
    period_end: str


class PlanResponse(BaseModel):
    id: str
    name: str
    tokens_per_month: int
    max_workflows: int
    max_api_keys: int
    max_team_members: int
    features: dict
    price_cents: int

    model_config = {"from_attributes": True}

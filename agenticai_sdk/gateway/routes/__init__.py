"""
Route modules for the AgenticAI FastAPI gateway.

All API route handlers are consolidated here under ``gateway/routes/``
instead of being scattered across ``auth/``, ``billing/``, ``evaluation/``, etc.
"""

from __future__ import annotations

from fastapi import APIRouter

from .auth import router as auth_router
from .workflows import router as workflows_router
from .integrations import router as integrations_router
from .observability import observability_router
from .billing import router as billing_router
from .secrets import router as secrets_router
from .policies import router as policies_router
from .skills import router as skills_router
from .config import router as config_router
from .runs import router as runs_router
from .workspaces import router as workspaces_router
from .evaluations import router as evaluations_router
from .audit import router as audit_router

# Ordered list of all route modules for app factory iteration
route_modules: list[APIRouter] = [
    auth_router,
    workflows_router,
    integrations_router,
    observability_router,
    billing_router,
    secrets_router,
    policies_router,
    skills_router,
    config_router,
    runs_router,
    workspaces_router,
    evaluations_router,
    audit_router,
]

__all__ = [
    "route_modules",
    "auth_router",
    "workflows_router",
    "integrations_router",
    "observability_router",
    "billing_router",
    "secrets_router",
    "policies_router",
    "skills_router",
    "config_router",
    "runs_router",
    "workspaces_router",
    "evaluations_router",
    "audit_router",
]

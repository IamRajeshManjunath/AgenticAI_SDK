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

# Ordered list of all route modules for app factory iteration
route_modules: list[APIRouter] = [
    auth_router,
    workflows_router,
    integrations_router,
    observability_router,
    billing_router,
]

__all__ = [
    "route_modules",
    "auth_router",
    "workflows_router",
    "integrations_router",
    "observability_router",
    "billing_router",
]

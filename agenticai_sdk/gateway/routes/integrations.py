"""FastAPI route handlers for third-party integration management.

Endpoints:
  POST   /api/v1/workflow/integrations/connect — register a new connection
  GET    /api/v1/workflow/integrations          — list active connections
  DELETE /api/v1/workflow/integrations/{type}   — disconnect
  POST   /api/v1/workflow/integrations/{type}/test — test connectivity
"""

from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import IntegrationConnection, User
from agenticai_sdk.runtime.integration_registry import IntegrationRegistry
from agenticai_sdk.schemas.integration import IntegrationConfig, IntegrationType

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/workflow/integrations", tags=["integrations"])


def _log_activity(
    db: Session,
    action: str,
    resource_type: str,
    resource_id: str,
    resource_name: str,
    workspace_id: str = "system",
    details: dict | None = None,
):
    from agenticai_sdk.db.models import ActivityLog
    entry = ActivityLog(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        event_type=f"integration.{action}",
        details={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            **(details or {}),
        },
    )
    db.add(entry)
    db.commit()


def _get_workspace_id(request: Request) -> str:
    return getattr(request.state, "workspace_id", None) or "default"


@router.post("/connect")
async def connect_integration(
    config: IntegrationConfig,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("integration:create")),
):
    ws_id = _get_workspace_id(request)
    registry = IntegrationRegistry(workspace_id=ws_id)
    result = registry.register_connection(
        integration_type=config.integration_type.value,
        name=config.name,
        auth_state=config.auth_state,
        rate_limits=config.rate_limits or {},
    )
    logger.info("integration_connected", type=config.integration_type.value, name=config.name)
    _log_activity(db, "connected", "integration", config.integration_type.value, config.name, workspace_id=ws_id)
    return {"success": True, "connection": result}


@router.get("")
async def list_integrations(
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("integration:read")),
):
    ws_id = _get_workspace_id(request)
    conns = db.query(IntegrationConnection).filter(
        IntegrationConnection.workspace_id == ws_id,
        IntegrationConnection.is_active == 1,
    ).all()
    return [
        {
            "id": c.id,
            "workspace_id": c.workspace_id,
            "integration_type": c.integration_type,
            "name": c.name,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in conns
    ]


@router.delete("/{integration_type}")
async def disconnect_integration(
    integration_type: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("integration:delete")),
):
    ws_id = _get_workspace_id(request)
    if integration_type not in {t.value for t in IntegrationType}:
        raise HTTPException(status_code=400, detail=f"Unsupported integration type: {integration_type}")

    conn_id = f"{ws_id}:{integration_type}"
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.id == conn_id,
        IntegrationConnection.workspace_id == ws_id,
        IntegrationConnection.is_active == 1,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail=f"No active connection found for {integration_type}")

    conn.is_active = 0
    db.commit()
    logger.info("integration_disconnected", type=integration_type)
    _log_activity(db, "disconnected", "integration", integration_type, conn.name, workspace_id=ws_id)
    return {"success": True, "message": f"Disconnected {integration_type}"}


class TestConnectionRequest(BaseModel):
    target: str | None = None
    message: str = "Hello from AgenticAI SDK!"


@router.post("/{integration_type}/test")
async def test_integration(
    integration_type: str,
    body: TestConnectionRequest,
    request: Request,
    _: User = Depends(require_permission("integration:connect")),
):
    ws_id = _get_workspace_id(request)
    if integration_type not in {t.value for t in IntegrationType}:
        raise HTTPException(status_code=400, detail=f"Unsupported integration type: {integration_type}")

    registry = IntegrationRegistry(workspace_id=ws_id)
    try:
        result = await registry.test_connection(integration_type, target=body.target, message=body.message)
        return {"success": True, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

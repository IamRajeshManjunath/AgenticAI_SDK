"""FastAPI route handlers for third-party integration management.

Endpoints:
  POST   /api/v1/workflow/integrations/connect — register a new connection
  GET    /api/v1/workflow/integrations          — list active connections
  DELETE /api/v1/workflow/integrations/{type}   — disconnect
  POST   /api/v1/workflow/integrations/{type}/test — test connectivity
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import IntegrationConnection
from agenticai_sdk.runtime.integration_registry import IntegrationRegistry
from agenticai_sdk.schemas.integration import IntegrationConfig, IntegrationType

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/workflow/integrations", tags=["integrations"])

DEFAULT_WORKSPACE = "default"


@router.post("/connect")
async def connect_integration(
    config: IntegrationConfig,
    db: Session = Depends(get_session),
):
    """Register a third-party integration connection (connect once, persist forever)."""
    registry = IntegrationRegistry(workspace_id=DEFAULT_WORKSPACE)
    result = registry.register_connection(
        integration_type=config.integration_type.value,
        name=config.name,
        auth_state=config.auth_state,
        rate_limits=config.rate_limits or {},
    )
    logger.info("integration_connected", type=config.integration_type.value, name=config.name)
    return {"success": True, "connection": result}


@router.get("")
async def list_integrations(db: Session = Depends(get_session)):
    """List all active integration connections."""
    conns = db.query(IntegrationConnection).filter(
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
    db: Session = Depends(get_session),
):
    """Disconnect a third-party integration."""
    if integration_type not in {t.value for t in IntegrationType}:
        raise HTTPException(status_code=400, detail=f"Unsupported integration type: {integration_type}")

    conn_id = f"{DEFAULT_WORKSPACE}:{integration_type}"
    conn = db.query(IntegrationConnection).filter(
        IntegrationConnection.id == conn_id,
        IntegrationConnection.is_active == 1,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail=f"No active connection found for {integration_type}")

    conn.is_active = 0
    db.commit()
    logger.info("integration_disconnected", type=integration_type)
    return {"success": True, "message": f"Disconnected {integration_type}"}


class TestConnectionRequest(BaseModel):
    target: str | None = None
    message: str = "Hello from AgenticAI SDK!"


@router.post("/{integration_type}/test")
async def test_integration(
    integration_type: str,
    body: TestConnectionRequest,
):
    """Send a test message to verify a connection is working."""
    if integration_type not in {t.value for t in IntegrationType}:
        raise HTTPException(status_code=400, detail=f"Unsupported integration type: {integration_type}")

    registry = IntegrationRegistry(workspace_id=DEFAULT_WORKSPACE)
    try:
        result = await registry.test_connection(integration_type, target=body.target, message=body.message)
        return {"success": True, "result": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

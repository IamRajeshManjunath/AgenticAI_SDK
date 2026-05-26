from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.auth.secrets import decrypt_value, encrypt_value
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import Secret, User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/secrets", tags=["secrets"])


def _get_workspace_id(request: Request) -> str:
    return getattr(request.state, "workspace_id", None) or "default"


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
        event_type=f"secret.{action}",
        details={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            **(details or {}),
        },
    )
    db.add(entry)
    db.flush()


class SecretCreateRequest(BaseModel):
    name: str
    value: str
    description: str | None = None


class SecretUpdateRequest(BaseModel):
    name: str | None = None
    value: str | None = None
    description: str | None = None


class SecretResponse(BaseModel):
    id: str
    name: str
    description: str | None
    created_at: str | None
    updated_at: str | None


class SecretValueResponse(SecretResponse):
    value: str


@router.get("", response_model=list[SecretResponse])
async def list_secrets(
    request: Request,
    current_user: User = Depends(require_permission("secret:read")),
    db: Session = Depends(get_session),
):
    ws_id = _get_workspace_id(request)
    secrets = db.query(Secret).filter(
        Secret.workspace_id == ws_id,
    ).all()
    return [
        SecretResponse(
            id=s.id,
            name=s.name,
            description=s.description,
            created_at=s.created_at.isoformat() if s.created_at else None,
            updated_at=s.updated_at.isoformat() if s.updated_at else None,
        )
        for s in secrets
    ]


@router.get("/{secret_id}", response_model=SecretValueResponse)
async def get_secret(
    secret_id: str,
    request: Request,
    current_user: User = Depends(require_permission("secret:read-value")),
    db: Session = Depends(get_session),
):
    ws_id = _get_workspace_id(request)
    secret = db.query(Secret).filter(
        Secret.id == secret_id,
        Secret.workspace_id == ws_id,
    ).first()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    return SecretValueResponse(
        id=secret.id,
        name=secret.name,
        description=secret.description,
        value=decrypt_value(secret.encrypted_value),
        created_at=secret.created_at.isoformat() if secret.created_at else None,
        updated_at=secret.updated_at.isoformat() if secret.updated_at else None,
    )


@router.post("", response_model=SecretResponse, status_code=status.HTTP_201_CREATED)
async def create_secret(
    body: SecretCreateRequest,
    request: Request,
    current_user: User = Depends(require_permission("secret:create")),
    db: Session = Depends(get_session),
):
    ws_id = _get_workspace_id(request)
    secret_id = str(uuid.uuid4())
    encrypted = encrypt_value(body.value)
    secret = Secret(
        id=secret_id,
        workspace_id=ws_id,
        name=body.name,
        encrypted_value=encrypted,
        description=body.description,
    )
    db.add(secret)
    _log_activity(db, "created", "secret", secret_id, body.name, workspace_id=ws_id)
    db.commit()
    logger.info("secret_created", id=secret_id, name=body.name)
    return SecretResponse(
        id=secret.id,
        name=secret.name,
        description=secret.description,
        created_at=secret.created_at.isoformat() if secret.created_at else None,
        updated_at=secret.updated_at.isoformat() if secret.updated_at else None,
    )


@router.patch("/{secret_id}", response_model=SecretResponse)
async def update_secret(
    secret_id: str,
    body: SecretUpdateRequest,
    request: Request,
    current_user: User = Depends(require_permission("secret:update")),
    db: Session = Depends(get_session),
):
    ws_id = _get_workspace_id(request)
    secret = db.query(Secret).filter(
        Secret.id == secret_id,
        Secret.workspace_id == ws_id,
    ).first()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    if body.name is not None:
        secret.name = body.name
    if body.value is not None:
        secret.encrypted_value = encrypt_value(body.value)
    if body.description is not None:
        secret.description = body.description
    _log_activity(db, "updated", "secret", secret_id, secret.name, workspace_id=ws_id)
    db.commit()
    logger.info("secret_updated", id=secret_id, name=secret.name)
    return SecretResponse(
        id=secret.id,
        name=secret.name,
        description=secret.description,
        created_at=secret.created_at.isoformat() if secret.created_at else None,
        updated_at=secret.updated_at.isoformat() if secret.updated_at else None,
    )


@router.delete("/{secret_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_secret(
    secret_id: str,
    request: Request,
    current_user: User = Depends(require_permission("secret:delete")),
    db: Session = Depends(get_session),
):
    ws_id = _get_workspace_id(request)
    secret = db.query(Secret).filter(
        Secret.id == secret_id,
        Secret.workspace_id == ws_id,
    ).first()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    name = secret.name
    db.delete(secret)
    _log_activity(db, "deleted", "secret", secret_id, name, workspace_id=ws_id)
    db.commit()
    logger.info("secret_deleted", id=secret_id, name=name)


@router.post("/{secret_id}/regenerate", response_model=SecretResponse)
async def regenerate_secret(
    secret_id: str,
    body: SecretCreateRequest,
    request: Request,
    current_user: User = Depends(require_permission("secret:update")),
    db: Session = Depends(get_session),
):
    ws_id = _get_workspace_id(request)
    secret = db.query(Secret).filter(
        Secret.id == secret_id,
        Secret.workspace_id == ws_id,
    ).first()
    if not secret:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Secret not found")
    secret.encrypted_value = encrypt_value(body.value)
    if body.description is not None:
        secret.description = body.description
    _log_activity(db, "regenerated", "secret", secret_id, secret.name, workspace_id=ws_id)
    db.commit()
    logger.info("secret_regenerated", id=secret_id, name=secret.name)
    return SecretResponse(
        id=secret.id,
        name=secret.name,
        description=secret.description,
        created_at=secret.created_at.isoformat() if secret.created_at else None,
        updated_at=secret.updated_at.isoformat() if secret.updated_at else None,
    )

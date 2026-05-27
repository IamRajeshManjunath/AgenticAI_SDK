from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import Policy, PolicyAttachment, User

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/policies", tags=["policies"])


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
        event_type=f"policy.{action}",
        details={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            **(details or {}),
        },
    )
    db.add(entry)
    db.commit()


class PolicyStatement(BaseModel):
    effect: str = Field(pattern="^(Allow|Deny)$")
    actions: list[str] = Field(min_length=1)
    resources: list[str] = Field(min_length=1)


class PolicyDocumentSchema(BaseModel):
    version: str = Field(pattern="^1$")
    statements: list[PolicyStatement] = Field(min_length=1)


class PolicyCreateRequest(BaseModel):
    name: str
    description: str | None = None
    policy_document: PolicyDocumentSchema


class PolicyUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    policy_document: PolicyDocumentSchema | None = None


class PolicyResponse(BaseModel):
    id: str
    name: str
    description: str | None
    is_system: bool
    policy_document: dict[str, Any] | None
    created_at: str | None


class AttachmentCreateRequest(BaseModel):
    policy_id: str
    principal_type: str = Field(pattern="^(user|role|workspace)$")
    principal_id: str


class AttachmentResponse(BaseModel):
    id: str
    policy_id: str
    principal_type: str
    principal_id: str


@router.get("", response_model=list[PolicyResponse])
async def list_policies(
    current_user: User = Depends(require_permission("role:read")),
    db: Session = Depends(get_session),
):
    policies = db.query(Policy).order_by(Policy.created_at.desc()).all()
    return [
        PolicyResponse(
            id=p.id,
            name=p.name,
            description=p.description,
            is_system=bool(p.is_system),
            policy_document=p.policy_document,
            created_at=p.created_at.isoformat() if p.created_at else None,
        )
        for p in policies
    ]


@router.get("/{policy_id}", response_model=PolicyResponse)
async def get_policy(
    policy_id: str,
    current_user: User = Depends(require_permission("role:read")),
    db: Session = Depends(get_session),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        is_system=bool(policy.is_system),
        policy_document=policy.policy_document,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
    )


@router.post("", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
async def create_policy(
    body: PolicyCreateRequest,
    current_user: User = Depends(require_permission("role:create")),
    db: Session = Depends(get_session),
):
    policy_id = str(uuid.uuid4())
    policy = Policy(
        id=policy_id,
        name=body.name,
        description=body.description or "",
        policy_document=body.policy_document.model_dump(),
        is_system=0,
    )
    db.add(policy)
    db.commit()
    logger.info("policy_created", id=policy_id, name=body.name)
    _log_activity(db, "created", "policy", policy_id, body.name)
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        is_system=False,
        policy_document=policy.policy_document,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
    )


@router.patch("/{policy_id}", response_model=PolicyResponse)
async def update_policy(
    policy_id: str,
    body: PolicyUpdateRequest,
    current_user: User = Depends(require_permission("role:update")),
    db: Session = Depends(get_session),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if policy.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System policies cannot be modified",
        )
    if body.name is not None:
        policy.name = body.name
    if body.description is not None:
        policy.description = body.description
    if body.policy_document is not None:
        policy.policy_document = body.policy_document.model_dump()
    db.commit()
    logger.info("policy_updated", id=policy_id, name=policy.name)
    _log_activity(db, "updated", "policy", policy_id, policy.name)
    return PolicyResponse(
        id=policy.id,
        name=policy.name,
        description=policy.description,
        is_system=False,
        policy_document=policy.policy_document,
        created_at=policy.created_at.isoformat() if policy.created_at else None,
    )


@router.delete("/{policy_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_policy(
    policy_id: str,
    current_user: User = Depends(require_permission("role:delete")),
    db: Session = Depends(get_session),
):
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")
    if policy.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System policies cannot be deleted",
        )
    name = policy.name
    db.delete(policy)
    db.commit()
    logger.info("policy_deleted", id=policy_id, name=name)
    _log_activity(db, "deleted", "policy", policy_id, name)


@router.get("/attachments", response_model=list[AttachmentResponse])
async def list_attachments(
    principal_type: str | None = None,
    principal_id: str | None = None,
    current_user: User = Depends(require_permission("role:read")),
    db: Session = Depends(get_session),
):
    q = db.query(PolicyAttachment)
    if principal_type:
        q = q.filter(PolicyAttachment.principal_type == principal_type)
    if principal_id:
        q = q.filter(PolicyAttachment.principal_id == principal_id)
    attachments = q.all()
    return [
        AttachmentResponse(
            id=a.id,
            policy_id=a.policy_id,
            principal_type=a.principal_type,
            principal_id=a.principal_id,
        )
        for a in attachments
    ]


@router.post("/attachments", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
async def attach_policy(
    body: AttachmentCreateRequest,
    current_user: User = Depends(require_permission("role:attach")),
    db: Session = Depends(get_session),
):
    policy = db.query(Policy).filter(Policy.id == body.policy_id).first()
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    existing = db.query(PolicyAttachment).filter(
        PolicyAttachment.policy_id == body.policy_id,
        PolicyAttachment.principal_type == body.principal_type,
        PolicyAttachment.principal_id == body.principal_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This policy is already attached to this principal",
        )

    attachment = PolicyAttachment(
        id=str(uuid.uuid4()),
        policy_id=body.policy_id,
        principal_type=body.principal_type,
        principal_id=body.principal_id,
    )
    db.add(attachment)
    db.commit()
    logger.info("policy_attached", policy_id=body.policy_id, principal_type=body.principal_type, principal_id=body.principal_id)
    _log_activity(db, "attached", "policy", body.policy_id, body.policy_id)
    return AttachmentResponse(
        id=attachment.id,
        policy_id=attachment.policy_id,
        principal_type=attachment.principal_type,
        principal_id=attachment.principal_id,
    )


@router.delete("/attachments/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def detach_policy(
    attachment_id: str,
    current_user: User = Depends(require_permission("role:detach")),
    db: Session = Depends(get_session),
):
    attachment = db.query(PolicyAttachment).filter(PolicyAttachment.id == attachment_id).first()
    if not attachment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    db.delete(attachment)
    db.commit()
    logger.info("policy_detached", id=attachment_id)
    _log_activity(db, "detached", "policy", attachment.policy_id, attachment.policy_id)

"""Auth routes: register, login, user profile, API keys, workspace members."""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
import jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import ApiKey, User, Workflow, Workspace, WorkspaceMember

from agenticai_sdk.auth.dependencies import get_current_user, SECRET_KEY, ALGORITHM
from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.auth.schemas import (
    ApiKeyCreateRequest,
    ApiKeyCreateResponse,
    ApiKeyResponse,
    ChangePasswordRequest,
    InviteMemberRequest,
    LoginRequest,
    RegisterRequest,
    TokenResponse,
    UpdateMemberRoleRequest,
    UserResponse,
    WorkspaceMemberResponse,
)

logger = structlog.get_logger(__name__)


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
        event_type=f"auth.{action}",
        details={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            **(details or {}),
        },
    )
    db.add(entry)
    db.commit()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 7 days


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_access_token(user_id: str, workspace_id: str | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if workspace_id:
        payload["workspace_id"] = workspace_id
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


# ── Register ──────────────────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Session = Depends(get_session)):
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user_id = str(uuid.uuid4())
    workspace_id = str(uuid.uuid4())

    user = User(
        id=user_id,
        email=body.email,
        hashed_password=_hash_password(body.password),
        full_name=body.full_name,
        is_active=1,
        default_workspace_id=workspace_id,
    )
    db.add(user)

    workspace = Workspace(
        id=workspace_id,
        name=body.workspace_name,
        description=f"{body.full_name or body.email}'s workspace",
        owner_id=user_id,
    )
    db.add(workspace)

    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user_id,
        role="admin",
    )
    db.add(membership)

    db.commit()

    token = _create_access_token(user_id, workspace_id)
    logger.info("user_registered", user_id=user_id, email=body.email)

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


# ── Login ─────────────────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: Session = Depends(get_session)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive",
        )

    token = _create_access_token(user.id, user.default_workspace_id)
    logger.info("user_logged_in", user_id=user.id)

    return TokenResponse(
        access_token=token,
        user=UserResponse.model_validate(user),
    )


# ── Profile ───────────────────────────────────────────────────────────────


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session),
):
    if not _verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    current_user.hashed_password = _hash_password(body.new_password)
    db.commit()


# ── API Keys ──────────────────────────────────────────────────────────────


@router.post("/api-keys", response_model=ApiKeyCreateResponse)
async def create_api_key(
    body: ApiKeyCreateRequest,
    current_user: User = Depends(require_permission("apikey:create")),
    db: Session = Depends(get_session),
):
    workspace_id = current_user.default_workspace_id
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No default workspace")

    raw_key = f"agk_{uuid.uuid4().hex}"
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        key_prefix=key_prefix,
        key_hash=_hash_password(raw_key),
        name=body.name,
    )
    db.add(api_key)
    db.commit()
    _log_activity(db, "apikey.created", "apikey", api_key.id, body.name, workspace_id=workspace_id)

    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=key_prefix,
    )


@router.get("/api-keys", response_model=list[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(require_permission("apikey:read")),
    db: Session = Depends(get_session),
):
    workspace_id = current_user.default_workspace_id
    if not workspace_id:
        return []
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.workspace_id == workspace_id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [ApiKeyResponse.model_validate(k) for k in keys]


@router.post("/api-keys/workflow/{workflow_id}", response_model=ApiKeyCreateResponse)
async def create_workflow_api_key(
    workflow_id: str,
    request: Request,
    current_user: User = Depends(require_permission("apikey:create")),
    db: Session = Depends(get_session),
):
    """Generate or regenerate a workflow-scoped API key (wfk_)."""
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == wf.workspace_id,
        WorkspaceMember.user_id == current_user.id,
    ).first()
    if not member:
        raise HTTPException(status_code=403, detail="Access denied to this workflow")

    workspace_id = wf.workspace_id

    existing = db.query(ApiKey).filter(
        ApiKey.workflow_id == workflow_id,
        ApiKey.is_active == 1,
    ).all()
    for ek in existing:
        ek.is_active = 0

    raw_key = f"wfk_{uuid.uuid4().hex}"
    key_prefix = raw_key[:12]

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        key_prefix=key_prefix,
        key_hash=_hash_password(raw_key),
        name=f"Workflow key for {wf.name}",
    )
    db.add(api_key)
    db.commit()
    _log_activity(db, "apikey.workflow_created", "apikey", api_key.id, api_key.name, workspace_id=workspace_id, details={"workflow_id": workflow_id})

    return ApiKeyCreateResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key,
        key_prefix=key_prefix,
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(require_permission("apikey:delete")),
    db: Session = Depends(get_session),
):
    key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(key)
    db.commit()
    _log_activity(db, "apikey.deleted", "apikey", key_id, key.name, workspace_id=key.workspace_id)


# ── Workspace Members ─────────────────────────────────────────────────────


@router.get("/workspace/members", response_model=list[WorkspaceMemberResponse])
async def list_members(
    db: Session = Depends(get_session),
    current_user: User = Depends(require_permission("member:list")),
):
    workspace_id = current_user.default_workspace_id
    members = (
        db.query(WorkspaceMember, User)
        .join(User, WorkspaceMember.user_id == User.id)
        .filter(WorkspaceMember.workspace_id == workspace_id)
        .all()
    )
    return [
        WorkspaceMemberResponse(
            user_id=u.id,
            email=u.email,
            full_name=u.full_name,
            role=m.role,
        )
        for m, u in members
    ]


@router.post("/workspace/invite", status_code=status.HTTP_201_CREATED)
async def invite_member(
    body: InviteMemberRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_permission("member:invite")),
):
    workspace_id = current_user.default_workspace_id
    invited = db.query(User).filter(User.email == body.email).first()
    if not invited:
        raise HTTPException(status_code=404, detail="User not found. They must register first.")

    existing = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == invited.id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")

    membership = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=invited.id,
        role=body.role,
    )
    db.add(membership)
    db.commit()
    _log_activity(db, "member.invited", "member", invited.id, body.email, workspace_id=workspace_id)
    return {"success": True}


@router.put("/workspace/members/{user_id}/role")
async def update_member_role(
    user_id: str,
    body: UpdateMemberRoleRequest,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_permission("member:update-role")),
):
    workspace_id = current_user.default_workspace_id
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")
    membership.role = body.role
    db.commit()
    _log_activity(db, "member.role_changed", "member", user_id, user_id, workspace_id=workspace_id, details={"new_role": body.role})
    return {"success": True}


@router.delete("/workspace/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    user_id: str,
    db: Session = Depends(get_session),
    current_user: User = Depends(require_permission("member:remove")),
):
    workspace_id = current_user.default_workspace_id
    membership = (
        db.query(WorkspaceMember)
        .filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
        .first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Member not found")
    if membership.role == "admin":
        admin_count = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == "admin",
            )
            .count()
        )
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")
    db.delete(membership)
    db.commit()
    _log_activity(db, "member.removed", "member", user_id, user_id, workspace_id=workspace_id)

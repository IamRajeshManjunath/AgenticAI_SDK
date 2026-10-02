"""FastAPI route handlers for workspace management.

Endpoints:
  GET    /api/v1/workspaces              — list workspaces
  POST   /api/v1/workspaces              — create workspace
  GET    /api/v1/workspaces/{workspace_id} — get workspace details
  PATCH  /api/v1/workspaces/{workspace_id} — update workspace
  DELETE /api/v1/workspaces/{workspace_id} — delete workspace
  GET    /api/v1/workspaces/{workspace_id}/members — list members
  POST   /api/v1/workspaces/{workspace_id}/members — invite member
  PATCH  /api/v1/workspaces/{workspace_id}/members/{user_id} — update member role
  DELETE /api/v1/workspaces/{workspace_id}/members/{user_id} — remove member
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from passlib.context import CryptContext

from agenticai_sdk.auth.dependencies import get_current_workspace, get_current_user, require_admin
from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/workspaces", tags=["workspaces"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Request/Response Models ──────────────────────────────────────────────────


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    owner_id: Optional[str]
    created_at: str
    updated_at: Optional[str]


class InviteMemberRequest(BaseModel):
    email: str = Field(..., min_length=1)
    role: str = Field(..., pattern="^(admin|editor|viewer)$")


class UpdateMemberRoleRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|editor|viewer)$")


class MemberResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    role: str
    invited_by: Optional[str]
    created_at: str


class MemberListResponse(BaseModel):
    members: List[MemberResponse]


# ── Route Handlers ───────────────────────────────────────────────────────────


@router.get("", response_model=List[WorkspaceResponse])
async def list_workspaces(
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("workspace:read")),
):
    """List all workspaces for the current user."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Get workspaces where user is a member
    workspaces = db.query(Workspace).join(WorkspaceMember, Workspace.id == WorkspaceMember.workspace_id).filter(
        WorkspaceMember.user_id == user_id
    ).all()
    
    return [
        WorkspaceResponse(
            id=w.id,
            name=w.name,
            description=w.description,
            owner_id=w.owner_id,
            created_at=w.created_at.isoformat() if w.created_at else "",
            updated_at=w.updated_at.isoformat() if w.updated_at else "",
        )
        for w in workspaces
    ]


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    request: Request,
    body: WorkspaceCreateRequest,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("workspace:create")),
):
    """Create a new workspace."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    ws_id = str(uuid.uuid4())
    ws = Workspace(
        id=ws_id,
        name=body.name,
        description=body.description,
        owner_id=user_id,
    )
    db.add(ws)
    
    # Add creator as admin member
    member = WorkspaceMember(
        workspace_id=ws_id,
        user_id=user_id,
        role="admin",
        invited_by=user_id,
    )
    db.add(member)
    db.commit()
    db.refresh(ws)
    
    logger.info("workspace_created", workspace_id=ws_id, owner_id=user_id)
    
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        description=ws.description,
        owner_id=ws.owner_id,
        created_at=ws.created_at.isoformat() if ws.created_at else "",
        updated_at=ws.updated_at.isoformat() if ws.updated_at else "",
    )


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("workspace:read")),
):
    """Get workspace details."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check membership
    user_id = getattr(request.state, "user_id", None)
    if not db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first():
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        description=ws.description,
        owner_id=ws.owner_id,
        created_at=ws.created_at.isoformat() if ws.created_at else "",
        updated_at=ws.updated_at.isoformat() if ws.updated_at else "",
    )


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
async def update_workspace(
    workspace_id: str,
    request: Request,
    body: WorkspaceUpdateRequest,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("workspace:update")),
):
    """Update workspace details."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    if body.name is not None:
        ws.name = body.name
    if body.description is not None:
        ws.description = body.description
    
    db.commit()
    db.refresh(ws)
    
    return WorkspaceResponse(
        id=ws.id,
        name=ws.name,
        description=ws.description,
        owner_id=ws.owner_id,
        created_at=ws.created_at.isoformat() if ws.created_at else "",
        updated_at=ws.updated_at.isoformat() if ws.updated_at else "",
    )


@router.delete("/{workspace_id}")
async def delete_workspace(
    workspace_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("workspace:delete")),
):
    """Delete a workspace (admin only)."""
    ws = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    
    # Check if user is workspace admin
    user_id = getattr(request.state, "user_id", None)
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    
    if not member or member.role != "admin":
        raise HTTPException(status_code=403, detail="Only workspace admins can delete workspace")
    
    db.delete(ws)
    db.commit()
    
    return {"success": True, "message": "Workspace deleted"}


# ── Member Management ──────────────────────────────────────────────────────


@router.get("/{workspace_id}/members", response_model=MemberListResponse)
async def list_members(
    workspace_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("member:read")),
):
    """List workspace members."""
    # Check membership
    user_id = getattr(request.state, "user_id", None)
    if not db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first():
        raise HTTPException(status_code=403, detail="Not a member of this workspace")
    
    members = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id
    ).all()
    
    members_data = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            members_data.append(MemberResponse(
                user_id=user.id,
                email=user.email,
                full_name=user.full_name,
                role=m.role,
                invited_by=m.invited_by,
                created_at=m.created_at.isoformat() if m.created_at else "",
            ))
    
    return MemberListResponse(members=members_data)


@router.post("/{workspace_id}/members", response_model=MemberResponse, status_code=status.HTTP_201_CREATED)
async def invite_member(
    workspace_id: str,
    request: Request,
    body: InviteMemberRequest,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("member:invite")),
):
    """Invite a member to the workspace."""
    # Check if inviter has permission
    user_id = getattr(request.state, "user_id", None)
    inviter = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    
    if not inviter or inviter.role not in ("admin", "editor"):
        raise HTTPException(status_code=403, detail="Insufficient permissions to invite members")
    
    # Find or create user
    user = db.query(User).filter(User.email == body.email).first()
    if not user:
        user = User(
            id=str(uuid.uuid4()),
            email=body.email,
            hashed_password="",  # Will be set on first login
            full_name=body.email.split("@")[0],
        )
        db.add(user)
        db.flush()
    
    # Check if already a member
    existing = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user.id
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="User is already a member")
    
    member = WorkspaceMember(
        workspace_id=workspace_id,
        user_id=user.id,
        role=body.role,
        invited_by=user_id,
    )
    db.add(member)
    db.commit()
    
    return MemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=body.role,
        invited_by=user_id,
        created_at=member.created_at.isoformat() if member.created_at else "",
    )


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberResponse)
async def update_member_role(
    workspace_id: str,
    user_id: str,
    request: Request,
    body: UpdateMemberRoleRequest,
    db: Session = Depends(get_session),
    _: Any = Depends(require_admin),
):
    """Update member role (admin only)."""
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    member.role = body.role
    db.commit()
    
    user = db.query(User).filter(User.id == user_id).first()
    return MemberResponse(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        invited_by=member.invited_by,
        created_at=member.created_at.isoformat() if member.created_at else "",
    )


@router.delete("/{workspace_id}/members/{user_id}")
async def remove_member(
    workspace_id: str,
    user_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("member:remove")),
):
    """Remove a member from the workspace."""
    member = db.query(WorkspaceMember).filter(
        WorkspaceMember.workspace_id == workspace_id,
        WorkspaceMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    
    # Prevent removing last admin
    if member.role == "admin":
        admin_count = db.query(WorkspaceMember).filter(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.role == "admin"
        ).count()
        if admin_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last admin")
    
    db.delete(member)
    db.commit()
    
    return {"success": True, "message": "Member removed"}
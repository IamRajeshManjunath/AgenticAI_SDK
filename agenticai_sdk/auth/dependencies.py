from __future__ import annotations

import os
from typing import Any

import structlog
from fastapi import Depends, HTTPException, Request, status
import jwt
from sqlalchemy.orm import Session

from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import User, WorkspaceMember

logger = structlog.get_logger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"

_JWTError = jwt.PyJWTError


async def get_current_user(
    request: Request,
    db: Session = Depends(get_session),
) -> User:
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


async def get_current_workspace(
    request: Request,
    db: Session = Depends(get_session),
) -> str:
    workspace_id = getattr(request.state, "workspace_id", None)
    if not workspace_id:
        workspace_id = getattr(request.state, "user_default_workspace", None)
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workspace context found. Set X-Workspace-ID header or assign a default workspace.",
        )
    return workspace_id


def require_role(*roles: str):
    """FastAPI dependency: ensure current user has one of the given roles in the workspace."""

    async def _require(
        request: Request,
        db: Session = Depends(get_session),
        user: User = Depends(get_current_user),
        workspace_id: str = Depends(get_current_workspace),
    ) -> User:
        membership = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if not membership:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this workspace",
            )
        if membership.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{membership.role}' not in allowed roles: {roles}",
            )
        return user

    return _require


require_admin = require_role("admin")

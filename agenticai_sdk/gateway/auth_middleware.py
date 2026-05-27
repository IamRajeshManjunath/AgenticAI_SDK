"""
Auth middleware — validates JWT Bearer tokens and X-API-Key headers.

Attaches user_id, workspace_id to request.state on success.
Skips public paths (/auth/*, /health, /docs, /openapi.json, /redoc).
"""

from __future__ import annotations

import os
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse
from passlib.context import CryptContext

from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import ApiKey

logger = structlog.get_logger(__name__)

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"

PUBLIC_PATHS = {
    "/api/v1/auth/register",
    "/api/v1/auth/login",
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import jwt


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware that validates JWT Bearer tokens or X-API-Key headers."""

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Skip public paths
        if path in PUBLIC_PATHS or path.startswith(("/docs", "/redoc", "/openapi.json")):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        api_key_header = request.headers.get("X-API-Key", "")

        user_id = None
        workspace_id = None

        # Try Bearer token first
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("sub")
                workspace_id = payload.get("workspace_id")
            except jwt.ExpiredSignatureError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Token has expired"},
                )
            except jwt.PyJWTError:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid token"},
                )

        # Fall back to API key
        elif api_key_header:
            db = next(get_session())
            try:
                api_keys = db.query(ApiKey).filter(ApiKey.is_active == 1).all()
                for ak in api_keys:
                    if pwd_context.verify(api_key_header, ak.key_hash):
                        request.state.auth_method = "api_key"
                        workspace_id = ak.workspace_id
                        request.state.workflow_key_scope = ak.workflow_id
                        ak.last_used_at = __import__("datetime").datetime.now(
                            __import__("datetime").timezone.utc
                        )
                        db.commit()
                        break
                else:
                    return JSONResponse(
                        status_code=401,
                        content={"detail": "Invalid API key"},
                    )
            finally:
                db.close()
        else:
            return JSONResponse(
                status_code=401,
                content={"detail": "Authentication required. Provide Authorization: Bearer <token> or X-API-Key header."},
            )

        request.state.user_id = user_id
        request.state.workspace_id = workspace_id
        if workspace_id:
            request.state.user_default_workspace = workspace_id

        return await call_next(request)

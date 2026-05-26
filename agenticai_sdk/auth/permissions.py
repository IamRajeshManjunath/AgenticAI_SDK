"""
AWS IAM-style permission system for AgenticAI.

Provides:
  - Permission catalog (enum of all actions across 22 categories)
  - Policy evaluation engine (explicit Deny > Allow > implicit Deny)
  - require_permission() FastAPI dependency
  - Helper to collect policies for a principal (role + user attachments)
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import structlog
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import Policy, PolicyAttachment, User, WorkspaceMember

logger = structlog.get_logger(__name__)


# ── Permission Catalog ────────────────────────────────────────────────────────

class Permission(str, Enum):
    """Every possible action in the system, organized by category.

    Naming convention: <category>:<action>
    """

    # Workflow
    WORKFLOW_CREATE = "workflow:create"
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_UPDATE = "workflow:update"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_RUN = "workflow:run"
    WORKFLOW_EXPORT = "workflow:export"
    WORKFLOW_IMPORT = "workflow:import"

    # API Keys
    APIKEY_CREATE = "apikey:create"
    APIKEY_READ = "apikey:read"
    APIKEY_UPDATE = "apikey:update"
    APIKEY_DELETE = "apikey:delete"
    APIKEY_REGENERATE = "apikey:regenerate"

    # Members
    MEMBER_LIST = "member:list"
    MEMBER_READ = "member:read"
    MEMBER_INVITE = "member:invite"
    MEMBER_REMOVE = "member:remove"
    MEMBER_UPDATE_ROLE = "member:update-role"

    # Workspace
    WORKSPACE_READ = "workspace:read"
    WORKSPACE_UPDATE = "workspace:update"
    WORKSPACE_DELETE = "workspace:delete"
    WORKSPACE_TRANSFER = "workspace:transfer"

    # Tools
    TOOL_CREATE = "tool:create"
    TOOL_READ = "tool:read"
    TOOL_UPDATE = "tool:update"
    TOOL_DELETE = "tool:delete"
    TOOL_TEST = "tool:test"

    # RAG Sources
    RAG_CREATE = "rag:create"
    RAG_READ = "rag:read"
    RAG_UPDATE = "rag:update"
    RAG_DELETE = "rag:delete"
    RAG_INGEST = "rag:ingest"

    # Billing
    BILLING_READ = "billing:read"
    BILLING_CHECKOUT = "billing:checkout"
    BILLING_PORTAL = "billing:portal"
    BILLING_UPDATE = "billing:update"
    BILLING_CANCEL = "billing:cancel"

    # Integrations
    INTEGRATION_CREATE = "integration:create"
    INTEGRATION_READ = "integration:read"
    INTEGRATION_UPDATE = "integration:update"
    INTEGRATION_DELETE = "integration:delete"
    INTEGRATION_CONNECT = "integration:connect"
    INTEGRATION_DISCONNECT = "integration:disconnect"

    # Cron / Schedules
    CRON_CREATE = "cron:create"
    CRON_READ = "cron:read"
    CRON_UPDATE = "cron:update"
    CRON_DELETE = "cron:delete"
    CRON_PAUSE = "cron:pause"
    CRON_RESUME = "cron:resume"

    # Secrets
    SECRET_CREATE = "secret:create"
    SECRET_READ = "secret:read"
    SECRET_READ_VALUE = "secret:read-value"
    SECRET_UPDATE = "secret:update"
    SECRET_DELETE = "secret:delete"

    # Observability
    OBSERVABILITY_READ = "observability:read"
    OBSERVABILITY_EXPORT = "observability:export"
    OBSERVABILITY_DELETE = "observability:delete"

    # Execution History
    EXECUTION_READ = "execution:read"
    EXECUTION_CANCEL = "execution:cancel"
    EXECUTION_RETRY = "execution:retry"
    EXECUTION_DELETE = "execution:delete"

    # Templates
    TEMPLATE_CREATE = "template:create"
    TEMPLATE_READ = "template:read"
    TEMPLATE_UPDATE = "template:update"
    TEMPLATE_DELETE = "template:delete"
    TEMPLATE_USE = "template:use"

    # Notifications
    NOTIFICATION_CREATE = "notification:create"
    NOTIFICATION_READ = "notification:read"
    NOTIFICATION_UPDATE = "notification:update"
    NOTIFICATION_DELETE = "notification:delete"
    NOTIFICATION_TEST = "notification:test"

    # Approvals (HITL)
    APPROVAL_READ = "approval:read"
    APPROVAL_APPROVE = "approval:approve"
    APPROVAL_REJECT = "approval:reject"

    # Audit Logs
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    AUDIT_DELETE = "audit:delete"

    # Invite Links
    INVITE_CREATE = "invite:create"
    INVITE_READ = "invite:read"
    INVITE_REVOKE = "invite:revoke"

    # Roles / Policies
    ROLE_CREATE = "role:create"
    ROLE_READ = "role:read"
    ROLE_UPDATE = "role:update"
    ROLE_DELETE = "role:delete"
    ROLE_ATTACH = "role:attach"
    ROLE_DETACH = "role:detach"

    # Tags
    TAG_CREATE = "tag:create"
    TAG_READ = "tag:read"
    TAG_UPDATE = "tag:update"
    TAG_DELETE = "tag:delete"
    TAG_ASSIGN = "tag:assign"
    TAG_UNASSIGN = "tag:unassign"

    # Database Config
    DB_READ = "db:read"
    DB_CONNECT = "db:connect"
    DB_RESET = "db:reset"

    # Settings
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"

    # Admin (superuser-only)
    ADMIN_SUPERUSER = "admin:superuser"
    ADMIN_IMPERSONATE = "admin:impersonate"
    ADMIN_AUDIT_ALL = "admin:audit-all"


# ── Policy Document Constants ─────────────────────────────────────────────────

ADMIN_POLICY_DOCUMENT: dict[str, Any] = {
    "version": "1",
    "statements": [
        {"effect": "Allow", "actions": ["*"], "resources": ["*"]},
    ],
}

EDITOR_POLICY_DOCUMENT: dict[str, Any] = {
    "version": "1",
    "statements": [
        {"effect": "Allow", "actions": ["*"], "resources": ["*"]},
        {"effect": "Deny", "actions": [
            "member:invite", "member:remove", "member:update-role",
            "workspace:delete", "workspace:transfer",
            "apikey:delete", "apikey:regenerate",
            "billing:*",
            "role:*",
            "db:*",
            "secret:read-value",
            "audit:export", "audit:delete",
            "approval:approve", "approval:reject",
            "invite:*",
            "admin:*",
        ], "resources": ["*"]},
    ],
}

VIEWER_POLICY_DOCUMENT: dict[str, Any] = {
    "version": "1",
    "statements": [
        {"effect": "Allow", "actions": [
            "workflow:read", "workflow:run",
            "tool:read",
            "rag:read",
            "member:list", "member:read",
            "workspace:read",
            "apikey:read",
            "integration:read",
            "cron:read",
            "observability:read",
            "execution:read",
            "template:read",
            "notification:read",
            "approval:read",
            "audit:read",
            "tag:read",
            "settings:read",
            "secret:read",
        ], "resources": ["*"]},
    ],
}


# ── Default policy definitions (for seeding) ──────────────────────────────────

DEFAULT_ROLE_POLICIES: dict[str, tuple[str, str, dict[str, Any]]] = {
    "admin": ("Admin Full Access", "Unrestricted access to all resources", ADMIN_POLICY_DOCUMENT),
    "editor": ("Editor Access", "Full CRUD except admin & billing actions", EDITOR_POLICY_DOCUMENT),
    "viewer": ("Viewer Access", "Read-only plus workflow execution", VIEWER_POLICY_DOCUMENT),
}


# ── Pattern Matching ──────────────────────────────────────────────────────────


def _match_pattern(pattern: str, value: str) -> bool:
    """Match an action/resource pattern against a concrete value.

    Supports:
      - ``*`` — matches everything
      - ``category:*`` — matches all actions in a category (e.g. ``workflow:*``)
      - Exact string match
    """
    if pattern == "*":
        return True
    if pattern.endswith(":*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def _match_resource_pattern(pattern: str, resource: str) -> bool:
    """Match a resource ARN pattern against a concrete resource.

    Supports:
      - ``*``
      - ``workspace:{id}/*``
      - ``workspace:{id}/workflow:{wf_id}``
    """
    if pattern == "*":
        return True
    if pattern.endswith("/*"):
        return resource.startswith(pattern[:-1])
    return pattern == resource


def _statement_matches_action(actions: list[str], action: str) -> bool:
    return any(_match_pattern(a, action) for a in actions)


def _statement_matches_resource(resources: list[str], resource: str) -> bool:
    return any(_match_resource_pattern(r, resource) for r in resources)


# ── Policy Evaluation ─────────────────────────────────────────────────────────


def evaluate_policies(
    policy_documents: list[dict[str, Any]],
    action: str,
    resource: str,
) -> bool:
    """AWS IAM-style policy evaluation.

    Resolution order:
      1. Any explicit ``Deny`` → **DENY** (immediate return ``False``)
      2. Any explicit ``Allow`` → **ALLOW** (return ``True``)
      3. No match → **DENY** (return ``False``)

    Args:
        policy_documents: List of parsed policy JSON documents.
        action: The action being checked (e.g. ``"workflow:run"``).
        resource: The resource ARN (e.g. ``"workspace:{id}/workflow:{wf_id}"``).

    Returns:
        ``True`` if the action is allowed, ``False`` otherwise.
    """
    allowed = False

    for doc in policy_documents:
        for stmt in doc.get("statements", []):
            if not _statement_matches_action(stmt.get("actions", []), action):
                continue
            if not _statement_matches_resource(stmt.get("resources", []), resource):
                continue

            if stmt["effect"] == "Deny":
                return False  # Explicit deny overrides everything
            if stmt["effect"] == "Allow":
                allowed = True

    return allowed


# ── Policy Retrieval ──────────────────────────────────────────────────────────


def get_attached_policy_documents(
    db: Session,
    principal_type: str,
    principal_id: str,
) -> list[dict[str, Any]]:
    """Collect all policy documents attached to a principal.

    Args:
        db: Database session.
        principal_type: ``"user"``, ``"role"``, or ``"workspace"``.
        principal_id: The principal's identifier.

    Returns:
        List of parsed policy JSON documents.
    """
    rows = (
        db.query(Policy.policy_document)
        .join(PolicyAttachment, PolicyAttachment.policy_id == Policy.id)
        .filter(
            PolicyAttachment.principal_type == principal_type,
            PolicyAttachment.principal_id == principal_id,
        )
        .all()
    )
    return [row.policy_document for row in rows if row.policy_document]


def get_workspace_resource(workspace_id: str) -> str:
    """Build the resource ARN for all resources in a workspace."""
    return f"workspace:{workspace_id}/*"


# ── FastAPI Dependency ────────────────────────────────────────────────────────


def require_permission(*actions: str):
    """FastAPI dependency: ensure the current user has ALL specified permissions.

    Usage::

        @router.get("/workflows")
        async def list_workflows(
            user: User = Depends(require_permission("workflow:read")),
        ):
            ...

    The permission check is scoped to the authenticated user's workspace.
    Admins (via their role policy) automatically pass all checks.

    Args:
        *actions: One or more actions the caller must be allowed to perform.

    Returns:
        The authenticated ``User`` object if permitted.

    Raises:
        HTTPException 401: If not authenticated.
        HTTPException 403: If permission is denied.
    """
    async def _check(
        request: Request,
        db: Session = Depends(get_session),
        user: User = Depends(_get_current_user_internal),
        workspace_id: str = Depends(_get_workspace_id_internal),
    ) -> User:
        # Resolve member's role
        member = (
            db.query(WorkspaceMember)
            .filter(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user.id,
            )
            .first()
        )
        if not member:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this workspace",
            )

        # Collect policies: role-based + any direct user attachments
        policy_docs = get_attached_policy_documents(db, "role", member.role)
        policy_docs.extend(get_attached_policy_documents(db, "user", user.id))

        resource = get_workspace_resource(workspace_id)

        for action in actions:
            if not evaluate_policies(policy_docs, action, resource):
                logger.warning(
                    "permission_denied",
                    user_id=user.id,
                    action=action,
                    resource=resource,
                    role=member.role,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required permission: {action}",
                )

        return user

    return _check


# ── Internal helpers (avoid circular imports) ─────────────────────────────────


async def _get_current_user_internal(
    request: Request,
    db: Session = Depends(get_session),
) -> User:
    """Same as ``auth.dependencies.get_current_user`` but self-contained."""
    import uuid
    user_id = getattr(request.state, "user_id", None)
    auth_method = getattr(request.state, "auth_method", None)

    if not user_id and auth_method == "api_key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key does not have a user context — use JWT for this endpoint",
        )

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


async def _get_workspace_id_internal(request: Request) -> str:
    """Same as ``auth.dependencies.get_current_workspace`` but self-contained."""
    workspace_id = getattr(request.state, "workspace_id", None)
    if not workspace_id:
        workspace_id = getattr(request.state, "user_default_workspace", None)
    if not workspace_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No workspace context found",
        )
    return workspace_id

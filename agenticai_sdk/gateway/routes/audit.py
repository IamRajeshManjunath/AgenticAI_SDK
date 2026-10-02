"""FastAPI route handlers for audit logs.

Endpoints:
  GET /api/v1/audit              — list audit logs
  GET /api/v1/audit/{log_id}     — get audit log details
  GET /api/v1/audit/export       — export audit logs (CSV/JSON)
"""

from __future__ import annotations

import csv
import io
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agenticai_sdk.auth.dependencies import get_current_workspace
from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import AuditLog

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


# ── Request/Response Models ──────────────────────────────────────────────────


class AuditLogResponse(BaseModel):
    id: str
    workspace_id: str
    user_id: Optional[str]
    event_category: str
    event_type: str
    severity: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    resource_name: Optional[str]
    action: str
    outcome: str
    details: Dict[str, Any]
    ip_address: Optional[str]
    user_agent: Optional[str]
    request_id: Optional[str]
    session_id: Optional[str]
    created_at: str


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    page_size: int


# ── Route Handlers ───────────────────────────────────────────────────────────


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("audit:read")),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    event_category: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """List audit logs with pagination and filtering."""
    workspace_id = getattr(request.state, "workspace_id", "default")
    
    query = db.query(AuditLog).filter(AuditLog.workspace_id == workspace_id)
    
    if event_category:
        query = query.filter(AuditLog.event_category == event_category)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if severity:
        query = query.filter(AuditLog.severity == severity)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if outcome:
        query = query.filter(AuditLog.outcome == outcome)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    total = query.count()
    logs = query.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    
    return AuditLogListResponse(
        logs=[
            AuditLogResponse(
                id=log.id,
                workspace_id=log.workspace_id,
                user_id=log.user_id,
                event_category=log.event_category,
                event_type=log.event_type,
                severity=log.severity,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                resource_name=log.resource_name,
                action=log.action,
                outcome=log.outcome,
                details=log.details,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                request_id=log.request_id,
                session_id=log.session_id,
                timestamp=log.created_at.isoformat() if log.created_at else "",
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("audit:read")),
):
    """Get audit log details."""
    workspace_id = getattr(request.state, "workspace_id", "default")
    log = db.query(AuditLog).filter(
        AuditLog.id == log_id,
        AuditLog.workspace_id == workspace_id
    ).first()
    
    if not log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return AuditLogResponse(
        id=log.id,
        workspace_id=log.workspace_id,
        user_id=log.user_id,
        event_category=log.event_category,
        event_type=log.event_type,
        severity=log.severity,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        resource_name=log.resource_name,
        action=log.action,
        outcome=log.outcome,
        details=log.details,
        ip_address=log.ip_address,
        user_agent=log.user_agent,
        request_id=log.request_id,
        session_id=log.session_id,
        timestamp=log.created_at.isoformat() if log.created_at else "",
    )


@router.get("/export")
async def export_audit_logs(
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("audit:export")),
    format: str = Query("csv", pattern="^(csv|json)$"),
    event_category: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    outcome: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
):
    """Export audit logs as CSV or JSON."""
    workspace_id = getattr(request.state, "workspace_id", "default")
    
    query = db.query(AuditLog).filter(AuditLog.workspace_id == workspace_id)
    
    if event_category:
        query = query.filter(AuditLog.event_category == event_category)
    if event_type:
        query = query.filter(AuditLog.event_type == event_type)
    if severity:
        query = query.filter(AuditLog.severity == severity)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if action:
        query = query.filter(AuditLog.action == action)
    if outcome:
        query = query.filter(AuditLog.outcome == outcome)
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)
    if end_date:
        query = query.filter(AuditLog.created_at <= end_date)
    
    logs = query.order_by(AuditLog.created_at.desc()).all()
    
    if format == "csv":
        def generate_csv():
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "id", "workspace_id", "user_id", "event_category", "event_type", 
                "severity", "resource_type", "resource_id", "resource_name",
                "action", "outcome", "ip_address", "user_agent", "request_id",
                "session_id", "timestamp", "details"
            ])
            for log in logs:
                writer.writerow([
                    log.id,
                    log.workspace_id,
                    log.user_id or "",
                    log.event_category,
                    log.event_type,
                    log.severity,
                    log.resource_type or "",
                    log.resource_id or "",
                    log.resource_name or "",
                    log.action,
                    log.outcome,
                    log.ip_address or "",
                    log.user_agent or "",
                    log.request_id or "",
                    log.session_id or "",
                    log.created_at.isoformat() if log.created_at else "",
                    json.dumps(log.details) if log.details else "{}",
                ])
                yield output.getvalue()
                output.seek(0)
                output.truncate(0)
        
        return StreamingResponse(
            generate_csv(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().isoformat()}.csv"}
        )
    
    else:  # json
        return StreamingResponse(
            iter([
                json.dumps({
                    "id": log.id,
                    "workspace_id": log.workspace_id,
                    "user_id": log.user_id,
                    "event_category": log.event_category,
                    "event_type": log.event_type,
                    "severity": log.severity,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "resource_name": log.resource_name,
                    "action": log.action,
                    "outcome": log.outcome,
                    "details": log.details,
                    "ip_address": log.ip_address,
                    "user_agent": log.user_agent,
                    "request_id": log.request_id,
                    "session_id": log.session_id,
                    "timestamp": log.created_at.isoformat() if log.created_at else "",
                }) + "\n"
                for log in logs
            ]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.now().isoformat()}.jsonl"}
        )
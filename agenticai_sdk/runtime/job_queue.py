"""Database-backed workflow job queue shared by API and worker processes."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import or_, update
from sqlalchemy.orm import Session

from agenticai_sdk.db.models import WorkflowJob


class IdempotencyConflictError(ValueError):
    """An idempotency key was reused for a different execution request."""


def request_fingerprint(workflow_config: dict[str, Any], input_message: str, initial_state: dict[str, Any]) -> str:
    canonical = json.dumps(
        {"workflow": workflow_config, "input_message": input_message, "initial_state": initial_state},
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def enqueue_job(
    db: Session,
    *,
    workspace_id: str,
    workflow_id: str,
    workflow_config: dict[str, Any],
    input_message: str,
    initial_state: dict[str, Any],
    idempotency_key: str | None,
) -> tuple[WorkflowJob, bool]:
    fingerprint = request_fingerprint(workflow_config, input_message, initial_state)
    if idempotency_key:
        existing = db.query(WorkflowJob).filter(
            WorkflowJob.workspace_id == workspace_id,
            WorkflowJob.idempotency_key == idempotency_key,
        ).first()
        if existing:
            if existing.request_hash != fingerprint:
                raise IdempotencyConflictError("Idempotency key was already used with a different request.")
            return existing, False

    job = WorkflowJob(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        thread_id=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        request_hash=fingerprint,
        workflow_config=workflow_config,
        input_message=input_message,
        initial_state=initial_state,
        resume=0,
        status="pending",
        attempts=0,
    )
    db.add(job)
    try:
        db.commit()
    except Exception:
        db.rollback()
        if not idempotency_key:
            raise
        existing = db.query(WorkflowJob).filter(
            WorkflowJob.workspace_id == workspace_id,
            WorkflowJob.idempotency_key == idempotency_key,
        ).first()
        if existing is None:
            raise
        if existing.request_hash != fingerprint:
            raise IdempotencyConflictError("Idempotency key was already used with a different request.")
        return existing, False
    db.refresh(job)
    return job, True


def claim_next_job(db: Session, worker_id: str) -> WorkflowJob | None:
    """Atomically claim one pending job; conditional update is portable to SQLite."""
    candidate = (
        db.query(WorkflowJob)
        .filter(WorkflowJob.status == "pending")
        .order_by(WorkflowJob.created_at, WorkflowJob.id)
        .first()
    )
    if candidate is None:
        return None
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(WorkflowJob)
        .where(WorkflowJob.id == candidate.id, WorkflowJob.status == "pending")
        .values(
            status="running",
            worker_id=worker_id,
            claimed_at=now,
            updated_at=now,
            attempts=WorkflowJob.attempts + 1,
        )
    )
    db.commit()
    if result.rowcount != 1:
        return None
    return db.query(WorkflowJob).filter(WorkflowJob.id == candidate.id).first()


def heartbeat_job(db: Session, job_id: str, worker_id: str) -> bool:
    now = datetime.now(timezone.utc)
    result = db.execute(
        update(WorkflowJob)
        .where(
            WorkflowJob.id == job_id,
            WorkflowJob.worker_id == worker_id,
            WorkflowJob.status == "running",
        )
        .values(claimed_at=now, updated_at=now)
    )
    db.commit()
    return result.rowcount == 1


def fail_stale_jobs(db: Session, stale_before: datetime) -> int:
    """Mark expired worker leases failed; never retry side-effecting work implicitly."""
    result = db.execute(
        update(WorkflowJob)
        .where(
            WorkflowJob.status == "running",
            or_(WorkflowJob.claimed_at.is_(None), WorkflowJob.claimed_at < stale_before),
        )
        .values(
            status="failed",
            error="Worker lease expired. The job was not retried to avoid duplicate external side effects.",
            completed_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
    return result.rowcount or 0

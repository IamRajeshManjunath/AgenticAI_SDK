"""Workspace-scoped workflow job API backed by the shared SQL database."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, model_validator
from pydantic import ValidationError
from sqlalchemy import update
from sqlalchemy.orm import Session

from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session
from agenticai_sdk.db.models import User, Workflow, WorkflowJob
from agenticai_sdk.runtime.job_queue import IdempotencyConflictError, enqueue_job
from agenticai_sdk.schemas.workflow import WorkflowSchema

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/runs", tags=["runs"])


class RunRequest(BaseModel):
    workflow_id: str | None = None
    workflow: WorkflowSchema | None = None
    input_message: str = Field(..., min_length=1)
    initial_state: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_workflow_reference(self) -> "RunRequest":
        if not self.workflow_id and not self.workflow:
            raise ValueError("workflow_id or workflow is required")
        return self

    @property
    def resolved_workflow_id(self) -> str:
        if self.workflow_id:
            return self.workflow_id
        if self.workflow is None:
            raise ValueError("workflow_id or workflow is required")
        return self.workflow.workflow_id


class RunAcceptedResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str
    status_url: str
    events_url: str


class ResumeRequest(BaseModel):
    state_updates: dict[str, Any] = Field(default_factory=dict)


class RunStatusResponse(RunAcceptedResponse):
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


def _workspace_id(request: Request) -> str:
    workspace_id = getattr(request.state, "workspace_id", None)
    if not workspace_id:
        raise HTTPException(status_code=400, detail="No workspace context found")
    return workspace_id


def _response(job: WorkflowJob) -> RunStatusResponse:
    return RunStatusResponse(
        run_id=job.id,
        thread_id=job.thread_id,
        status=job.status,
        status_url=f"/api/v1/runs/{job.id}",
        events_url=f"/api/v1/runs/{job.id}/events",
        result=job.result,
        error=job.error,
        created_at=job.created_at.isoformat() if job.created_at else None,
        updated_at=job.updated_at.isoformat() if job.updated_at else None,
    )


def _get_job(db: Session, run_id: str, workspace_id: str) -> WorkflowJob:
    job = db.query(WorkflowJob).filter(
        WorkflowJob.id == run_id,
        WorkflowJob.workspace_id == workspace_id,
    ).first()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found")
    return job


@router.post("", response_model=RunAcceptedResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_run(
    request: Request,
    request_body: RunRequest,
    db: Session = Depends(get_session),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    _: User = Depends(require_permission("workflow:run")),
) -> RunAcceptedResponse:
    """Persist an execution request and return without running model calls inline."""
    workspace_id = _workspace_id(request)
    workflow_id = request_body.resolved_workflow_id
    workflow = db.query(Workflow).filter(
        Workflow.id == workflow_id,
        Workflow.workspace_id == workspace_id,
    ).first()
    if workflow is None:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not workflow.config:
        raise HTTPException(status_code=400, detail="Workflow has no saved configuration")
    try:
        validated_workflow = WorkflowSchema.model_validate(workflow.config)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc

    workflow_scope = getattr(request.state, "workflow_key_scope", None)
    if workflow_scope and workflow_scope != workflow_id:
        raise HTTPException(status_code=403, detail="API key not scoped to this workflow")

    try:
        job, created = enqueue_job(
            db,
            workspace_id=workspace_id,
            workflow_id=workflow.id,
            workflow_config=validated_workflow.model_dump(mode="json"),
            input_message=request_body.input_message,
            initial_state=request_body.initial_state,
            idempotency_key=idempotency_key,
        )
    except IdempotencyConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    if created:
        logger.info("workflow_job_queued", job_id=job.id, workflow_id=workflow_id, workspace_id=workspace_id)
    return RunAcceptedResponse(
        run_id=job.id,
        thread_id=job.thread_id,
        status=job.status,
        status_url=f"/api/v1/runs/{job.id}",
        events_url=f"/api/v1/runs/{job.id}/events",
    )


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("workflow:read")),
) -> RunStatusResponse:
    return _response(_get_job(db, run_id, _workspace_id(request)))


@router.post("/{run_id}/cancel", response_model=RunStatusResponse)
async def cancel_run(
    run_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("workflow:cancel")),
) -> RunStatusResponse:
    job = _get_job(db, run_id, _workspace_id(request))
    result = db.execute(
        update(WorkflowJob)
        .where(
            WorkflowJob.id == run_id,
            WorkflowJob.workspace_id == job.workspace_id,
            WorkflowJob.status == "pending",
        )
        .values(
            status="cancelled",
            updated_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount != 1:
        db.rollback()
        job = _get_job(db, run_id, job.workspace_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Only queued runs can be cancelled; current status is '{job.status}'.",
        )
    db.commit()
    return _response(_get_job(db, run_id, job.workspace_id))


@router.post("/{run_id}/resume", response_model=RunStatusResponse)
async def resume_run(
    run_id: str,
    body: ResumeRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("workflow:run")),
) -> RunStatusResponse:
    job = _get_job(db, run_id, _workspace_id(request))
    if job.status != "paused":
        raise HTTPException(status_code=409, detail=f"Run is not paused; current status is '{job.status}'.")
    from agenticai_sdk.runtime.job_checkpointer import durable_checkpointer

    try:
        async with durable_checkpointer() as checkpointer:
            checkpoint = await checkpointer.aget_tuple(
                {"configurable": {"thread_id": job.thread_id}}
            )
    except (ImportError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"Durable checkpoint storage is unavailable: {exc}") from exc
    if checkpoint is None:
        raise HTTPException(status_code=409, detail="No durable checkpoint exists for this run.")

    result = db.execute(
        update(WorkflowJob)
        .where(
            WorkflowJob.id == run_id,
            WorkflowJob.workspace_id == job.workspace_id,
            WorkflowJob.status == "paused",
        )
        .values(
            initial_state=body.state_updates,
            resume=1,
            status="pending",
            error=None,
            result=None,
            worker_id=None,
            claimed_at=None,
            completed_at=None,
            updated_at=datetime.now(timezone.utc),
        )
    )
    if result.rowcount != 1:
        db.rollback()
        current_job = _get_job(db, run_id, job.workspace_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Run is not paused; current status is '{current_job.status}'.",
        )
    db.commit()
    return _response(_get_job(db, run_id, job.workspace_id))


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("workflow:read")),
) -> StreamingResponse:
    workspace_id = _workspace_id(request)
    _get_job(db, run_id, workspace_id)

    async def event_generator():
        last_version: tuple[str, str | None] | None = None
        while not await request.is_disconnected():
            event_db = next(get_session())
            try:
                job = event_db.query(WorkflowJob).filter(
                    WorkflowJob.id == run_id,
                    WorkflowJob.workspace_id == workspace_id,
                ).first()
                if job is None:
                    yield "event: error\ndata: {\"detail\":\"Run not found\"}\n\n"
                    return
                updated = job.updated_at
                if updated and updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                version = (job.status, updated.isoformat() if updated else None)
                if version != last_version:
                    payload = _response(job).model_dump(mode="json")
                    yield f"event: status\ndata: {json.dumps(payload)}\n\n"
                    last_version = version
                if job.status in {"completed", "failed", "cancelled", "paused"}:
                    return
            finally:
                event_db.close()
            await asyncio.sleep(1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

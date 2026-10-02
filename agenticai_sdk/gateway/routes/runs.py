"""FastAPI route handlers for workflow run management.

Endpoints:
  POST /api/v1/runs              — execute a workflow (with idempotency)
  GET  /api/v1/runs/{run_id}     — get run status and results
  POST /api/v1/runs/{run_id}/cancel — cancel a running workflow
  POST /api/v1/runs/{run_id}/resume — resume a paused workflow
  GET  /api/v1/runs/{run_id}/events — stream execution events (SSE)
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agenticai_sdk.auth.dependencies import get_current_workspace
from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session, Workspace
from agenticai_sdk.db.models import WorkflowRun
from agenticai_sdk.runtime import RunManager
from agenticai_sdk.runtime.orchestrator import Orchestrator
from agenticai_sdk.compiler import Compiler
from agenticai_sdk.schemas.workflow import WorkflowSchema

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/runs", tags=["runs"])

_orchestrator = Orchestrator()
_compiler = Compiler()


# ── Request/Response Models ──────────────────────────────────────────────────


class RunRequest(BaseModel):
    workflow: WorkflowSchema = Field(...)
    input_message: str = Field(..., min_length=1)
    thread_id: Optional[str] = None
    initial_state: Optional[Dict[str, Any]] = None
    workflow_revision_id: Optional[str] = None


class RunResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str
    messages: List[Dict[str, Any]]
    scratchpad: Dict[str, Any]
    retrieved_context: List[Dict[str, Any]]
    inner_thoughts: List[Dict[str, Any]]
    next_step: Optional[str]
    duration_ms: int
    token_usage: Dict[str, Any]
    checkpoint_id: Optional[str]


class RunStatusResponse(BaseModel):
    run_id: str
    thread_id: str
    status: str
    checkpoint_id: Optional[str]
    current_node: Optional[str]
    iteration: int
    created_at: Optional[str]


class ResumeRequest(BaseModel):
    state_updates: Optional[Dict[str, Any]] = None


# ── Helper Functions ─────────────────────────────────────────────────────────


def get_if_match(request: Request) -> Optional[str]:
    """Extract If-Match header for optimistic concurrency."""
    return request.headers.get("If-Match")


def get_idempotency_key(request: Request) -> Optional[str]:
    """Extract Idempotency-Key header for execution deduplication."""
    return request.headers.get("Idempotency-Key")


def check_if_match(if_match: Optional[str], current_revision: int) -> None:
    """Validate If-Match header against current revision."""
    if if_match is None:
        return
    try:
        expected = int(if_match.strip('"'))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid If-Match header: {if_match}. Must be integer revision number."
        )
    if expected != current_revision:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "WORKFLOW_REVISION_CONFLICT",
                "message": "Workflow was modified by another operation.",
                "request_id": str(uuid.uuid4()),
                "details": {
                    "expected_revision": expected,
                    "current_revision": current_revision
                }
            }
        )


def check_idempotency_key(db: Session, idempotency_key: Optional[str], workspace_id: str) -> Optional[str]:
    """Check if idempotency key was already used."""
    if not idempotency_key:
        return None
    existing = db.query(WorkflowRun).filter(
        WorkflowRun.workspace_id == workspace_id,
        WorkflowRun.idempotency_key == idempotency_key
    ).first()
    if existing:
        return existing.id
    return None


def _serialize_messages(messages: list) -> list[dict[str, Any]]:
    serialized = []
    for msg in messages:
        entry: dict[str, Any] = {
            "type": getattr(msg, "type", type(msg).__name__.lower()),
            "content": getattr(msg, "content", str(msg)),
        }
        if hasattr(msg, "tool_calls") and msg.tool_calls:
            entry["tool_calls"] = msg.tool_calls
        if hasattr(msg, "additional_kwargs") and msg.additional_kwargs:
            entry["additional_kwargs"] = msg.additional_kwargs
        serialized.append(entry)
    return serialized


# ── Route Handlers ───────────────────────────────────────────────────────────


@router.post("", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    request: Request,
    request_body: RunRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    _: Any = Depends(require_permission("workflow:run")),
):
    """Execute a workflow with idempotency and checkpointing."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    log = logger.bind(request_id=request_id)

    db = next(get_session())
    try:
        workspace_id = getattr(request.state, "workspace_id", "default")

        # Check idempotency key
        existing_run_id = check_idempotency_key(db, idempotency_key, workspace_id)
        if existing_run_id:
            log.info("idempotent_request_detected", existing_run_id=existing_run_id)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "IDEMPOTENCY_KEY_EXISTS",
                    "message": "Request with this Idempotency-Key has already been processed.",
                    "existing_run_id": existing_run_id
                }
            )

        # Get workflow
        workflow_scope = getattr(request.state, "workflow_key_scope", None)
        if workflow_scope:
            wf_id = workflow_scope
        elif request_body.workflow.workflow_id:
            wf_id = request_body.workflow.workflow_id
        else:
            raise HTTPException(status_code=400, detail="workflow_id required")

        log = log.bind(workflow_id=wf_id)
        wf = db.query(Workflow).filter(Workflow.id == wf_id, Workflow.workspace_id == request.state.workspace_id).first()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        if not wf.config:
            raise HTTPException(status_code=400, detail="Workflow has no config — compile it first")

        # Check idempotency key for workflow run
        if idempotency_key:
            existing_run = db.query(WorkflowRun).filter(
                WorkflowRun.workspace_id == workspace_id,
                WorkflowRun.idempotency_key == idempotency_key
            ).first()
            if existing_run:
                log.info("idempotent_run_detected", existing_run_id=existing_run.id)
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "code": "IDEMPOTENCY_KEY_EXISTS",
                        "message": "Request with this Idempotency-Key has already been processed.",
                        "existing_run_id": existing_run.id
                    }
                )

        schema = WorkflowSchema(**wf.config)
        input_message = request_body.input_message
        thread_id = request_body.thread_id or str(uuid.uuid4())
        scratchpad = request_body.initial_state.get("scratchpad", {}) if request_body.initial_state else {}

        log.info("run_started", thread_id=thread_id, input_preview=input_message[:100])

        # Execute with checkpointing
        from agenticai_sdk.runtime import RunManager
        run_manager = RunManager(Orchestrator(), Compiler())
        result = await run_manager.run(
            workflow=WorkflowSchema(**wf.config),
            input_message=input_message,
            thread_id=thread_id,
            initial_state={"scratchpad": scratchpad} if scratchpad else None,
            workflow_revision_id=request_body.workflow_revision_id,
        )

        # Record run in database
        run_id = str(uuid.uuid4())
        run_record = WorkflowRun(
            id=run_id,
            workspace_id=workspace_id,
            workflow_id=wf.id,
            thread_id=thread_id,
            status="completed",
            idempotency_key=idempotency_key,
            input={"input_message": input_message, "thread_id": thread_id},
            output={"status": "completed", "messages_count": len(result.get("messages", []))},
            duration_ms=result.get("duration_ms", 0),
            total_input_tokens=result.get("token_usage", {}).get("input_tokens", 0),
            total_output_tokens=result.get("token_usage", {}).get("output_tokens", 0),
            total_cost_usd=0.0,
        )
        db.add(run_record)
        db.commit()

        return RunResponse(
            run_id=run_id,
            thread_id=result["thread_id"],
            status=result["status"],
            messages=result["messages"],
            scratchpad=result["scratchpad"],
            retrieved_context=result["retrieved_context"],
            inner_thoughts=result["inner_thoughts"],
            next_step=result.get("next_step"),
            duration_ms=result.get("duration_ms", 0),
            token_usage=result.get("token_usage", {}),
            checkpoint_id=result.get("checkpoint_id"),
        )

    except HTTPException:
        raise
    except Exception as exc:
        log.error("run_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Workflow execution failed: {exc}")
    finally:
        db.close()


@router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    request: Request,
    _: Any = Depends(require_permission("workflow:read")),
):
    """Get current run status from checkpoint."""
    # For now, return basic status - would integrate with RunManager for full status
    db = next(get_session())
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        return RunStatusResponse(
            run_id=run.id,
            thread_id=run.thread_id,
            status=run.status,
            checkpoint_id=None,  # Would come from checkpoint
            current_node=None,
            iteration=0,
            created_at=run.created_at.isoformat() if run.created_at else None,
        )
    finally:
        db.close()


@router.post("/{run_id}/cancel", response_model=Dict[str, Any])
async def cancel_run(
    run_id: str,
    request: Request,
    _: Any = Depends(require_permission("workflow:cancel")),
):
    """Cancel a running workflow."""
    db = next(get_session())
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        run.status = "cancelled"
        db.commit()
        
        return {"success": True, "message": "Run cancelled"}
    finally:
        db.close()


@router.post("/{run_id}/resume", response_model=RunResponse)
async def resume_run(
    run_id: str,
    request_body: ResumeRequest,
    request: Request,
    _: Any = Depends(require_permission("workflow:run")),
):
    """Resume a paused workflow from checkpoint."""
    db = next(get_session())
    try:
        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        
        wf = db.query(Workflow).filter(Workflow.id == run.workflow_id).first()
        if not wf:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        if not wf.config:
            raise HTTPException(status_code=400, detail="Workflow has no config")
        
        schema = WorkflowSchema(**wf.config)
        
        from agenticai_sdk.runtime import RunManager
        run_manager = RunManager(Orchestrator(), Compiler())
        result = await run_manager.resume(
            thread_id=run.thread_id,
            workflow=WorkflowSchema(**wf.config),
            state_updates=request_body.state_updates,
        )
        
        return RunResponse(
            run_id=run_id,
            thread_id=result["thread_id"],
            status=result["status"],
            messages=result["messages"],
            scratchpad=result["scratchpad"],
            retrieved_context=result["retrieved_context"],
            inner_thoughts=result["inner_thoughts"],
            next_step=result.get("next_step"),
            duration_ms=result.get("duration_ms", 0),
            token_usage=result.get("token_usage", {}),
            checkpoint_id=result.get("checkpoint_id"),
        )
    finally:
        db.close()


@router.get("/{run_id}/events")
async def stream_run_events(
    run_id: str,
    request: Request,
    _: Any = Depends(require_permission("workflow:read")),
):
    """Stream execution events via SSE."""
    from fastapi.responses import StreamingResponse
    
    async def event_generator():
        # This would stream events from the run's checkpoint
        # For now, return a placeholder
        yield f"data: {{\"type\": \"status\", \"status\": \"running\"}}\n\n"
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")


# Register the router
# Note: This needs to be added to gateway/routes/__init__.py
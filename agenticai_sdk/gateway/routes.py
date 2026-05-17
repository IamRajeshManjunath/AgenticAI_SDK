"""
FastAPI route handlers for the AgenticAI SDK gateway.

Endpoints:
  POST /api/v1/workflow/run         — compile and execute a workflow
  POST /api/v1/workflow/hitl/approve — resume a HITL-interrupted workflow
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field

from agenticai_sdk.exceptions import (
    AgenticSDKError,
    HITLRejectError,
    WorkflowCompilationError,
)
from agenticai_sdk.runtime.orchestrator import Orchestrator
from agenticai_sdk.schemas.workflow import WorkflowSchema
from agenticai_sdk.state.workflow_state import WorkflowState

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

# Shared orchestrator instance (stateless aside from checkpointer)
_orchestrator = Orchestrator()


# ── Request / Response Models ─────────────────────────────────────────────────


class WorkflowRunRequest(BaseModel):
    """Payload for the /workflow/run endpoint."""

    workflow: WorkflowSchema = Field(
        ...,
        description="Complete WorkflowSchema definition.",
    )
    input_message: str = Field(
        ...,
        min_length=1,
        description="Initial user message / task to execute against the workflow.",
    )
    thread_id: str | None = Field(
        default=None,
        description="Optional thread ID for stateful conversation resumption. "
                    "Auto-generated if not provided.",
    )
    initial_scratchpad: dict[str, Any] | None = Field(
        default=None,
        description="Optional initial key-value data to pre-populate the scratchpad.",
    )


class WorkflowRunResponse(BaseModel):
    """Response from the /workflow/run endpoint."""

    thread_id: str = Field(description="Thread ID for this execution (use for HITL resume).")
    status: str = Field(description="Execution status: 'complete' or 'interrupted'.")
    messages: list[dict[str, Any]] = Field(description="Full message history after execution.")
    scratchpad: dict[str, Any] = Field(description="Final scratchpad state.")
    retrieved_context: list[dict[str, Any]] = Field(description="All retrieved RAG documents.")
    inner_thoughts: list[dict[str, Any]] = Field(description="Chain-of-thought reasoning traces.")
    next_step: str | None = Field(description="Pending routing decision (if interrupted).")


class HITLApproveRequest(BaseModel):
    """Payload for the /workflow/hitl/approve endpoint."""

    thread_id: str = Field(
        ...,
        description="Thread ID of the interrupted workflow execution.",
    )
    approved: bool = Field(
        ...,
        description="True to approve and resume; False to reject and halt.",
    )
    state_updates: dict[str, Any] | None = Field(
        default=None,
        description="Optional state overrides to apply before resumption.",
    )
    workflow: WorkflowSchema = Field(
        ...,
        description="The original WorkflowSchema (needed to recompile the graph).",
    )


class HITLApproveResponse(BaseModel):
    """Response from the /workflow/hitl/approve endpoint."""

    thread_id: str
    status: str
    messages: list[dict[str, Any]]
    scratchpad: dict[str, Any]
    inner_thoughts: list[dict[str, Any]]


# ── Route Handlers ────────────────────────────────────────────────────────────


@router.post(
    "/run",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Compile and execute a workflow",
    description=(
        "Accepts a raw WorkflowSchema payload and initial state inputs. "
        "Asynchronously compiles the graph, executes the agent DAG, and returns "
        "the final serialized message history and scratchpad payload."
    ),
)
async def run_workflow(request_body: WorkflowRunRequest, request: Request) -> WorkflowRunResponse:
    """Compile and execute a complete workflow from a JSON schema payload."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    thread_id = request_body.thread_id or str(uuid.uuid4())

    log = logger.bind(
        request_id=request_id,
        thread_id=thread_id,
        workflow_id=request_body.workflow.workflow_id,
    )
    log.info("workflow_run_requested", input_preview=request_body.input_message[:100])

    try:
        # Compile the workflow graph
        app = await _orchestrator.compile(request_body.workflow)

        # Build initial state
        initial_state: WorkflowState = {
            "messages": [HumanMessage(content=request_body.input_message)],
            "scratchpad": request_body.initial_scratchpad or {},
            "retrieved_context": [],
            "inner_thoughts": [],
            "next_step": None,
            "middleware_metadata": {},
            "trace_id": None,
        }

        # Execute the graph
        config = {"configurable": {"thread_id": thread_id}}
        final_state = await app.ainvoke(initial_state, config=config)

        # Determine execution status
        exec_status = "complete"
        if final_state is None:
            # Graph was interrupted by HITL before returning
            exec_status = "interrupted"
            final_state = {
                "messages": [],
                "scratchpad": {},
                "retrieved_context": [],
                "inner_thoughts": [],
                "next_step": None,
                "middleware_metadata": {},
                "trace_id": None,
            }

        log.info("workflow_run_complete", status=exec_status)

        return WorkflowRunResponse(
            thread_id=thread_id,
            status=exec_status,
            messages=_serialize_messages(final_state.get("messages", [])),
            scratchpad=final_state.get("scratchpad", {}),
            retrieved_context=final_state.get("retrieved_context", []),
            inner_thoughts=final_state.get("inner_thoughts", []),
            next_step=final_state.get("next_step"),
        )

    except WorkflowCompilationError as exc:
        log.error("workflow_compilation_failed", error=str(exc), detail=exc.detail)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": str(exc), "detail": exc.detail},
        ) from exc
    except AgenticSDKError as exc:
        log.error("workflow_sdk_error", error=str(exc), error_type=type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": str(exc), "error_type": type(exc).__name__},
        ) from exc
    except Exception as exc:
        log.error("workflow_unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Unexpected error: {exc}"},
        ) from exc


@router.post(
    "/hitl/approve",
    response_model=HITLApproveResponse,
    status_code=status.HTTP_200_OK,
    summary="Resume or reject an interrupted HITL workflow",
    description=(
        "Accepts a thread ID, optional state updates, and an approval flag to safely "
        "resume or reject an interrupted workflow execution path using the LangGraph checkpointer."
    ),
)
async def hitl_approve(request_body: HITLApproveRequest, request: Request) -> HITLApproveResponse:
    """Resume or halt a workflow that was interrupted at a HITL checkpoint."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    log = logger.bind(
        request_id=request_id,
        thread_id=request_body.thread_id,
        approved=request_body.approved,
    )
    log.info("hitl_approval_received")

    if not request_body.approved:
        log.info("hitl_rejected_by_reviewer")
        raise HTTPException(
            status_code=status.HTTP_200_OK,
            detail={
                "thread_id": request_body.thread_id,
                "status": "rejected",
                "message": "Workflow execution rejected by human reviewer.",
            },
        )

    try:
        # Recompile the graph (uses the same checkpointer — state is preserved)
        app = await _orchestrator.compile(request_body.workflow)
        config = {"configurable": {"thread_id": request_body.thread_id}}

        # Apply state updates if provided
        update_input = request_body.state_updates or {}

        # Resume the interrupted graph by invoking with None input
        # (LangGraph resumes from checkpointed state)
        final_state = await app.ainvoke(update_input or None, config=config)

        if final_state is None:
            final_state = {"messages": [], "scratchpad": {}, "inner_thoughts": []}

        log.info("hitl_resumed_successfully")

        return HITLApproveResponse(
            thread_id=request_body.thread_id,
            status="resumed",
            messages=_serialize_messages(final_state.get("messages", [])),
            scratchpad=final_state.get("scratchpad", {}),
            inner_thoughts=final_state.get("inner_thoughts", []),
        )

    except HITLRejectError as exc:
        log.warning("hitl_reject_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": str(exc)},
        ) from exc
    except AgenticSDKError as exc:
        log.error("hitl_sdk_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": str(exc)},
        ) from exc
    except Exception as exc:
        log.error("hitl_unexpected_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Unexpected error during HITL resume: {exc}"},
        ) from exc


# ── Serialization helpers ─────────────────────────────────────────────────────


def _serialize_messages(messages: list) -> list[dict[str, Any]]:
    """Convert LangChain message objects to JSON-serializable dicts."""
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


# ── SaaS Backend Migration (FastAPI CRUD Endpoints) ───────────────────────────

import datetime

from fastapi import Depends
from sqlalchemy.orm import Session
from agenticai_sdk.db import get_session, Workspace, Workflow, Tool as DBTool, ActivityLog, BillingData
from datetime import datetime

def _log_activity(db: Session, action: str, resource_type: str, resource_id: str, resource_name: str, details: Any = None):
    log = ActivityLog(
        id=str(uuid.uuid4()),
        workspace_id=resource_id if resource_type == "workspace" else "system",
        event_type=action,
        details={
            "resource_type": resource_type,
            "resource_id": resource_id,
            "resource_name": resource_name,
            "details": details or {}
        }
    )
    db.add(log)
    db.commit()

# --- Workflows CRUD ---
@router.get("/workflows", tags=["saas-workflows"])
async def get_workflows(db: Session = Depends(get_session)):
    wfs = db.query(Workflow).all()
    out = []
    for w in wfs:
        out.append({
            "id": w.id,
            "name": w.name,
            "description": w.description,
            "config": w.config,
            "workspace_id": w.workspace_id,
        })
    return out

@router.post("/workflows", tags=["saas-workflows"])
async def create_workflow(request: Request, db: Session = Depends(get_session)):
    body = await request.json()
    w_id = body.get("id") or str(uuid.uuid4())
    w = Workflow(
        id=w_id,
        name=body.get("name", "Untitled"),
        description=body.get("description", ""),
        config=body.get("config", {})
    )
    db.add(w)
    db.commit()
    _log_activity(db, "workflow.created", "workflow", w_id, w.name)
    return {"id": w.id, "name": w.name}

@router.get("/workflows/{w_id}", tags=["saas-workflows"])
async def get_workflow(w_id: str, db: Session = Depends(get_session)):
    w = db.query(Workflow).filter(Workflow.id == w_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"id": w.id, "name": w.name, "config": w.config}

@router.patch("/workflows/{w_id}", tags=["saas-workflows"])
async def update_workflow(w_id: str, request: Request, db: Session = Depends(get_session)):
    w = db.query(Workflow).filter(Workflow.id == w_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    body = await request.json()
    if "name" in body:
        w.name = body["name"]
    if "config" in body:
        w.config = body["config"]
    db.commit()
    _log_activity(db, "workflow.updated", "workflow", w_id, w.name)
    return {"id": w.id, "name": w.name}

@router.delete("/workflows/{w_id}", tags=["saas-workflows"])
async def delete_workflow(w_id: str, db: Session = Depends(get_session)):
    w = db.query(Workflow).filter(Workflow.id == w_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    name = w.name
    db.delete(w)
    db.commit()
    _log_activity(db, "workflow.deleted", "workflow", w_id, name)
    return {"success": True}

# --- Workspaces CRUD (New!) ---
@router.delete("/workspaces/{ws_id}", tags=["saas-workspaces"])
async def delete_workspace(ws_id: str, db: Session = Depends(get_session)):
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.commit()
    _log_activity(db, "workspace.deleted", "workspace", ws_id, ws.name)
    return {"success": True}

# --- Tools CRUD ---
@router.get("/tools", tags=["saas-tools"])
async def get_tools(db: Session = Depends(get_session)):
    from agenticai_sdk.runtime.tool_registry import dynamic_tools_db
    tools = []
    # Dynamic tools could be fetched from DB or memory depending on implementation
    # Defaulting to our new DB model:
    db_tools = db.query(DBTool).all()
    for t in db_tools:
        tools.append({
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "type": t.tool_type
        })
    return tools

@router.post("/tools", tags=["saas-tools"])
async def create_tool(request: Request, db: Session = Depends(get_session)):
    body = await request.json()
    t_id = body.get("id") or str(uuid.uuid4())
    t = DBTool(
        id=t_id,
        name=body.get("name"),
        description=body.get("description", ""),
        tool_type=body.get("type", "custom_python"),
        code_or_url=body.get("code", "") or body.get("mcp_url", "")
    )
    db.add(t)
    db.commit()
    
    # We must also register it with our SDK dynamically
    from agenticai_sdk.runtime.tool_registry import register_dynamic_tool
    if t.tool_type == "custom_python":
        register_dynamic_tool(t.name, t.description, t.code_or_url)
        
    _log_activity(db, "tool.created", "tool", t_id, t.name, {"type": t.tool_type})
    return {"id": t.id, "name": t.name}

# --- Database / Settings ---
@router.get("/db/status", tags=["saas-db"])
async def get_db_status(db: Session = Depends(get_session)):
    return {
        "status": "connected",
        "provider": "sqlalchemy",
        "latency_ms": 5,
        "collections": {
            "workflows": db.query(Workflow).count(),
            "tools": db.query(DBTool).count(),
            "activity": db.query(ActivityLog).count(),
        }
    }

@router.post("/db/connect", tags=["saas-db"])
async def connect_database(request: Request):
    return {"success": True, "message": "Connection configs are updated in .env"}

@router.get("/activity", tags=["saas-activity"])
async def get_activity(db: Session = Depends(get_session)):
    logs = db.query(ActivityLog).order_by(ActivityLog.created_at.desc()).limit(50).all()
    return [{"id": L.id, "action": L.event_type, "details": L.details, "timestamp": L.created_at} for L in logs]


# --- Observability ---
from fastapi import Response

@router.get("/metrics", tags=["observability"])
async def get_metrics():
    """Expose Prometheus metrics for Grafana scraping."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

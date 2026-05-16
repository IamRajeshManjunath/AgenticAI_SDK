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

# In-memory database mock to replace Next.js API/DB layer
SaaS_DB = {
    "workflows": {},
    "tools": {},
    "rag": {},
    "executions": {},
    "activity": []
}

def _log_activity(action: str, resource_type: str, resource_id: str, resource_name: str, details: Any = None):
    SaaS_DB["activity"].insert(0, {
        "id": str(uuid.uuid4()),
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "resource_name": resource_name,
        "details": details
    })


# --- Workflows CRUD ---
@router.get("/workflows", tags=["saas-workflows"])
async def get_workflows():
    return list(SaaS_DB["workflows"].values())

@router.post("/workflows", tags=["saas-workflows"])
async def create_workflow(request: Request):
    body = await request.json()
    w_id = str(uuid.uuid4())
    workflow = {
        "id": w_id,
        "name": body.get("name", "Untitled Workflow"),
        "description": body.get("description"),
        "status": body.get("status", "draft"),
        "nodes": body.get("nodes", []),
        "edges": body.get("edges", []),
        "user_id": "user-1",
        "settings": body.get("settings", {})
    }
    SaaS_DB["workflows"][w_id] = workflow
    _log_activity("workflow.created", "workflow", w_id, workflow["name"])
    return workflow

@router.get("/workflows/{w_id}", tags=["saas-workflows"])
async def get_workflow(w_id: str):
    if w_id not in SaaS_DB["workflows"]:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return SaaS_DB["workflows"][w_id]

@router.patch("/workflows/{w_id}", tags=["saas-workflows"])
async def update_workflow(w_id: str, request: Request):
    if w_id not in SaaS_DB["workflows"]:
        raise HTTPException(status_code=404, detail="Workflow not found")
    body = await request.json()
    SaaS_DB["workflows"][w_id].update(body)
    _log_activity("workflow.updated", "workflow", w_id, SaaS_DB["workflows"][w_id]["name"])
    return SaaS_DB["workflows"][w_id]

@router.delete("/workflows/{w_id}", tags=["saas-workflows"])
async def delete_workflow(w_id: str):
    if w_id not in SaaS_DB["workflows"]:
        raise HTTPException(status_code=404, detail="Workflow not found")
    name = SaaS_DB["workflows"][w_id]["name"]
    del SaaS_DB["workflows"][w_id]
    _log_activity("workflow.deleted", "workflow", w_id, name)
    return {"success": True}


# --- Tools CRUD ---
@router.get("/tools", tags=["saas-tools"])
async def get_tools():
    return list(SaaS_DB["tools"].values())

@router.post("/tools", tags=["saas-tools"])
async def create_tool(request: Request):
    body = await request.json()
    t_id = str(uuid.uuid4())
    tool = {
        "id": t_id,
        "name": body.get("name"),
        "description": body.get("description", ""),
        "type": body.get("type"),
        "schema": body.get("schema", {"input": {}, "output": {}}),
        "config": body.get("config", {}),
        "is_active": body.get("is_active", True),
        "user_id": "user-1"
    }
    SaaS_DB["tools"][t_id] = tool
    _log_activity("tool.created", "tool", t_id, tool["name"], {"type": tool["type"]})
    return tool


# --- RAG CRUD ---
@router.get("/rag", tags=["saas-rag"])
async def get_rag_sources():
    return list(SaaS_DB["rag"].values())

@router.post("/rag", tags=["saas-rag"])
async def create_rag_source(request: Request):
    body = await request.json()
    r_id = str(uuid.uuid4())
    rag = {
        "id": r_id,
        "name": body.get("name"),
        "description": body.get("description", ""),
        "provider": body.get("provider"),
        "config": body.get("config", {}),
        "is_active": body.get("is_active", True),
        "user_id": "user-1"
    }
    SaaS_DB["rag"][r_id] = rag
    _log_activity("rag.created", "rag", r_id, rag["name"], {"provider": rag["provider"]})
    return rag


# --- Executions CRUD ---
@router.get("/executions", tags=["saas-executions"])
async def get_executions():
    return list(SaaS_DB["executions"].values())

@router.post("/executions", tags=["saas-executions"])
async def create_execution(request: Request):
    body = await request.json()
    e_id = str(uuid.uuid4())
    execution = {
        "id": e_id,
        "workflow_id": body.get("workflow_id"),
        "status": body.get("status", "running"),
        "started_at": datetime.datetime.utcnow().isoformat() + "Z",
        "inputs": body.get("inputs", {}),
        "user_id": "user-1"
    }
    SaaS_DB["executions"][e_id] = execution
    _log_activity("execution.started", "execution", e_id, f"Execution {e_id}")
    return execution


# --- Activity & DB Status ---
@router.get("/activity", tags=["saas-activity"])
async def get_activity():
    return SaaS_DB["activity"]

@router.post("/activity", tags=["saas-activity"])
async def create_activity(request: Request):
    body = await request.json()
    _log_activity(
        action=body.get("action", "unknown"),
        resource_type=body.get("resource_type", "system"),
        resource_id=body.get("resource_id", "none"),
        resource_name=body.get("resource_name", "Unknown"),
        details=body.get("details")
    )
    return {"success": True}

@router.get("/db/status", tags=["saas-db"])
async def get_db_status():
    return {
        "status": "connected",
        "provider": SaaS_DB.get("provider", "in-memory"),
        "latency_ms": 12,
        "collections": {
            "workflows": len(SaaS_DB["workflows"]),
            "tools": len(SaaS_DB["tools"]),
            "rag": len(SaaS_DB["rag"]),
            "executions": len(SaaS_DB["executions"]),
            "activity": len(SaaS_DB["activity"])
        }
    }

@router.post("/db/connect", tags=["saas-db"])
async def connect_database(request: Request):
    """Update DB connection settings (e.g. Postgres, Cloud Provider)."""
    body = await request.json()
    provider = body.get("provider", "in-memory")
    uri = body.get("uri", "")
    
    # In a real implementation, you would initialize the SQLAlchemy/Redis pool here.
    SaaS_DB["provider"] = provider
    SaaS_DB["uri"] = uri
    
    _log_activity("db.connected", "system", provider, f"Connected to {provider} Database")
    
    return {
        "success": True,
        "message": f"Successfully connected to {provider}",
        "provider": provider
    }

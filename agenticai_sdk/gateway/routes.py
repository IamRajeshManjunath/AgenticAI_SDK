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

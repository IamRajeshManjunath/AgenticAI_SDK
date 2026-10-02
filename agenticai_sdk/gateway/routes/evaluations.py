"""FastAPI route handlers for evaluations.

Endpoints:
  POST   /api/v1/evaluations              — run evaluation
  GET    /api/v1/evaluations              — list evaluations
  GET    /api/v1/evaluations/{eval_id}    — get evaluation details
  POST   /api/v1/evaluations/run          — run evaluation for a workflow
"""

from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from io import StringIO

from agenticai_sdk.auth.dependencies import get_current_workspace
from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session
from agenticai_sdk.evaluation import WorkflowEvaluator, ResponseQualityEvaluator
from agenticai_sdk.schemas.workflow import WorkflowSchema
from agenticai_sdk.runtime import RunManager, Orchestrator
from agenticai_sdk.compiler import Compiler
from langchain_core.messages import HumanMessage

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/evaluations", tags=["evaluations"])


# ── Request/Response Models ──────────────────────────────────────────────────


class EvaluationRunRequest(BaseModel):
    workflow: WorkflowSchema = Field(...)
    input_message: str = Field(..., min_length=1)
    ground_truth: Optional[str] = None
    thread_id: Optional[str] = None
    initial_state: Optional[Dict[str, Any]] = None


class EvaluationRunResponse(BaseModel):
    evaluation_id: str
    status: str
    quality_score: float
    metrics: Dict[str, float]
    details: Dict[str, Any]


class EvaluationListResponse(BaseModel):
    evaluations: List[Dict[str, Any]]


class EvaluationDetailResponse(BaseModel):
    evaluation_id: str
    workflow_id: str
    status: str
    quality_score: float
    metrics: Dict[str, float]
    details: Dict[str, Any]
    created_at: str
    completed_at: Optional[str]


# ── Route Handlers ───────────────────────────────────────────────────────────


@router.post("/run", response_model=EvaluationRunResponse, status_code=status.HTTP_201_CREATED)
async def run_evaluation(
    request_body: EvaluationRunRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("evaluation:run")),
):
    """Run an evaluation for a workflow."""
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    log = logger.bind(request_id=request_id)
    
    try:
        workspace_id = getattr(request.state, "workspace_id", "default")
        
        # Compile workflow
        compiler = Compiler()
        compilation = compiler.compile(config_dict=request_body.workflow.model_dump())
        if not compilation.success:
            raise HTTPException(status_code=422, detail={"errors": compilation.errors})
        
        # Execute workflow
        graph = compilation.graph
        initial_state = {
            "messages": [HumanMessage(content=request_body.input_message)],
            "scratchpad": request_body.initial_state.get("scratchpad", {}) if request_body.initial_state else {},
            "retrieved_context": [],
            "inner_thoughts": [],
            "next_step": None,
            "middleware_metadata": {},
            "trace_id": str(uuid.uuid4()),
        }
        
        config = {"configurable": {"thread_id": request_body.thread_id or str(uuid.uuid4())}}
        final_state = await compilation.graph.ainvoke(initial_state, config=config)
        
        # Run evaluation
        evaluator = WorkflowEvaluator()
        quality_eval = ResponseQualityEvaluator()
        
        # Evaluate response quality
        response_text = final_state.get("messages", [])[-1].content if final_state.get("messages") else ""
        
        quality_result = quality_eval.evaluate(
            query=request_body.input_message,
            response=response_text,
            ground_truth=request_body.ground_truth,
        )
        
        # Full workflow evaluation
        eval_result = evaluator.evaluate_workflow(
            workflow_id=str(uuid.uuid4()),
            input_data={"input_message": request_body.input_message},
            output_data=final_state,
            ground_truth=request_body.ground_truth,
        )
        
        eval_id = str(uuid.uuid4())
        
        return EvaluationRunResponse(
            evaluation_id=eval_id,
            status="completed",
            quality_score=quality_result.overall_score,
            metrics={
                "relevance": quality_result.relevance,
                "coherence": quality_result.coherence,
                "groundedness": quality_result.groundedness,
                "faithfulness": quality_result.faithfulness,
                "completeness": quality_result.completeness,
                "conciseness": quality_result.conciseness,
            },
            details=eval_result.details,
        )
        
    except HTTPException:
        raise
    except Exception as exc:
        log.error("evaluation_failed", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Evaluation failed: {exc}")


@router.get("", response_model=EvaluationListResponse)
async def list_evaluations(
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("evaluation:read")),
):
    """List evaluations for the workspace."""
    # TODO: Implement database storage for evaluations
    return EvaluationListResponse(evaluations=[])


@router.get("/{eval_id}", response_model=EvaluationDetailResponse)
async def get_evaluation(
    eval_id: str,
    request: Request,
    db: Session = Depends(get_session),
    _: Any = Depends(require_permission("evaluation:read")),
):
    """Get evaluation details."""
    # TODO: Implement database storage for evaluations
    raise HTTPException(status_code=404, detail="Evaluation not found")


@router.post("/run", response_model=EvaluationRunResponse, status_code=status.HTTP_201_CREATED)
async def run_evaluation_legacy(
    request: Request,
    _: Any = Depends(require_permission("evaluation:run")),
):
    """Legacy endpoint for running evaluation."""
    return await run_evaluation(await request.json(), request, next(get_session()))
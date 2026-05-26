"""
FastAPI route handlers for workflow execution and SaaS CRUD.

Endpoints:
  POST /api/v1/workflow/run              — compile and execute a workflow
  POST /api/v1/workflow/run/{workflow_id} — run a deployed workflow by ID
  POST /api/v1/workflow/hitl/approve     — resume a HITL-interrupted workflow
  GET|POST|PATCH|DELETE /api/v1/workflow/workflows — SaaS CRUD
  GET|POST|PATCH|DELETE /api/v1/workflow/tools     — SaaS CRUD
  GET|POST|PATCH|DELETE /api/v1/workflow/rag-sources — SaaS CRUD
  POST /api/v1/workflow/master/generate  — master agent proposal
  POST /api/v1/workflow/master/compile   — master agent compile
  GET  /api/v1/workflow/activity         — activity logs
  GET  /api/v1/workflow/db/*             — database management
  GET  /api/v1/workflow/metrics          — Prometheus metrics
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from langchain_core.messages import HumanMessage
from passlib.context import CryptContext
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from agenticai_sdk.auth.dependencies import get_current_workspace
from agenticai_sdk.auth.permissions import require_permission
from agenticai_sdk.db import get_session, Workspace, Workflow, Tool as DBTool, ActivityLog, BillingData, ApiKey, User
from agenticai_sdk.db.database import get_db_status as _get_db_status, reset_db, _load_config
from agenticai_sdk.db.models import RAGSource as _RAGSource
from agenticai_sdk.db.models import WorkflowTrace as _WorkflowTrace
from agenticai_sdk.exceptions import AgenticSDKError, HITLRejectError, WorkflowCompilationError
from agenticai_sdk.runtime.orchestrator import Orchestrator
from agenticai_sdk.schemas.workflow import WorkflowSchema
from agenticai_sdk.state.workflow_state import WorkflowState

from master_agent.agent import StructuredMasterAgent

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/api/v1/workflow", tags=["workflow"])

_orchestrator = Orchestrator()
_master_agent = StructuredMasterAgent()

_EXEC_CACHE: dict[str, Any] = {}


# ── Request / Response Models ─────────────────────────────────────────────────


class WorkflowRunRequest(BaseModel):
    workflow: WorkflowSchema = Field(...)
    input_message: str = Field(..., min_length=1)
    thread_id: str | None = None
    initial_scratchpad: dict[str, Any] | None = None


class WorkflowRunResponse(BaseModel):
    thread_id: str
    status: str
    messages: list[dict[str, Any]]
    scratchpad: dict[str, Any]
    retrieved_context: list[dict[str, Any]]
    inner_thoughts: list[dict[str, Any]]
    next_step: str | None


class WorkflowRunByKeyRequest(BaseModel):
    input_message: str = Field(..., min_length=1)
    thread_id: str | None = None
    initial_scratchpad: dict[str, Any] | None = None
    workflow_id: str | None = None


class WorkflowRunByIDRequest(BaseModel):
    input_message: str = Field(..., min_length=1)
    thread_id: str | None = None
    initial_scratchpad: dict[str, Any] | None = None


class HITLApproveRequest(BaseModel):
    thread_id: str
    approved: bool
    state_updates: dict[str, Any] | None = None
    workflow: WorkflowSchema


class HITLApproveResponse(BaseModel):
    thread_id: str
    status: str
    messages: list[dict[str, Any]]
    scratchpad: dict[str, Any]
    inner_thoughts: list[dict[str, Any]]


class MasterGenerateRequest(BaseModel):
    prompt: str


class DBConnectRequest(BaseModel):
    core_db_url: str
    routing_map: dict[str, str] | None = None
    persist: bool = True


class DBConnectResponse(BaseModel):
    success: bool
    provider: str
    url: str
    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _get_workspace_id(request: Request) -> str:
    return getattr(request.state, "workspace_id", None) or "default"


def _log_activity(db: Session, action: str, resource_type: str, resource_id: str, resource_name: str, workspace_id: str = "system", details: Any = None):
    log = ActivityLog(
        id=str(uuid.uuid4()),
        workspace_id=workspace_id,
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


async def _execute_workflow(
    workflow_schema: WorkflowSchema,
    input_message: str,
    thread_id: str | None = None,
    initial_scratchpad: dict[str, Any] | None = None,
) -> WorkflowRunResponse:
    tid = thread_id or str(uuid.uuid4())
    app = await _orchestrator.compile(workflow_schema)
    initial_state: WorkflowState = {
        "messages": [HumanMessage(content=input_message)],
        "scratchpad": initial_scratchpad or {},
        "retrieved_context": [],
        "inner_thoughts": [],
        "next_step": None,
        "middleware_metadata": {},
        "trace_id": None,
    }
    config = {"configurable": {"thread_id": tid}}
    final_state = await app.ainvoke(initial_state, config=config)

    exec_status = "complete"
    if final_state is None:
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

    return WorkflowRunResponse(
        thread_id=tid,
        status=exec_status,
        messages=_serialize_messages(final_state.get("messages", [])),
        scratchpad=final_state.get("scratchpad", {}),
        retrieved_context=final_state.get("retrieved_context", []),
        inner_thoughts=final_state.get("inner_thoughts", []),
        next_step=final_state.get("next_step"),
    )


# ── Workflow Run ──────────────────────────────────────────────────────────────


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(request_body: WorkflowRunRequest | WorkflowRunByKeyRequest, request: Request, _: User = Depends(require_permission("workflow:run"))):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    log = logger.bind(request_id=request_id)

    db = next(get_session())
    try:
        workflow_scope = getattr(request.state, "workflow_key_scope", None)

        if isinstance(request_body, WorkflowRunByKeyRequest):
            if workflow_scope:
                wf_id = workflow_scope
            elif request_body.workflow_id:
                wf_id = request_body.workflow_id
            else:
                raise HTTPException(status_code=400, detail="workflow_id required")

            log = log.bind(workflow_id=wf_id)
            wf = db.query(Workflow).filter(Workflow.id == wf_id, Workflow.workspace_id == request.state.workspace_id).first()
            if not wf:
                raise HTTPException(status_code=404, detail="Workflow not found")
            if not wf.config:
                raise HTTPException(status_code=400, detail="Workflow has no config — compile it first")
            schema = WorkflowSchema(**wf.config)
            input_message = request_body.input_message
            thread_id = request_body.thread_id
            scratchpad = request_body.initial_scratchpad
        else:
            schema = request_body.workflow
            input_message = request_body.input_message
            thread_id = request_body.thread_id
            scratchpad = request_body.initial_scratchpad

        log.info("workflow_run_requested", input_preview=input_message[:100])
        return await _execute_workflow(schema, input_message, thread_id, scratchpad)

    except HTTPException:
        raise
    except WorkflowCompilationError as exc:
        log.error("workflow_compilation_failed", error=str(exc))
        raise HTTPException(status_code=422, detail={"message": str(exc)})
    except Exception as exc:
        log.error("workflow_unexpected_error", error=str(exc))
        raise HTTPException(status_code=500, detail=f"Unexpected error: {exc}")
    finally:
        db.close()


@router.post("/run/{workflow_id}", response_model=WorkflowRunResponse)
async def run_workflow_by_id(
    workflow_id: str,
    body: WorkflowRunByIDRequest,
    request: Request,
    db: Session = Depends(get_session),
    _: User = Depends(require_permission("workflow:run")),
):
    workflow_scope = getattr(request.state, "workflow_key_scope", None)
    if workflow_scope and workflow_scope != workflow_id:
        raise HTTPException(status_code=403, detail="API key not scoped to this workflow")

    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not wf.config:
        raise HTTPException(status_code=400, detail="Workflow has no config — compile it first")

    log = logger.bind(workflow_id=workflow_id)
    log.info("workflow_run_by_id", input_preview=body.input_message[:100])

    schema = WorkflowSchema(**wf.config)
    return await _execute_workflow(schema, body.input_message, body.thread_id, body.initial_scratchpad)


# ── HITL Approve ──────────────────────────────────────────────────────────────


@router.post("/hitl/approve", response_model=HITLApproveResponse)
async def hitl_approve(request_body: HITLApproveRequest, request: Request, _: User = Depends(require_permission("approval:approve"))):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    log = logger.bind(request_id=request_id, thread_id=request_body.thread_id, approved=request_body.approved)
    log.info("hitl_approval_received")

    if not request_body.approved:
        log.info("hitl_rejected_by_reviewer")
        raise HTTPException(status_code=200, detail={"thread_id": request_body.thread_id, "status": "rejected", "message": "Workflow execution rejected by human reviewer."})

    try:
        app = await _orchestrator.compile(request_body.workflow)
        config = {"configurable": {"thread_id": request_body.thread_id}}
        update_input = request_body.state_updates or {}
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
        raise HTTPException(status_code=400, detail={"message": str(exc)})
    except AgenticSDKError as exc:
        raise HTTPException(status_code=500, detail={"message": str(exc)})
    except Exception as exc:
        raise HTTPException(status_code=500, detail={"message": f"Unexpected error during HITL resume: {exc}"})


# ── SaaS Backend CRUD ─────────────────────────────────────────────────────────


@router.get("/workflows", tags=["saas-workflows"])
async def get_workflows(request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("workflow:read"))):
    ws_id = _get_workspace_id(request)
    wfs = db.query(Workflow).filter(Workflow.workspace_id == ws_id).all()
    return [{"id": w.id, "name": w.name, "description": w.description, "config": w.config, "workspace_id": w.workspace_id} for w in wfs]


@router.post("/workflows", tags=["saas-workflows"])
async def create_workflow(request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("workflow:create"))):
    ws_id = _get_workspace_id(request)
    body = await request.json()
    w_id = body.get("id") or str(uuid.uuid4())
    w = Workflow(id=w_id, workspace_id=ws_id, name=body.get("name", "Untitled"), description=body.get("description", ""), config=body.get("config", {}))
    db.add(w)
    db.commit()

    raw_key = f"wfk_{uuid.uuid4().hex}"
    db.add(ApiKey(id=str(uuid.uuid4()), workspace_id=ws_id, workflow_id=w_id, key_prefix=raw_key[:12], key_hash=pwd_context.hash(raw_key), name=f"Auto-key for {w.name}"))
    db.commit()

    _log_activity(db, "workflow.created", "workflow", w_id, w.name, workspace_id=ws_id)
    return {"id": w.id, "name": w.name, "api_key": raw_key}


@router.get("/workflows/{w_id}", tags=["saas-workflows"])
async def get_workflow(w_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("workflow:read"))):
    ws_id = _get_workspace_id(request)
    w = db.query(Workflow).filter(Workflow.id == w_id, Workflow.workspace_id == ws_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"id": w.id, "name": w.name, "config": w.config}


@router.patch("/workflows/{w_id}", tags=["saas-workflows"])
async def update_workflow(w_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("workflow:update"))):
    ws_id = _get_workspace_id(request)
    w = db.query(Workflow).filter(Workflow.id == w_id, Workflow.workspace_id == ws_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    body = await request.json()
    if "name" in body:
        w.name = body["name"]
    if "config" in body:
        w.config = body["config"]
    db.commit()
    _log_activity(db, "workflow.updated", "workflow", w_id, w.name, workspace_id=ws_id)
    return {"id": w.id, "name": w.name}


@router.delete("/workflows/{w_id}", tags=["saas-workflows"])
async def delete_workflow(w_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("workflow:delete"))):
    ws_id = _get_workspace_id(request)
    w = db.query(Workflow).filter(Workflow.id == w_id, Workflow.workspace_id == ws_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Workflow not found")
    name = w.name
    db.delete(w)
    db.commit()
    _log_activity(db, "workflow.deleted", "workflow", w_id, name, workspace_id=ws_id)
    return {"success": True}


@router.delete("/workspaces/{ws_id}", tags=["saas-workspaces"])
async def delete_workspace(ws_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("workspace:delete"))):
    ws = db.query(Workspace).filter(Workspace.id == ws_id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found")
    db.delete(ws)
    db.commit()
    _log_activity(db, "workspace.deleted", "workspace", ws_id, ws.name)
    return {"success": True}


@router.get("/tools", tags=["saas-tools"])
async def get_tools(request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("tool:read"))):
    ws_id = _get_workspace_id(request)
    return [{"id": t.id, "name": t.name, "description": t.description, "type": t.tool_type} for t in db.query(DBTool).filter(DBTool.workspace_id == ws_id).all()]


@router.post("/tools", tags=["saas-tools"])
async def create_tool(request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("tool:create"))):
    ws_id = _get_workspace_id(request)
    body = await request.json()
    t_id = body.get("id") or str(uuid.uuid4())
    t = DBTool(id=t_id, workspace_id=ws_id, name=body.get("name"), description=body.get("description", ""), tool_type=body.get("type", "custom_python"), code_or_url=body.get("code", "") or body.get("mcp_url", ""))
    db.add(t)
    db.commit()
    from agenticai_sdk.runtime.tool_registry import register_dynamic_tool
    if t.tool_type == "custom_python":
        register_dynamic_tool(t.name, t.description, t.code_or_url)
    _log_activity(db, "tool.created", "tool", t_id, t.name, workspace_id=ws_id, details={"type": t.tool_type})
    return {"id": t.id, "name": t.name}


@router.patch("/tools/{t_id}", tags=["saas-tools"])
async def update_tool(t_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("tool:update"))):
    ws_id = _get_workspace_id(request)
    t = db.query(DBTool).filter(DBTool.id == t_id, DBTool.workspace_id == ws_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tool not found")
    body = await request.json()
    if "name" in body:
        t.name = body["name"]
    if "description" in body:
        t.description = body["description"]
    if "type" in body:
        t.tool_type = body["type"]
    if "code" in body:
        t.code_or_url = body["code"]
    db.commit()
    return {"id": t.id, "name": t.name}


@router.delete("/tools/{t_id}", tags=["saas-tools"])
async def delete_tool(t_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("tool:delete"))):
    ws_id = _get_workspace_id(request)
    t = db.query(DBTool).filter(DBTool.id == t_id, DBTool.workspace_id == ws_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tool not found")
    db.delete(t)
    db.commit()
    _log_activity(db, "tool.deleted", "tool", t_id, t.name, workspace_id=ws_id)
    return {"success": True}


@router.get("/rag-sources", tags=["saas-rag"])
async def get_rag_sources(request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("rag:read"))):
    ws_id = _get_workspace_id(request)
    return [{"id": s.id, "name": s.name, "provider": s.provider, "config": s.config} for s in db.query(_RAGSource).filter(_RAGSource.workspace_id == ws_id).all()]


@router.post("/rag-sources", tags=["saas-rag"])
async def create_rag_source(request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("rag:create"))):
    ws_id = _get_workspace_id(request)
    body = await request.json()
    s_id = body.get("id") or str(uuid.uuid4())
    s = _RAGSource(id=s_id, workspace_id=ws_id, name=body.get("name", "New RAG Source"), provider=body.get("provider", "qdrant"), config=body.get("config", {}))
    db.add(s)
    db.commit()
    return {"id": s.id, "name": s.name}


@router.patch("/rag-sources/{s_id}", tags=["saas-rag"])
async def update_rag_source(s_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("rag:update"))):
    ws_id = _get_workspace_id(request)
    s = db.query(_RAGSource).filter(_RAGSource.id == s_id, _RAGSource.workspace_id == ws_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="RAG source not found")
    body = await request.json()
    if "name" in body:
        s.name = body["name"]
    if "provider" in body:
        s.provider = body["provider"]
    if "config" in body:
        s.config = body["config"]
    db.commit()
    return {"id": s.id, "name": s.name}


@router.delete("/rag-sources/{s_id}", tags=["saas-rag"])
async def delete_rag_source(s_id: str, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("rag:delete"))):
    ws_id = _get_workspace_id(request)
    s = db.query(_RAGSource).filter(_RAGSource.id == s_id, _RAGSource.workspace_id == ws_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="RAG source not found")
    db.delete(s)
    db.commit()
    return {"success": True}


@router.get("/db/status", tags=["saas-db"])
async def get_db_status(db: Session = Depends(get_session), _: User = Depends(require_permission("db:read"))):
    status = _get_db_status()
    status["collections"] = {"workflows": db.query(Workflow).count(), "tools": db.query(DBTool).count(), "activity": db.query(ActivityLog).count(), "traces": db.query(_WorkflowTrace).count()}
    return status


@router.post("/db/connect", response_model=DBConnectResponse, tags=["saas-db"])
async def connect_database(body: DBConnectRequest, _: User = Depends(require_permission("db:connect"))):
    try:
        engines = reset_db(core_db_url=body.core_db_url, routing_map=body.routing_map)
        provider = "sqlite"
        if "postgresql" in body.core_db_url:
            provider = "postgresql"
        elif "clickhouse" in body.core_db_url:
            provider = "clickhouse"
        return DBConnectResponse(success=True, provider=provider, url=body.core_db_url, message=f"Database connected successfully ({provider}).")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {exc}")


@router.get("/db/config", tags=["saas-db"])
async def get_db_config(_: User = Depends(require_permission("db:read"))):
    config = _load_config()
    if config:
        return {"configured": True, **config}
    return {"configured": False, "message": "No persisted config found — using default SQLite."}


@router.post("/db/reset", tags=["saas-db"])
async def reset_database(_: User = Depends(require_permission("db:reset"))):
    from agenticai_sdk.db.database import _clear_config, init_db
    _clear_config()
    init_db()
    return {"success": True, "message": "Reset to default SQLite database."}


@router.get("/activity", tags=["saas-activity"])
async def get_activity(request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("audit:read"))):
    ws_id = _get_workspace_id(request)
    logs = db.query(ActivityLog).filter(ActivityLog.workspace_id == ws_id).order_by(ActivityLog.created_at.desc()).limit(50).all()
    return [{"id": L.id, "action": L.event_type, "details": L.details, "timestamp": L.created_at} for L in logs]


@router.get("/metrics", tags=["observability"])
async def get_metrics(_: User = Depends(require_permission("observability:read"))):
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
    except ImportError:
        raise HTTPException(status_code=503, detail="prometheus_client is not installed.")


# ── Master Agent ──────────────────────────────────────────────────────────────


@router.post("/master/generate", tags=["master-agent"])
async def master_generate(body: MasterGenerateRequest, _: User = Depends(require_permission("workflow:create"))):
    try:
        proposal = _master_agent.generate_proposal(body.prompt)
        return {"success": True, "proposal": proposal}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Master Agent generation failed: {str(e)}")


@router.post("/master/compile", tags=["master-agent"])
async def master_compile(workflow_schema: WorkflowSchema, request: Request, db: Session = Depends(get_session), _: User = Depends(require_permission("workflow:create"))):
    try:
        app = await _orchestrator.compile(workflow_schema)
        ws_id = _get_workspace_id(request)

        w = db.query(Workflow).filter(Workflow.id == workflow_schema.id).first()
        if w:
            w.name = workflow_schema.name
            w.description = workflow_schema.description or ""
            w.config = workflow_schema.model_dump()
            w.workspace_id = ws_id
        else:
            w = Workflow(id=workflow_schema.id, workspace_id=ws_id, name=workflow_schema.name, description=workflow_schema.description or "", config=workflow_schema.model_dump())
            db.add(w)
        db.commit()

        existing_key = db.query(ApiKey).filter(ApiKey.workflow_id == workflow_schema.id, ApiKey.is_active == 1).first()
        api_key = None
        if not existing_key:
            raw_key = f"wfk_{uuid.uuid4().hex}"
            db.add(ApiKey(id=str(uuid.uuid4()), workspace_id=ws_id, workflow_id=workflow_schema.id, key_prefix=raw_key[:12], key_hash=pwd_context.hash(raw_key), name=f"Auto-key for {workflow_schema.name}"))
            db.commit()
            api_key = raw_key

        _log_activity(db, "workflow.master_compiled", "workflow", workflow_schema.id, workflow_schema.name)
        result = {"success": True, "workflow_id": workflow_schema.id, "message": "Workflow successfully compiled and persisted."}
        if api_key:
            result["api_key"] = api_key
        return result
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Downstream compilation failed: {str(e)}")

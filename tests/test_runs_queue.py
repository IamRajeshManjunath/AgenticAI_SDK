from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.db import get_session
from agenticai_sdk.db.database import reset_db
from agenticai_sdk.db.models import Workflow
from agenticai_sdk.gateway.app import create_app
from agenticai_sdk.runtime.job_queue import claim_next_job
from agenticai_sdk.worker import WorkflowJobWorker


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "jobs.db"
    monkeypatch.setenv("AGENTICAI_DB_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("AGENTICAI_DB_CONFIG", str(tmp_path / ".agenticai_db_config"))
    reset_db(f"sqlite:///{db_path}")
    return TestClient(create_app(log_level="WARNING"))


def _register(client: TestClient, label: str) -> tuple[dict[str, str], str]:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": f"{label}-{uuid.uuid4().hex[:8]}@example.com", "password": "strongpassword123"},
    )
    assert response.status_code == 201
    data = response.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user"]["default_workspace_id"]


def _workflow_config(workflow_id: str) -> dict:
    return {
        "workflow_id": workflow_id,
        "name": "Queued workflow",
        "agents": [
            {
                "agent_id": "researcher",
                "role": "Research analyst",
                "prompt_template": {
                    "template_id": "research",
                    "template_string": "Research: {topic}",
                    "input_variables": ["topic"],
                },
                "llm": {
                    "provider": "openai",
                    "model_name": "gpt-4o",
                    "temperature": 0.5,
                    "api_key_env_var": "OPENAI_API_KEY",
                },
                "tools": [],
            }
        ],
        "edges": [{"source": "researcher", "target": "__end__"}],
        "entry_point": "researcher",
    }


def _save_workflow(workspace_id: str, workflow_id: str) -> None:
    db = next(get_session())
    try:
        db.add(
            Workflow(
                id=workflow_id,
                workspace_id=workspace_id,
                name="Queued workflow",
                description="",
                config=_workflow_config(workflow_id),
            )
        )
        db.commit()
    finally:
        db.close()


def test_run_is_queued_and_idempotent_by_payload(client):
    headers, workspace_id = _register(client, "queue")
    workflow_id = f"wf-{uuid.uuid4().hex}"
    _save_workflow(workspace_id, workflow_id)
    payload = {"workflow_id": workflow_id, "input_message": "Summarize this."}
    headers["Idempotency-Key"] = "request-123"

    first = client.post("/api/v1/runs", headers=headers, json=payload)
    replay = client.post("/api/v1/runs", headers=headers, json=payload)

    assert first.status_code == 202
    assert replay.status_code == 202
    assert replay.json()["run_id"] == first.json()["run_id"]
    status_response = client.get(first.json()["status_url"], headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "pending"


def test_idempotency_key_cannot_be_reused_for_different_payload(client):
    headers, workspace_id = _register(client, "queue-conflict")
    workflow_id = f"wf-{uuid.uuid4().hex}"
    _save_workflow(workspace_id, workflow_id)
    headers["Idempotency-Key"] = "request-123"

    first = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "input_message": "First."},
    )
    second = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "input_message": "Different."},
    )

    assert first.status_code == 202
    assert second.status_code == 409


def test_run_and_status_are_workspace_scoped(client):
    owner_headers, owner_workspace = _register(client, "owner")
    other_headers, _ = _register(client, "other")
    workflow_id = f"wf-{uuid.uuid4().hex}"
    _save_workflow(owner_workspace, workflow_id)

    response = client.post(
        "/api/v1/runs",
        headers=owner_headers,
        json={"workflow_id": workflow_id, "input_message": "Run."},
    )
    assert response.status_code == 202
    hidden = client.get(response.json()["status_url"], headers=other_headers)
    assert hidden.status_code == 404

    denied_run = client.post(
        "/api/v1/runs",
        headers=other_headers,
        json={"workflow_id": workflow_id, "input_message": "Run."},
    )
    assert denied_run.status_code == 404


def test_claiming_a_job_transitions_it_only_once(client):
    headers, workspace_id = _register(client, "claim")
    workflow_id = f"wf-{uuid.uuid4().hex}"
    _save_workflow(workspace_id, workflow_id)
    queued = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "input_message": "Run once."},
    )
    assert queued.status_code == 202

    first_session = next(get_session())
    second_session = next(get_session())
    try:
        claimed = claim_next_job(first_session, "worker-a")
        duplicate_claim = claim_next_job(second_session, "worker-b")
    finally:
        first_session.close()
        second_session.close()

    assert claimed is not None
    assert claimed.id == queued.json()["run_id"]
    assert claimed.status == "running"
    assert claimed.worker_id == "worker-a"
    assert duplicate_claim is None


def test_running_job_cannot_be_cancelled(client):
    headers, workspace_id = _register(client, "cancel")
    workflow_id = f"wf-{uuid.uuid4().hex}"
    _save_workflow(workspace_id, workflow_id)
    queued = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "input_message": "Run."},
    )
    db = next(get_session())
    try:
        claim_next_job(db, "worker-a")
    finally:
        db.close()

    response = client.post(f"/api/v1/runs/{queued.json()['run_id']}/cancel", headers=headers)
    assert response.status_code == 409
    assert response.json()["detail"].endswith("'running'.")


def test_worker_persists_execution_result(client, monkeypatch):
    headers, workspace_id = _register(client, "worker")
    workflow_id = f"wf-{uuid.uuid4().hex}"
    _save_workflow(workspace_id, workflow_id)
    queued = client.post(
        "/api/v1/runs",
        headers=headers,
        json={"workflow_id": workflow_id, "input_message": "Run in worker."},
    )
    assert queued.status_code == 202

    class FakeGraph:
        async def ainvoke(self, state, config):
            return {
                "messages": [],
                "scratchpad": {},
                "retrieved_context": [],
                "inner_thoughts": [],
                "next_step": None,
            }

        async def aget_state(self, config):
            return SimpleNamespace(next=())

    class FakeOrchestrator:
        def __init__(self, *, checkpointer):
            pass

        async def compile(self, workflow):
            return FakeGraph()

    @asynccontextmanager
    async def fake_checkpointer():
        yield object()

    monkeypatch.setattr("agenticai_sdk.worker.Orchestrator", FakeOrchestrator)
    monkeypatch.setattr("agenticai_sdk.worker.durable_checkpointer", fake_checkpointer)
    worker = WorkflowJobWorker()
    job = worker.claim()
    assert job is not None

    asyncio.run(worker._execute(job))

    status_response = client.get(queued.json()["status_url"], headers=headers)
    assert status_response.status_code == 200
    assert status_response.json()["status"] == "completed"
    assert status_response.json()["result"]["thread_id"] == job["thread_id"]

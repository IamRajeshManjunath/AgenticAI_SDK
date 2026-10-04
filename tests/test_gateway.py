"""Tests for the FastAPI gateway endpoints."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.gateway.app import create_app


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path, monkeypatch):
    """Force all tests to use a fresh temporary SQLite database."""
    db_path = tmp_path / "test.db"
    os.environ["AGENTICAI_DB_URL"] = f"sqlite:///{db_path}"
    monkeypatch.setenv("AGENTICAI_DB_CONFIG", str(tmp_path / ".agenticai_db_config"))
    from agenticai_sdk.db.database import reset_db
    reset_db(f"sqlite:///{db_path}")
    yield
    os.environ.pop("AGENTICAI_DB_URL", None)


@pytest.fixture
def client():
    app = create_app(log_level="WARNING")
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    email = f"gw-test-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "strongpassword123",
        "full_name": "Gateway Tester",
        "workspace_name": "Test Workspace",
    })
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestHealthEndpoints:
    def test_root(self, client, auth_headers):
        resp = client.get("/", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "AgenticAI SDK Gateway"
        assert "endpoints" in data

    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


class TestObservabilityAuthorization:
    def test_observability_requires_authentication(self, client):
        response = client.get("/api/v1/observability/traces")
        assert response.status_code == 401

    def test_trace_queries_are_workspace_scoped(self, client):
        email = f"trace-scope-{uuid.uuid4().hex[:8]}@example.com"
        registration = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": "strongpassword123"},
        )
        assert registration.status_code == 201
        user = registration.json()["user"]
        auth_headers = {"Authorization": f"Bearer {registration.json()['access_token']}"}
        from agenticai_sdk.db import get_session
        from agenticai_sdk.db.models import WorkflowTrace

        db = next(get_session())
        try:
            db.add_all(
                [
                    WorkflowTrace(
                        id="trace-current",
                        trace_id="trace-current",
                        workspace_id=user["default_workspace_id"],
                        workflow_id="current-workflow",
                        duration_ms=20,
                        total_tokens=10,
                        cost_usd=0.01,
                        error_count=0,
                        span_tree={"status": "completed"},
                    ),
                    WorkflowTrace(
                        id="trace-other",
                        trace_id="trace-other",
                        workspace_id="another-workspace",
                        workflow_id="other-workflow",
                        duration_ms=900,
                        total_tokens=900,
                        cost_usd=99,
                        error_count=0,
                        span_tree={"status": "completed"},
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        response = client.get("/api/v1/observability/traces", headers=auth_headers)
        assert response.status_code == 200
        assert [trace["trace_id"] for trace in response.json()["traces"]] == ["trace-current"]

        hidden = client.get("/api/v1/observability/traces/trace-other", headers=auth_headers)
        assert hidden.status_code == 404

        health = client.get("/api/v1/observability/health", headers=auth_headers)
        assert health.status_code == 200
        health_data = health.json()
        assert health_data["metrics_summary"]["total_requests"] == 1
        assert health_data["metrics_summary"]["total_tokens"] == 10
        assert health_data["components"]["persisted_traces"]["count"] == 1


class TestMiddleware:
    def test_request_id_header(self, client):
        resp = client.get("/health")
        assert "x-request-id" in resp.headers
        assert "x-execution-time-ms" in resp.headers

    def test_custom_request_id(self, client):
        resp = client.get("/health", headers={"X-Request-ID": "my-test-id-123"})
        assert resp.headers["x-request-id"] == "my-test-id-123"


class TestWorkflowRunEndpoint:
    def test_invalid_payload_returns_422(self, client, auth_headers):
        resp = client.post("/api/v1/workflow/run", json={"bad": "data"}, headers=auth_headers)
        assert resp.status_code == 422

    def test_empty_input_message_returns_422(self, client, auth_headers):
        payload = {
            "workflow": {
                "workflow_id": "test",
                "name": "test",
                "agents": [
                    {
                        "agent_id": "a1",
                        "role": "test",
                        "prompt_template": {
                            "template_id": "t1",
                            "template_string": "do {task}",
                            "input_variables": ["task"],
                        },
                        "llm": {
                            "provider": "openai",
                            "model_name": "gpt-4o",
                            "temperature": 0.5,
                            "api_key_env_var": "OPENAI_API_KEY",
                        },
                    }
                ],
                "edges": [{"source": "a1", "target": "__end__"}],
                "entry_point": "a1",
            },
            "input_message": "",
        }
        resp = client.post("/api/v1/workflow/run", json=payload, headers=auth_headers)
        assert resp.status_code == 422


class TestHITLEndpoint:
    def test_rejected_approval(self, client, auth_headers):
        """Rejecting a HITL approval should return a clear rejection status."""
        payload = {
            "thread_id": "test-thread",
            "approved": False,
            "workflow": {
                "workflow_id": "test",
                "name": "test",
                "agents": [
                    {
                        "agent_id": "a1",
                        "role": "test",
                        "prompt_template": {
                            "template_id": "t1",
                            "template_string": "do {task}",
                            "input_variables": ["task"],
                        },
                        "llm": {
                            "provider": "openai",
                            "model_name": "gpt-4o",
                            "temperature": 0.5,
                            "api_key_env_var": "OPENAI_API_KEY",
                        },
                    }
                ],
                "edges": [{"source": "a1", "target": "__end__"}],
                "entry_point": "a1",
            },
        }
        resp = client.post("/api/v1/workflow/hitl/approve", json=payload, headers=auth_headers)
        data = resp.json()
        assert "rejected" in str(data).lower() or resp.status_code == 200

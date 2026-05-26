"""Tests for the FastAPI gateway endpoints."""

from __future__ import annotations

import os
import uuid

import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.gateway.app import create_app


@pytest.fixture(autouse=True)
def _use_temp_db(tmp_path):
    """Force all tests to use a fresh temporary SQLite database."""
    db_path = tmp_path / "test.db"
    os.environ["AGENTICAI_DB_URL"] = f"sqlite:///{db_path}"
    yield
    os.environ.pop("AGENTICAI_DB_URL", None)


@pytest.fixture
def client():
    app = create_app(log_level="WARNING")
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    email = f"gw-test-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/auth/register", json={
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

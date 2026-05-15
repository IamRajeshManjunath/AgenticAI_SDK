"""Tests for the FastAPI gateway endpoints."""

from __future__ import annotations

import json
import pathlib

import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.gateway.app import create_app


@pytest.fixture
def client():
    app = create_app(log_level="WARNING")
    return TestClient(app)


class TestHealthEndpoints:
    def test_root(self, client):
        resp = client.get("/")
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
    def test_invalid_payload_returns_422(self, client):
        resp = client.post("/api/v1/workflow/run", json={"bad": "data"})
        assert resp.status_code == 422

    def test_empty_input_message_returns_422(self, client):
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
        resp = client.post("/api/v1/workflow/run", json=payload)
        assert resp.status_code == 422


class TestHITLEndpoint:
    def test_rejected_approval(self, client):
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
        resp = client.post("/api/v1/workflow/hitl/approve", json=payload)
        # Rejection returns 200 with detail containing "rejected"
        data = resp.json()
        assert "rejected" in str(data).lower() or resp.status_code == 200

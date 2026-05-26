"""Tests for third-party integration routes and IntegrationRegistry."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.gateway.app import create_app
from agenticai_sdk.runtime.integration_registry import IntegrationRegistry


@pytest.fixture
def client():
    app = create_app(log_level="WARNING")
    return TestClient(app)


class TestIntegrationRoutes:
    def test_list_integrations_returns_list(self, client):
        resp = client.get("/api/v1/workflow/integrations")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_connect_slack(self, client):
        payload = {
            "integration_type": "slack",
            "name": "My Slack",
            "auth_state": {"webhook_url": "https://hooks.slack.com/test"},
        }
        resp = client.post("/api/v1/workflow/integrations/connect", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["connection"]["integration_type"] == "slack"

    def test_connect_invalid_type(self, client):
        payload = {
            "integration_type": "invalid_type",
            "name": "Bad",
            "auth_state": {},
        }
        resp = client.post("/api/v1/workflow/integrations/connect", json=payload)
        assert resp.status_code == 422

    def test_list_after_connect(self, client):
        # Connect first
        client.post("/api/v1/workflow/integrations/connect", json={
            "integration_type": "teams",
            "name": "My Teams",
            "auth_state": {"webhook_url": "https://teams.webhook/test"},
        })
        resp = client.get("/api/v1/workflow/integrations")
        assert resp.status_code == 200
        data = resp.json()
        assert any(c["integration_type"] == "teams" for c in data)

    def test_disconnect(self, client):
        resp = client.delete("/api/v1/workflow/integrations/slack")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    def test_disconnect_nonexistent(self, client):
        resp = client.delete("/api/v1/workflow/integrations/whatsapp")
        assert resp.status_code == 404

    def test_test_connection_no_connection(self, client):
        resp = client.post("/api/v1/workflow/integrations/whatsapp/test", json={})
        assert resp.status_code == 400


class TestIntegrationRegistry:
    def test_register_and_get(self):
        registry = IntegrationRegistry(workspace_id="reg-test-ws")
        registry.register_connection("slack", "Test", {"webhook_url": "https://test.com"})
        conn = registry.get_connection("slack")
        assert conn is not None
        assert conn["integration_type"] == "slack"
        assert conn["name"] == "Test"

    def test_unsupported_type(self):
        registry = IntegrationRegistry(workspace_id="unsup-test-ws")
        with pytest.raises(ValueError, match="Unsupported"):
            registry.register_connection("unsupported", "X", {})

    def test_get_tools_returns_tools(self):
        registry = IntegrationRegistry(workspace_id="tools-test-ws")
        registry.register_connection("slack", "Test", {"webhook_url": "https://test.com"})
        tools = registry.get_tools()
        assert len(tools) >= 1
        assert any("slack" in t.name for t in tools)

    def test_get_tools_empty(self):
        registry = IntegrationRegistry(workspace_id="empty-test-ws")
        tools = registry.get_tools()
        assert tools == []

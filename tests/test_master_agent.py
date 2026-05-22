"""Unit tests for the Upstream Structured Master Agent and its gateway integration."""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.gateway.app import create_app
from Master_agent.rag import MasterAgentRAG
from Master_agent.agent import StructuredMasterAgent

@pytest.fixture
def client():
    app = create_app(log_level="WARNING")
    return TestClient(app)

class TestMasterAgentRAG:
    def test_rag_seeding_and_retrieval(self):
        rag = MasterAgentRAG()
        assert len(rag.documents) > 0
        
        # Test basic retrieval
        chunks = rag.retrieve("search web", top_k=2)
        assert len(chunks) > 0
        assert any("schema" in c["content"].lower() or "sdk" in c["content"].lower() for c in chunks)

class TestStructuredMasterAgent:
    def test_deterministic_proposal_generation(self):
        agent = StructuredMasterAgent()
        
        # Test standard workflow generation
        proposal = agent.generate_proposal("Build a flow to search google for current weather")
        assert "workflow_id" in proposal
        assert "agents" in proposal
        assert "edges" in proposal
        assert "entry_point" in proposal
        assert len(proposal["agents"]) > 0
        
        # Verify pydantic schema compliance
        from agenticai_sdk.schemas.workflow import WorkflowSchema
        validated = WorkflowSchema(**proposal)
        assert validated.workflow_id == proposal["workflow_id"]

class TestMasterGatewayEndpoints:
    def test_master_generate_route(self, client):
        payload = {"prompt": "Create an agent that writes articles using python code"}
        resp = client.post("/api/v1/workflow/master/generate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "proposal" in data
        assert "workflow_id" in data["proposal"]

    def test_master_compile_route(self, client):
        # Obtain a valid proposal first
        agent = StructuredMasterAgent()
        proposal = agent.generate_proposal("Simple test agent")
        
        resp = client.post("/api/v1/workflow/master/compile", json=proposal)
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "workflow_id" in data

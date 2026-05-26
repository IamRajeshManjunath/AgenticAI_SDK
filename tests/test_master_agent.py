"""Unit tests for the Upstream Structured Master Agent and its gateway integration."""

from __future__ import annotations
import pytest
from fastapi.testclient import TestClient

from agenticai_sdk.gateway.app import create_app
from Master_agent.rag import MasterAgentRAG
from Master_agent.context_loader import AgentContextLoader


@pytest.fixture
def client():
    app = create_app(log_level="WARNING")
    return TestClient(app)


class TestMasterAgentRAG:
    def test_rag_seeding_and_retrieval(self):
        rag = MasterAgentRAG()
        assert len(rag.documents) > 0

        chunks = rag.retrieve("search web", top_k=2)
        assert len(chunks) > 0
        assert any("schema" in c["content"].lower() or "sdk" in c["content"].lower() for c in chunks)


class TestAgentContextLoader:
    def test_load_all_contexts_empty(self):
        loader = AgentContextLoader(agents_dir="/tmp/nonexistent_agents_dir")
        contexts = loader.load_all_contexts()
        assert contexts == []

    def test_format_context_block_empty(self):
        loader = AgentContextLoader()
        assert loader.format_context_block([]) == ""

    def test_extract_yaml_frontmatter(self):
        content = '---\nrole: "researcher"\nmodel: gpt-4o\n---\n\nBody text here'
        frontmatter, body = AgentContextLoader.extract_yaml_frontmatter(content)
        assert frontmatter["role"] == "researcher"
        assert frontmatter["model"] == "gpt-4o"
        assert "Body text here" in body

    def test_extract_yaml_frontmatter_none(self):
        content = "Just plain markdown body"
        frontmatter, body = AgentContextLoader.extract_yaml_frontmatter(content)
        assert frontmatter == {}
        assert body == content


class TestMasterGatewayEndpoints:
    def test_master_generate_route_no_key(self, client):
        """Without a valid API key, the endpoint should return 500."""
        resp = client.post("/api/v1/workflow/master/generate", json={"prompt": "test"})
        assert resp.status_code == 500

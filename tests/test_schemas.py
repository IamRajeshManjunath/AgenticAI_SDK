"""Tests for the AgenticAI SDK schema validation layer."""

from __future__ import annotations

import json
import pathlib

import pytest
from pydantic import ValidationError

from agenticai_sdk.schemas import (
    AgentNodeConfig,
    DeepAgentTopologyConfig,
    EdgeConfig,
    HITLConfig,
    LLMConfig,
    MemoryConfig,
    PromptTemplateConfig,
    RAGConfig,
    ToolConfig,
    WorkflowSchema,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def valid_llm_config() -> dict:
    return {
        "provider": "openai",
        "model_name": "gpt-4o",
        "temperature": 0.5,
        "api_key_env_var": "OPENAI_API_KEY",
    }


@pytest.fixture
def valid_prompt_config() -> dict:
    return {
        "template_id": "test_prompt",
        "template_string": "Research this topic: {topic}",
        "input_variables": ["topic"],
    }


@pytest.fixture
def valid_agent_config(valid_llm_config, valid_prompt_config) -> dict:
    return {
        "agent_id": "researcher",
        "role": "Research Analyst",
        "prompt_template": valid_prompt_config,
        "llm": valid_llm_config,
        "tools": [],
    }


@pytest.fixture
def minimal_workflow(valid_agent_config) -> dict:
    return {
        "workflow_id": "test-workflow",
        "name": "Test Workflow",
        "agents": [valid_agent_config],
        "edges": [{"source": "researcher", "target": "__end__"}],
        "entry_point": "researcher",
    }


# ── LLMConfig Tests ──────────────────────────────────────────────────────────

class TestLLMConfig:
    def test_valid_config(self, valid_llm_config):
        config = LLMConfig(**valid_llm_config)
        assert config.provider.value == "openai"
        assert config.model_name == "gpt-4o"
        assert config.max_retries == 3
        assert config.request_timeout == 60.0

    def test_invalid_provider(self, valid_llm_config):
        valid_llm_config["provider"] = "invalid_provider"
        with pytest.raises(ValidationError):
            LLMConfig(**valid_llm_config)

    def test_temperature_range(self, valid_llm_config):
        valid_llm_config["temperature"] = 3.0
        with pytest.raises(ValidationError):
            LLMConfig(**valid_llm_config)

    def test_empty_model_name(self, valid_llm_config):
        valid_llm_config["model_name"] = ""
        with pytest.raises(ValidationError):
            LLMConfig(**valid_llm_config)


# ── PromptTemplateConfig Tests ────────────────────────────────────────────────

class TestPromptTemplateConfig:
    def test_valid_template(self, valid_prompt_config):
        config = PromptTemplateConfig(**valid_prompt_config)
        assert config.template_id == "test_prompt"
        assert "topic" in config.input_variables

    def test_missing_variable_in_template(self):
        """Declared variable not found as {placeholder} in the template string."""
        with pytest.raises(ValidationError, match="not present"):
            PromptTemplateConfig(
                template_id="bad",
                template_string="No placeholders here.",
                input_variables=["missing_var"],
            )

    def test_undeclared_variable_in_template(self):
        """Placeholder exists in template but is not listed in input_variables."""
        with pytest.raises(ValidationError, match="not listed"):
            PromptTemplateConfig(
                template_id="bad",
                template_string="Hello {name}, welcome to {place}.",
                input_variables=["name"],
            )

    def test_multiple_variables(self):
        config = PromptTemplateConfig(
            template_id="multi",
            template_string="Dear {name}, your task is {task} for {audience}.",
            input_variables=["name", "task", "audience"],
        )
        assert len(config.input_variables) == 3


# ── ToolConfig Tests ──────────────────────────────────────────────────────────

class TestToolConfig:
    def test_valid_tool(self):
        config = ToolConfig(
            tool_id="search",
            type="built_in",
            connection_string="web_search",
        )
        assert config.tool_id == "search"

    def test_tool_with_arguments(self):
        config = ToolConfig(
            tool_id="api_tool",
            type="rest_api",
            connection_string="https://api.example.com/v1",
            arguments={"method": "POST", "timeout": 30},
        )
        assert config.arguments["method"] == "POST"


# ── RAGConfig Tests ───────────────────────────────────────────────────────────

class TestRAGConfig:
    def test_valid_rag(self):
        config = RAGConfig(
            rag_id="docs",
            vector_db="qdrant",
            connection_uri="http://localhost:6333",
            embedding_provider="openai",
            embedding_model="text-embedding-3-small",
            collection_name="knowledge",
        )
        assert config.top_k == 5
        assert config.similarity_threshold == 0.7

    def test_threshold_bounds(self):
        with pytest.raises(ValidationError):
            RAGConfig(
                rag_id="bad",
                vector_db="qdrant",
                connection_uri="http://localhost:6333",
                embedding_provider="openai",
                embedding_model="text-embedding-3-small",
                collection_name="knowledge",
                similarity_threshold=1.5,
            )


# ── DeepAgentTopologyConfig Tests ─────────────────────────────────────────────

class TestTopologyConfig:
    def test_defaults(self):
        config = DeepAgentTopologyConfig()
        assert config.orchestration_mode.value == "model_driven"
        assert config.max_thought_tokens == 1024
        assert config.fallback_strategy.value == "retry"

    def test_agent_driven_with_steps(self):
        config = DeepAgentTopologyConfig(
            orchestration_mode="agent_driven",
            reasoning_steps=["analyze", "plan", "execute"],
            fallback_strategy="escalate",
        )
        assert len(config.reasoning_steps) == 3


# ── WorkflowSchema Tests ─────────────────────────────────────────────────────

class TestWorkflowSchema:
    def test_valid_minimal_workflow(self, minimal_workflow):
        schema = WorkflowSchema(**minimal_workflow)
        assert schema.workflow_id == "test-workflow"
        assert schema.entry_point == "researcher"
        assert len(schema.agents) == 1

    def test_invalid_entry_point(self, minimal_workflow):
        minimal_workflow["entry_point"] = "nonexistent_agent"
        with pytest.raises(ValidationError, match="entry_point"):
            WorkflowSchema(**minimal_workflow)

    def test_invalid_edge_source(self, minimal_workflow):
        minimal_workflow["edges"] = [{"source": "ghost", "target": "__end__"}]
        with pytest.raises(ValidationError, match="Edge source"):
            WorkflowSchema(**minimal_workflow)

    def test_invalid_tool_reference(self, valid_agent_config, minimal_workflow):
        valid_agent_config["tools"] = ["nonexistent_tool"]
        minimal_workflow["agents"] = [valid_agent_config]
        with pytest.raises(ValidationError, match="tool"):
            WorkflowSchema(**minimal_workflow)

    def test_invalid_rag_reference(self, valid_agent_config, minimal_workflow):
        valid_agent_config["rag_sources"] = ["nonexistent_rag"]
        minimal_workflow["agents"] = [valid_agent_config]
        with pytest.raises(ValidationError, match="rag_source"):
            WorkflowSchema(**minimal_workflow)

    def test_invalid_hitl_reference(self, minimal_workflow):
        minimal_workflow["hitl"] = {
            "interruption_points": ["nonexistent_node"],
            "approval_timeout": 3600,
            "notification_channel": "api_wait",
        }
        with pytest.raises(ValidationError, match="HITL interruption"):
            WorkflowSchema(**minimal_workflow)

    def test_example_workflow_validates(self):
        """The shipped example_workflow.json must parse without errors."""
        example_path = pathlib.Path(__file__).parent.parent / "example_workflow.json"
        if example_path.exists():
            data = json.loads(example_path.read_text())
            schema = WorkflowSchema(**data)
            assert schema.workflow_id == "enterprise-hierarchy-v2"
            assert len(schema.agents) == 3
            assert len(schema.tools) == 3


# ── EdgeConfig Tests ──────────────────────────────────────────────────────────

class TestEdgeConfig:
    def test_unconditional(self):
        edge = EdgeConfig(source="a", target="b")
        assert edge.condition is None
        assert edge.routing_middleware is None

    def test_conditional(self):
        edge = EdgeConfig(
            source="a",
            target="b",
            condition='state["next_step"] == "review"',
        )
        assert edge.condition is not None

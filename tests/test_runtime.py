"""Tests for the runtime domain — tool registry and context engine."""

from __future__ import annotations

import pytest

from agenticai_sdk.exceptions import ToolResolutionError
from agenticai_sdk.runtime.context_engine import ContextEngine
from agenticai_sdk.runtime.tool_registry import ToolRegistry
from agenticai_sdk.schemas import (
    AgentNodeConfig,
    LLMConfig,
    MemoryConfig,
    PromptTemplateConfig,
)
from agenticai_sdk.schemas.tools import ToolConfig


# ── ToolRegistry Tests ────────────────────────────────────────────────────────


class TestToolRegistry:
    def test_resolve_built_in_tools(self):
        configs = [
            ToolConfig(tool_id="search", type="built_in", connection_string="web_search"),
            ToolConfig(tool_id="calc", type="built_in", connection_string="calculator"),
        ]
        registry = ToolRegistry()
        registry.resolve_all(configs)
        tools = registry.get_tools_for_agent(["search", "calc"])
        assert len(tools) == 2

    def test_unknown_tool_id_raises(self):
        registry = ToolRegistry()
        registry.resolve_all([])
        with pytest.raises(ToolResolutionError, match="not in the registry"):
            registry.get_tools_for_agent(["nonexistent"])

    def test_unknown_built_in_raises(self):
        config = ToolConfig(tool_id="bad", type="built_in", connection_string="does_not_exist")
        registry = ToolRegistry()
        with pytest.raises(ToolResolutionError):
            registry.resolve_all([config])

    def test_rest_api_tool(self):
        config = ToolConfig(
            tool_id="my_api",
            type="rest_api",
            connection_string="https://api.example.com/v1",
            arguments={"method": "GET"},
        )
        registry = ToolRegistry()
        registry.resolve_all([config])
        tools = registry.get_tools_for_agent(["my_api"])
        assert len(tools) == 1
        assert tools[0].name == "my_api"

    def test_mcp_tool(self):
        config = ToolConfig(
            tool_id="mcp_endpoint",
            type="mcp",
            connection_string="http://localhost:9090/mcp",
        )
        registry = ToolRegistry()
        registry.resolve_all([config])
        tools = registry.get_tools_for_agent(["mcp_endpoint"])
        assert len(tools) == 1


# ── ContextEngine Tests ───────────────────────────────────────────────────────


class TestContextEngine:
    @pytest.fixture
    def engine(self) -> ContextEngine:
        return ContextEngine()

    @pytest.fixture
    def agent_config(self) -> AgentNodeConfig:
        return AgentNodeConfig(
            agent_id="test_agent",
            role="Test Agent Role",
            prompt_template=PromptTemplateConfig(
                template_id="test",
                template_string="Analyze this: {topic}",
                input_variables=["topic"],
            ),
            llm=LLMConfig(
                provider="openai",
                model_name="gpt-4o",
                temperature=0.5,
                api_key_env_var="OPENAI_API_KEY",
            ),
        )

    def test_render_prompt(self, engine, agent_config):
        rendered = engine.render_prompt(agent_config, {"topic": "AI Safety"})
        assert "AI Safety" in rendered

    def test_build_system_message(self, engine, agent_config):
        msg = engine.build_system_message(agent_config)
        assert "Test Agent Role" in msg.content
        assert "Analyze this" in msg.content

    def test_build_system_message_with_context(self, engine, agent_config):
        msg = engine.build_system_message(
            agent_config,
            context_block="[Source: docs] Relevant info here.",
        )
        assert "Relevant info here" in msg.content

    def test_apply_memory_window_short_term(self, engine):
        from langchain_core.messages import HumanMessage

        messages = [HumanMessage(content=f"msg_{i}") for i in range(20)]
        config = MemoryConfig(execution_memory_type="short_term", window_size=5)
        windowed = engine.apply_memory_window(messages, config)
        assert len(windowed) == 5
        assert windowed[0].content == "msg_15"

    def test_apply_memory_window_episodic(self, engine):
        from langchain_core.messages import HumanMessage

        messages = [HumanMessage(content=f"msg_{i}") for i in range(20)]
        config = MemoryConfig(execution_memory_type="episodic")
        windowed = engine.apply_memory_window(messages, config)
        assert len(windowed) == 20  # episodic keeps everything

    def test_extract_last_ai_content(self, engine):
        from langchain_core.messages import AIMessage, HumanMessage

        messages = [
            HumanMessage(content="hello"),
            AIMessage(content="first response"),
            HumanMessage(content="follow up"),
            AIMessage(content="second response"),
        ]
        result = engine.extract_last_ai_content(messages)
        assert result == "second response"

    def test_extract_last_ai_content_empty(self, engine):
        from langchain_core.messages import HumanMessage

        messages = [HumanMessage(content="hello")]
        result = engine.extract_last_ai_content(messages)
        assert result == ""

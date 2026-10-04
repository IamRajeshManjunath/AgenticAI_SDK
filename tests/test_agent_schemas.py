from __future__ import annotations

import asyncio
import json

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import ValidationError

from agenticai_sdk.db import get_session
from agenticai_sdk.db.database import reset_db
from agenticai_sdk.db.models import SchemaAuditTrail
from agenticai_sdk.middleware.base import MiddlewarePipeline
from agenticai_sdk.runtime.orchestrator import Orchestrator
from agenticai_sdk.runtime.agent_schemas import (
    AgentSchemaValidationError,
    build_agent_input_payload,
    validate_agent_input,
    validate_agent_output,
)
from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.llm import LLMConfig
from agenticai_sdk.schemas.prompts import PromptTemplateConfig


@pytest.fixture(autouse=True)
def temporary_db(tmp_path, monkeypatch):
    database_url = f"sqlite:///{tmp_path / 'agent-schemas.db'}"
    monkeypatch.setenv("AGENTICAI_DB_URL", database_url)
    monkeypatch.setenv("AGENTICAI_DB_CONFIG", str(tmp_path / ".agenticai_db_config"))
    reset_db(database_url)


def _agent(**overrides) -> AgentNodeConfig:
    values = {
        "agent_id": "schema-agent",
        "role": "Schema test agent",
        "prompt_template": PromptTemplateConfig(
            template_id="schema-test",
            template_string="Handle {input_message}",
            input_variables=["input_message"],
        ),
        "llm": LLMConfig(
            provider="openai",
            model_name="gpt-4o",
            temperature=0.2,
            api_key_env_var="OPENAI_API_KEY",
        ),
    }
    values.update(overrides)
    return AgentNodeConfig(**values)


def _audit_rows() -> list[SchemaAuditTrail]:
    db = next(get_session())
    try:
        return db.query(SchemaAuditTrail).all()
    finally:
        db.close()


def test_input_payload_is_json_safe_and_uses_latest_user_message():
    payload = build_agent_input_payload(
        {
            "messages": [
                HumanMessage(content="Earlier request"),
                AIMessage(content="Previous answer"),
                HumanMessage(content="Current request"),
            ],
            "scratchpad": {"topic": "agents"},
            "retrieved_context": [{"text": "Relevant source"}],
        }
    )

    assert payload == {
        "input_message": "Current request",
        "scratchpad": {"topic": "agents"},
        "retrieved_context": [{"text": "Relevant source"}],
    }


def test_input_schema_accepts_payload_and_audits_workspace_scope():
    agent = _agent(
        input_schema={
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "required": ["input_message", "scratchpad", "retrieved_context"],
            "properties": {
                "input_message": {"type": "string"},
                "scratchpad": {"type": "object"},
                "retrieved_context": {"type": "array"},
            },
        }
    )

    validate_agent_input(
        agent,
        {"input_message": "Run", "scratchpad": {}, "retrieved_context": []},
        workspace_id="workspace-a",
        workflow_id="workflow-a",
    )

    row = _audit_rows()[0]
    assert row.is_valid == 1
    assert row.direction == "incoming"
    assert row.workspace_id == "workspace-a"
    assert row.workflow_id == "workflow-a"
    assert "sha256" in row.payload


def test_input_schema_violation_fails_and_records_scoped_audit():
    agent = _agent(input_schema={"type": "object", "required": ["missing"]})

    with pytest.raises(AgentSchemaValidationError, match="violated its JSON Schema"):
        validate_agent_input(
            agent,
            {"input_message": "Run", "scratchpad": {}, "retrieved_context": []},
            workspace_id="workspace-a",
            workflow_id="workflow-a",
        )

    row = _audit_rows()[0]
    assert row.is_valid == 0
    assert row.direction == "incoming"
    assert row.workspace_id == "workspace-a"
    assert row.workflow_id == "workflow-a"
    assert "missing" not in json.dumps(row.payload)


def test_output_schema_parses_and_validates_final_assistant_json():
    agent = _agent(
        output_schema={
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
            "additionalProperties": False,
        }
    )
    result = {
        "messages": [
            AIMessage(content="", tool_calls=[{"name": "search", "args": {}, "id": "call-1"}]),
            AIMessage(content='{"answer":"done"}'),
        ]
    }

    validate_agent_output(
        agent,
        result,
        workspace_id="workspace-a",
        workflow_id="workflow-a",
    )

    row = _audit_rows()[0]
    assert row.is_valid == 1
    assert row.direction == "outgoing"
    assert row.workspace_id == "workspace-a"
    assert row.workflow_id == "workflow-a"


@pytest.mark.parametrize(
    "content, error",
    [
        ("not JSON", "not valid JSON"),
        ('{"answer":3}', "violated its JSON Schema"),
    ],
)
def test_output_schema_mismatch_fails_and_records_audit(content, error):
    agent = _agent(
        output_schema={
            "type": "object",
            "required": ["answer"],
            "properties": {"answer": {"type": "string"}},
        }
    )

    with pytest.raises(AgentSchemaValidationError, match=error):
        validate_agent_output(
            agent,
            {"messages": [AIMessage(content=content)]},
            workspace_id="workspace-a",
            workflow_id="workflow-a",
        )

    row = _audit_rows()[0]
    assert row.is_valid == 0
    assert row.direction == "outgoing"
    assert row.workspace_id == "workspace-a"
    assert row.workflow_id == "workflow-a"


def test_invalid_json_schema_is_rejected_during_agent_validation():
    with pytest.raises(ValidationError, match="Invalid JSON Schema"):
        _agent(output_schema={"type": "not-a-json-schema-type"})


@pytest.mark.parametrize(
    "agent_options, response_content, expected_error, runner_should_execute",
    [
        (
            {"input_schema": {"type": "object", "required": ["absent"]}},
            '{"answer":"ok"}',
            "violated its JSON Schema",
            False,
        ),
        (
            {
                "output_schema": {
                    "type": "object",
                    "required": ["answer"],
                    "properties": {"answer": {"type": "string"}},
                }
            },
            "not JSON",
            "not valid JSON",
            True,
        ),
    ],
)
def test_primary_orchestrator_enforces_agent_schemas(
    monkeypatch,
    agent_options,
    response_content,
    expected_error,
    runner_should_execute,
):
    runner_state = {"executed": False}

    class FakeDeepAgentsIntegration:
        def __init__(self, config):
            pass

        def create_deep_agent(self, **kwargs):
            async def run(state):
                runner_state["executed"] = True
                return {
                    **state,
                    "messages": [*state["messages"], AIMessage(content=response_content)],
                }

            return run

    monkeypatch.setattr(
        "agenticai_sdk.runtime.orchestrator.DeepAgentsIntegration",
        FakeDeepAgentsIntegration,
    )
    orchestrator = Orchestrator()
    orchestrator._llm_factory.create = lambda config: object()
    orchestrator._build_middleware_pipeline = lambda config: MiddlewarePipeline()
    monkeypatch.setattr("agenticai_sdk.config.schemas.AgenticAIConfig", lambda: object())
    agent = _agent(**agent_options)
    workflow = type("Workflow", (), {"workflow_id": "workflow-a", "agents": [agent]})()

    async def invoke():
        node = await orchestrator._build_node_callable(agent, {}, workflow, {})
        return await node(
            {
                "messages": [HumanMessage(content="Run")],
                "scratchpad": {},
                "retrieved_context": [],
                "inner_thoughts": [],
                "next_step": None,
                "middleware_metadata": {},
                "trace_id": None,
                "workspace_id": "workspace-a",
            }
        )

    with pytest.raises(AgentSchemaValidationError, match=expected_error):
        asyncio.run(invoke())

    assert runner_state["executed"] is runner_should_execute

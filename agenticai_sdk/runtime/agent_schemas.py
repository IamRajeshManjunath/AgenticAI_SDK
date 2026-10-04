"""Per-agent JSON input/output schema validation and workspace-scoped audit."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

import structlog
from jsonschema import Draft202012Validator, ValidationError
from langchain_core.messages import AIMessage, HumanMessage

from agenticai_sdk.db.database import get_session
from agenticai_sdk.db.models import SchemaAuditTrail
from agenticai_sdk.schemas.agent_node import AgentNodeConfig

logger = structlog.get_logger(__name__)


class AgentSchemaValidationError(ValueError):
    """A configured agent input or output contract was not satisfied."""


def build_agent_input_payload(
    state: dict[str, Any],
    *,
    retrieved_context: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the documented JSON-only contract supplied to an agent."""
    input_message = ""
    for message in reversed(state.get("messages", [])):
        if isinstance(message, HumanMessage):
            input_message = _message_content(message)
            break
        if isinstance(message, dict) and message.get("type", message.get("role")) in {
            "human",
            "user",
        }:
            input_message = str(message.get("content", ""))
            break
    return {
        "input_message": input_message,
        "scratchpad": state.get("scratchpad", {}),
        "retrieved_context": (
            retrieved_context
            if retrieved_context is not None
            else state.get("retrieved_context", [])
        ),
    }


def validate_agent_input(
    agent: AgentNodeConfig,
    payload: dict[str, Any],
    *,
    workspace_id: str | None,
    workflow_id: str,
) -> None:
    if agent.input_schema is None:
        return
    _validate_and_audit(
        agent=agent,
        schema=agent.input_schema,
        payload=payload,
        direction="incoming",
        workspace_id=workspace_id,
        workflow_id=workflow_id,
    )


def validate_agent_output(
    agent: AgentNodeConfig,
    result: dict[str, Any],
    *,
    workspace_id: str | None,
    workflow_id: str,
) -> None:
    if agent.output_schema is None:
        return

    try:
        response = _final_response_content(result)
    except AgentSchemaValidationError as exc:
        _audit(
            agent=agent,
            schema=agent.output_schema,
            payload={"response_unavailable": True},
            direction="outgoing",
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            is_valid=False,
            error=str(exc),
        )
        raise
    try:
        parsed_output = json.loads(response)
    except json.JSONDecodeError as exc:
        error = f"Agent '{agent.agent_id}' response is not valid JSON: {exc.msg} at character {exc.pos}."
        _audit(
            agent=agent,
            schema=agent.output_schema,
            payload={"response_parse_failed": True},
            direction="outgoing",
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            is_valid=False,
            error=error,
        )
        raise AgentSchemaValidationError(error) from exc

    _validate_and_audit(
        agent=agent,
        schema=agent.output_schema,
        payload=parsed_output,
        direction="outgoing",
        workspace_id=workspace_id,
        workflow_id=workflow_id,
    )


def _message_content(message: HumanMessage) -> str:
    content = message.content
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def _final_response_content(result: dict[str, Any]) -> str:
    messages = result.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            if message.tool_calls:
                continue
            content = message.content
        elif isinstance(message, dict) and message.get("type", message.get("role")) in {
            "ai",
            "assistant",
        }:
            if message.get("tool_calls"):
                continue
            content = message.get("content", "")
        else:
            continue
        if isinstance(content, str) and content.strip():
            return content
        raise AgentSchemaValidationError(
            "The final agent response must be a JSON string when output_schema is configured."
        )
    raise AgentSchemaValidationError(
        "No final assistant response was produced for output_schema validation."
    )


def _validate_and_audit(
    *,
    agent: AgentNodeConfig,
    schema: dict[str, Any],
    payload: Any,
    direction: str,
    workspace_id: str | None,
    workflow_id: str,
) -> None:
    try:
        Draft202012Validator(schema).validate(payload)
    except ValidationError as exc:
        path = ".".join(str(part) for part in exc.absolute_path) or "$"
        error = f"Schema validation failed at '{path}': {exc.message}"
        _audit(
            agent=agent,
            schema=schema,
            payload=payload,
            direction=direction,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            is_valid=False,
            error=f"Schema validation failed at '{path}' ({exc.validator}).",
        )
        raise AgentSchemaValidationError(
            f"{direction.capitalize()} payload for agent '{agent.agent_id}' violated its JSON Schema: {error}"
        ) from exc
    except (TypeError, ValueError) as exc:
        error = f"Payload is not JSON-compatible: {exc}"
        _audit(
            agent=agent,
            schema=schema,
            payload={"serialization_failed": True},
            direction=direction,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            is_valid=False,
            error=error,
        )
        raise AgentSchemaValidationError(
            f"{direction.capitalize()} payload for agent '{agent.agent_id}' could not be validated: {error}"
        ) from exc

    _audit(
        agent=agent,
        schema=schema,
        payload=payload,
        direction=direction,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        is_valid=True,
        error=None,
    )


def _audit(
    *,
    agent: AgentNodeConfig,
    schema: dict[str, Any],
    payload: Any,
    direction: str,
    workspace_id: str | None,
    workflow_id: str,
    is_valid: bool,
    error: str | None,
) -> None:
    try:
        canonical_payload = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        payload_metadata = {
            "sha256": hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest(),
            "top_level_keys": sorted(payload.keys()) if isinstance(payload, dict) else None,
        }
    except (TypeError, ValueError):
        payload_metadata = {"sha256": None, "serialization_failed": True}

    db = next(get_session())
    try:
        db.add(
            SchemaAuditTrail(
                id=uuid.uuid4().hex,
                agent_id=agent.agent_id,
                direction=direction,
                payload=payload_metadata,
                schema_definition=schema,
                is_valid=int(is_valid),
                violation_error=error,
                workspace_id=workspace_id,
                workflow_id=workflow_id,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "agent_schema_audit_persistence_failed",
            agent_id=agent.agent_id,
            workflow_id=workflow_id,
            workspace_id=workspace_id,
            direction=direction,
        )
    finally:
        db.close()

"""
Schema Validation Middleware — enforces dynamic agent input/output schemas and records database audit trails.
"""

from typing import Any
import structlog
from jsonschema import validate, ValidationError
from agenticai_sdk.schemas.agent_node import AgentNodeConfig

logger = structlog.get_logger(__name__)

class SchemaValidationMiddleware:
    """
    Middleware that enforces dynamic input and output schemas configured on an AgentNode.
    Records every interaction (passed or blocked) directly to the persistent database.
    """

    def __init__(self, node_config: AgentNodeConfig):
        self.node_config = node_config
        self.input_schema = node_config.input_schema
        self.output_schema = node_config.output_schema

    def _log_audit_trail(self, direction: str, payload: dict, schema_def: dict, is_valid: bool, error: str = None):
        """Persists exact payload and schema rules mapped over the agent execution."""
        from agenticai_sdk.db.database import get_session
        from agenticai_sdk.db.models import SchemaAuditTrail
        try:
            # We fetch a new short-lived session since we might run concurrently.
            db = next(get_session())
            record = SchemaAuditTrail(
                id=__import__('uuid').uuid4().hex,
                agent_id=self.node_config.agent_id,
                direction=direction,
                payload=payload,
                schema_definition=schema_def,
                is_valid=int(is_valid),
                violation_error=error
            )
            db.add(record)
            db.commit()
            db.close()
        except Exception as e:
            logger.error("schema_audit_trail_failed", error=str(e))

    async def __call__(self, state: dict[str, Any], next_handler) -> dict[str, Any]:
        """
        Intercepts execution, validates the inbound state (or specific payload),
        executes the next handler, and validates the outbound result.
        """
        # Validate Input Schema
        if self.input_schema:
            try:
                validate(instance=state, schema=self.input_schema)
                self._log_audit_trail("incoming", payload=state, schema_def=self.input_schema, is_valid=True)
                logger.debug("input_schema_validated", agent_id=self.node_config.agent_id)
            except ValidationError as e:
                self._log_audit_trail("incoming", payload=state, schema_def=self.input_schema, is_valid=False, error=e.message)
                logger.error("input_schema_violation", agent_id=self.node_config.agent_id, error=str(e))
                raise ValueError(f"Input to agent '{self.node_config.agent_id}' violated schema: {e.message}") from e

        # Execute Node Logic (LLM calls, tools, etc.)
        updated_state = await next_handler(state)

        # Validate Output Schema
        if self.output_schema:
            try:
                validate(instance=updated_state, schema=self.output_schema)
                self._log_audit_trail("outgoing", payload=updated_state, schema_def=self.output_schema, is_valid=True)
                logger.debug("output_schema_validated", agent_id=self.node_config.agent_id)
            except ValidationError as e:
                self._log_audit_trail("outgoing", payload=updated_state, schema_def=self.output_schema, is_valid=False, error=e.message)
                logger.error("output_schema_violation", agent_id=self.node_config.agent_id, error=str(e))
                raise ValueError(f"Output from agent '{self.node_config.agent_id}' violated schema: {e.message}") from e

        return updated_state

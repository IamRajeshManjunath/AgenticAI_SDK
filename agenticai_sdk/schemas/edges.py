"""Edge configuration schema — graph routing between agent nodes."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EdgeConfig(BaseModel):
    """Graph routing configuration defining transitions between agent nodes.

    Attributes:
        source: Source agent_id (outgoing node).
        target: Target agent_id (incoming node).
        condition: Optional condition expression evaluated against WorkflowState.
            When ``None``, the edge is unconditional.
        routing_middleware: Optional ordered list of middleware hook identifiers
            that transform the state payload as it traverses this edge.
    """

    source: str = Field(
        ...,
        min_length=1,
        description="Source node agent_id.",
    )
    target: str = Field(
        ...,
        min_length=1,
        description="Target node agent_id.",
    )
    condition: str | None = Field(
        default=None,
        description=(
            "Optional condition expression evaluated against the current WorkflowState. "
            "Examples: 'state[\"next_step\"] == \"review\"', 'len(state[\"messages\"]) > 5'."
        ),
    )
    routing_middleware: list[str] | None = Field(
        default=None,
        description="Ordered list of middleware hook IDs for state transformation on this edge.",
    )

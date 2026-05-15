"""DeepAgent topology configuration schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class OrchestrationMode(str, Enum):
    """Inner-loop orchestration strategy.

    - ``model_driven``: The LLM autonomously decides tool usage and routing.
    - ``agent_driven``: Explicit reasoning steps and structured tool sequences.
    """

    MODEL_DRIVEN = "model_driven"
    AGENT_DRIVEN = "agent_driven"


class FallbackStrategy(str, Enum):
    """Strategy when the inner cognitive loop encounters an unrecoverable error."""

    RETRY = "retry"
    ESCALATE = "escalate"
    HALT = "halt"


class DeepAgentTopologyConfig(BaseModel):
    """Advanced inner-loop cognitive profile for an agent node.

    Attributes:
        orchestration_mode: Whether the inner loop is model-driven or agent-driven.
        reasoning_steps: Optional explicit reasoning trajectory labels.
        max_thought_tokens: Token budget for inner chain-of-thought reasoning.
        fallback_strategy: What to do when the cognitive loop fails.
    """

    orchestration_mode: OrchestrationMode = Field(
        default=OrchestrationMode.MODEL_DRIVEN,
        description="Select model-driven (LLM autonomous) or agent-driven (explicit steps) orchestration.",
    )
    reasoning_steps: list[str] | None = Field(
        default=None,
        description="Optional ordered list of explicit reasoning step labels for agent-driven mode.",
    )
    max_thought_tokens: int = Field(
        default=1024,
        ge=64,
        le=16384,
        description="Maximum token budget for inner chain-of-thought reasoning.",
    )
    fallback_strategy: FallbackStrategy = Field(
        default=FallbackStrategy.RETRY,
        description="Error recovery strategy (retry, escalate, halt).",
    )

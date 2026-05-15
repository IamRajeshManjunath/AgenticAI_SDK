"""Memory configuration schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ExecutionMemoryType(str, Enum):
    """Memory persistence mode for agent execution context."""

    SHORT_TERM = "short_term"
    EPISODIC = "episodic"


class CachingStrategy(str, Enum):
    """Caching backend for prompt/response memoisation."""

    REDIS = "redis"
    IN_MEMORY = "in_memory"
    NONE = "none"


class MemoryConfig(BaseModel):
    """Persistence and token-optimization layer configuration.

    Attributes:
        execution_memory_type: How execution history is retained.
        window_size: Number of recent messages to keep in the sliding window.
            Only meaningful for ``short_term`` memory.
        caching_strategy: Backend used for caching LLM responses.
    """

    execution_memory_type: ExecutionMemoryType = Field(
        default=ExecutionMemoryType.SHORT_TERM,
        description="Memory retention mode (short_term or episodic).",
    )
    window_size: int | None = Field(
        default=10,
        ge=1,
        description="Sliding window size for short-term memory (message count).",
    )
    caching_strategy: CachingStrategy = Field(
        default=CachingStrategy.IN_MEMORY,
        description="Caching backend for LLM response memoisation.",
    )

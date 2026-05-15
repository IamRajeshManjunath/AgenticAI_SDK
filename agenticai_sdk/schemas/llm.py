"""LLM provider configuration schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM inference providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"


class LLMConfig(BaseModel):
    """Model orchestration schema defining how to connect to an LLM backend.

    Attributes:
        provider: The inference backend to use.
        model_name: Exact model identifier (e.g. ``gpt-4o``, ``claude-sonnet-4-20250514``).
        temperature: Sampling temperature controlling output randomness.
        api_key_env_var: Name of the environment variable holding the API key.
        max_retries: Maximum number of automatic retry attempts on transient failures.
        request_timeout: Per-request timeout in seconds.
    """

    provider: LLMProvider = Field(
        ...,
        description="The LLM inference provider (openai, anthropic, ollama).",
    )
    model_name: str = Field(
        ...,
        min_length=1,
        description="Model identifier as recognized by the provider.",
    )
    temperature: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 = deterministic, 2.0 = maximum randomness).",
    )
    api_key_env_var: str = Field(
        ...,
        min_length=1,
        description="Environment variable name containing the provider API key.",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Number of automatic retries on transient API errors.",
    )
    request_timeout: float = Field(
        default=60.0,
        gt=0,
        description="Per-request timeout in seconds.",
    )

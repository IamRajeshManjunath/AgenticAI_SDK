"""LLM provider configuration schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class LLMProvider(str, Enum):
    """Supported LLM inference providers (legacy - for backward compat).
    
    For new integrations, use ChatModelConfig with plugin registry.
    """
    
    # Legacy providers (built-in)
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    
    # Extended providers (available via plugin registry)
    AZURE_OPENAI = "azure_openai"
    GOOGLE_GENAI = "google_genai"
    GOOGLE_VERTEX = "google_vertex"
    AWS_BEDROCK = "aws_bedrock"
    GROQ = "groq"
    MISTRAL = "mistral"
    COHERE = "cohere"
    XAI = "xai"
    DEEPSEEK = "deepseek"
    NVIDIA = "nvidia"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    DATABRICKS = "databricks"
    WATSONX = "watsonx"
    PERPLEXITY = "perplexity"
    CEREBRAS = "cerebras"
    HUGGINGFACE = "huggingface"
    LITELLM = "litellm"
    OPENROUTER = "openrouter"
    AZURE_AI = "azure_ai"


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
        description="The LLM inference provider.",
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
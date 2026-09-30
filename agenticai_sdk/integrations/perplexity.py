"""Perplexity integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class PerplexityConfig(BaseModel):
    """Configuration for Perplexity chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Perplexity API key")
    
    # Model parameters
    model: str = Field(default="llama-3.1-sonar-large-128k-online", description="Perplexity model name")
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True)
    tools: bool = Field(default=False)  # Perplexity doesn't support tools
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=False)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=False,
            structured_output=True,
            multimodal=False,
        )
    )

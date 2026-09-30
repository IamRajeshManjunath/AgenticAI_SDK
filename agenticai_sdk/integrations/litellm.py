"""LiteLLM integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class LiteLLMConfig(BaseModel):
    """Configuration for LiteLLM (unified LLM interface)."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for LiteLLM proxy API key")
    base_url: str = Field(default="http://localhost:4000", description="LiteLLM proxy URL")
    
    # Model parameters
    model: str = Field(default="gpt-4o", description="Model name (LiteLLM format)")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features (depends on underlying provider)
    streaming: bool = Field(default=True)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=True)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )

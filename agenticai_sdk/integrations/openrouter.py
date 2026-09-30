"""OpenRouter integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class OpenRouterConfig(BaseModel):
    """Configuration for OpenRouter chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for OpenRouter API key")
    base_url: str = Field(default="https://openrouter.ai/api/v1", description="OpenRouter base URL")
    
    # Model parameters
    model: str = Field(default="openai/gpt-4o", description="OpenRouter model slug")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=True)
    
    # OpenRouter specific
    http_referer: Optional[str] = Field(default=None, description="HTTP referer for analytics")
    x_title: Optional[str] = Field(default=None, description="X-Title header for analytics")
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )

"""Anthropic integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class AnthropicConfig(BaseModel):
    """Configuration for Anthropic chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable name for Anthropic API key")
    
    # Model parameters
    model: str = Field(default="claude-3-5-sonnet-20241022", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1, le=200000)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True, description="Enable streaming responses")
    tools: bool = Field(default=True, description="Enable tool calling")
    structured_output: bool = Field(default=True, description="Enable structured output")
    multimodal: bool = Field(default=True, description="Enable multimodal (vision)")
    
    # Advanced
    base_url: Optional[str] = Field(default=None, description="Custom base URL")
    default_headers: dict = Field(default_factory=dict)
    extra_body: dict = Field(default_factory=dict)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )


class VertexAIAnthropicConfig(BaseModel):
    """Configuration for Anthropic models on Google Vertex AI."""
    
    # Required
    project_id: str = Field(..., description="Google Cloud project ID")
    location: str = Field(default="us-east5", description="Vertex AI location")
    credentials_env: Optional[str] = Field(default=None, description="Environment variable for credentials JSON")
    
    # Model parameters
    model: str = Field(default="claude-3-5-sonnet@20240620", description="Model name on Vertex AI")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )

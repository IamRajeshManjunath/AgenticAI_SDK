"""Azure AI integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class AzureAIConfig(BaseModel):
    """Configuration for Azure AI chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Azure AI API key")
    endpoint: str = Field(..., description="Azure AI endpoint URL")
    deployment_name: str = Field(..., description="Model deployment name")
    api_version: str = Field(default="2024-02-01", description="API version")
    
    # Model parameters
    model: str = Field(default="gpt-4o", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
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

"""OpenAI integration configuration."""

from __future__ import annotations

from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class OpenAIConfig(BaseModel):
    """Configuration for OpenAI chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable name for OpenAI API key")
    
    # Optional
    organization_env: Optional[str] = Field(default=None, description="Environment variable for organization ID")
    base_url: Optional[str] = Field(default=None, description="Custom base URL (for compatible APIs)")
    
    # Model parameters
    model: str = Field(default="gpt-4o", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True, description="Enable streaming responses")
    tools: bool = Field(default=True, description="Enable tool calling")
    structured_output: bool = Field(default=True, description="Enable structured output")
    multimodal: bool = Field(default=True, description="Enable multimodal (vision)")
    
    # Advanced
    default_headers: Dict[str, str] = Field(default_factory=dict)
    extra_body: Dict[str, Any] = Field(default_factory=dict)
    
    # Feature flags (auto-populated from plugin metadata)
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )


class AzureOpenAIConfig(BaseModel):
    """Configuration for Azure OpenAI chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Azure OpenAI API key")
    azure_endpoint: str = Field(..., description="Azure OpenAI endpoint URL")
    azure_deployment: str = Field(..., description="Deployment name")
    api_version: str = Field(default="2024-02-01", description="API version")
    
    # Optional
    model: str = Field(default="gpt-4o", description="Model name (deployment name)")
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

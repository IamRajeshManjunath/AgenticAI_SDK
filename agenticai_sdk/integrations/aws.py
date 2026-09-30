"""AWS Bedrock integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class BedrockConfig(BaseModel):
    """Configuration for AWS Bedrock chat models."""
    
    # Authentication (use one of these)
    aws_access_key_id_env: Optional[str] = Field(default=None, description="AWS access key ID env var")
    aws_secret_access_key_env: Optional[str] = Field(default=None, description="AWS secret access key env var")
    aws_session_token_env: Optional[str] = Field(default=None, description="AWS session token env var")
    aws_profile: Optional[str] = Field(default=None, description="AWS profile name")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    
    # Model parameters
    model: str = Field(default="anthropic.claude-3-5-sonnet-20241022-v2:0", description="Bedrock model ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=4096, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=True)
    
    # Guardrails
    guardrail_id: Optional[str] = Field(default=None, description="Bedrock Guardrail ID")
    guardrail_version: Optional[str] = Field(default=None, description="Guardrail version")
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )


class BedrockEmbeddingsConfig(BaseModel):
    """Configuration for AWS Bedrock embeddings."""
    
    aws_region: str = Field(default="us-east-1")
    model: str = Field(default="amazon.titan-embed-text-v2:0", description="Bedrock embedding model ID")
    dimensions: Optional[int] = Field(default=None)
    batch_size: int = Field(default=100, ge=1, le=2048)

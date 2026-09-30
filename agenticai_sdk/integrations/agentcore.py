"""AWS Bedrock AgentCore sandbox configuration."""

from __future__ import annotations

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

from ...config.schemas import FeatureFlags


class AgentCoreConfig(BaseModel):
    """Configuration for AWS Bedrock AgentCore sandbox."""
    
    # Required
    aws_access_key_id_env: Optional[str] = Field(default=None, description="AWS access key ID")
    aws_secret_access_key_env: Optional[str] = Field(default=None, description="AWS secret access key")
    aws_region: str = Field(default="us-east-1", description="AWS region")
    
    # Sandbox settings
    sandbox_id: Optional[str] = Field(default=None, description="AgentCore sandbox ID")
    timeout: int = Field(default=300, ge=30)
    
    # Resources
    cpu: float = Field(default=1.0, ge=0.1)
    memory_mb: int = Field(default=1024, ge=256)
    
    # Features
    streaming: bool = Field(default=False)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=False)
    multimodal: bool = Field(default=False)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=False,
            tools=True,
            structured_output=False,
            multimodal=False,
        )
    )
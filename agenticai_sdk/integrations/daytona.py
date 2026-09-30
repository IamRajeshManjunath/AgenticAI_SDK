"""Daytona sandbox configuration."""

from __future__ import annotations

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

from ...config.schemas import FeatureFlags


class DaytonaConfig(BaseModel):
    """Configuration for Daytona sandbox."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Daytona API key")
    server_url: str = Field(default="https://app.daytona.io", description="Daytona server URL")
    
    # Sandbox settings
    sandbox_id: Optional[str] = Field(default=None, description="Daytona sandbox ID")
    timeout: int = Field(default=300, ge=30)
    
    # Resources
    cpu: float = Field(default=2.0, ge=0.5, le=32.0)
    memory_mb: int = Field(default=4096, ge=1024, le=131072)
    
    # Image
    image: str = Field(default="daytonaio/workspace:latest", description="Docker image")
    
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
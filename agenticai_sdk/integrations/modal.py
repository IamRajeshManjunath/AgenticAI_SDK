"""Modal sandbox configuration."""

from __future__ import annotations

from typing import Optional, Dict, Any

from pydantic import BaseModel, Field

from ...config.schemas import FeatureFlags


class ModalConfig(BaseModel):
    """Configuration for Modal sandbox."""
    
    # Required
    token_id_env: str = Field(..., description="Environment variable for Modal token ID")
    token_secret_env: str = Field(..., description="Environment variable for Modal token secret")
    
    # Sandbox settings
    app_name: str = Field(default="agenticai-sandbox", description="Modal app name")
    timeout: int = Field(default=300, ge=30, description="Timeout in seconds")
    
    # Resources
    cpu: float = Field(default=1.0, ge=0.1, le=32.0)
    memory_mb: int = Field(default=1024, ge=256, le=131072)
    gpu: Optional[str] = Field(default=None, description="GPU type (e.g., 'T4', 'A10G', 'H100')")
    
    # Image
    image: str = Field(default="python:3.11-slim", description="Docker image")
    
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
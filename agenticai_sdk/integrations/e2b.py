"""E2B code interpreter configuration."""

from __future__ import annotations

from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from ...config.schemas import FeatureFlags


class E2BConfig(BaseModel):
    """Configuration for E2B code interpreter sandbox."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for E2B API key")
    
    # Sandbox settings
    template: str = Field(default="base", description="E2B template (base, python, nodejs, etc.)")
    timeout: int = Field(default=300, ge=30, description="Sandbox timeout in seconds")
    
    # Resources
    cpu: float = Field(default=1.0, ge=0.1, le=8.0)
    memory_mb: int = Field(default=1024, ge=256, le=32768)
    
    # Environment
    env_vars: Dict[str, str] = Field(default_factory=dict)
    
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
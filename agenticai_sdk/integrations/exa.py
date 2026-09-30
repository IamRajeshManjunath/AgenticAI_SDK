"""Exa search tool configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ...config.schemas import FeatureFlags


class ExaConfig(BaseModel):
    """Configuration for Exa search tool."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Exa API key")
    
    # Search settings
    max_results: int = Field(default=10, ge=1, le=50)
    include_domains: Optional[list[str]] = Field(default=None)
    exclude_domains: Optional[list[str]] = Field(default=None)
    start_published_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    end_published_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    
    # Features
    streaming: bool = Field(default=False)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=False)
    
    timeout: float = Field(default=30.0, gt=0)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=False,
            tools=True,
            structured_output=True,
            multimodal=False,
        )
    )
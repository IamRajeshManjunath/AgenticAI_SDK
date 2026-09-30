"""Google search tool configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from ...config.schemas import FeatureFlags


class GoogleSearchConfig(BaseModel):
    """Configuration for Google Custom Search tool."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Google Custom Search API key")
    cse_id_env: str = Field(..., description="Environment variable for Custom Search Engine ID")
    
    # Search settings
    max_results: int = Field(default=10, ge=1, le=100)
    safe_search: str = Field(default="active", pattern="^(active|moderate|off)$")
    
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
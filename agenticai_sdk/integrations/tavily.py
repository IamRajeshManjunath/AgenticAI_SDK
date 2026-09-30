"""Tavily search tool configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class TavilyConfig(BaseModel):
    """Configuration for Tavily search tool."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Tavily API key")
    
    # Search parameters
    max_results: int = Field(default=5, ge=1, le=50)
    search_depth: str = Field(default="basic", pattern="^(basic|advanced)$")
    include_answer: bool = Field(default=True)
    include_raw_content: bool = Field(default=False)
    include_images: bool = Field(default=False)
    include_image_descriptions: bool = Field(default=False)
    
    # Domain filtering
    include_domains: Optional[list[str]] = Field(default=None)
    exclude_domains: Optional[list[str]] = Field(default=None)
    
    # Timeout
    timeout: float = Field(default=30.0, gt=0)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=False,
            tools=True,
            structured_output=False,
            multimodal=False,
        )
    )

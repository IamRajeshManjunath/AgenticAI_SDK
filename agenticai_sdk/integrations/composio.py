"""Composio tool configuration."""

from __future__ import annotations

from typing import Optional, List

from pydantic import BaseModel, Field

from ...config.schemas import FeatureFlags


class ComposioConfig(BaseModel):
    """Configuration for Composio integration platform (500+ tools)."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Composio API key")
    
    # Apps to enable (subset of 500+ available)
    apps: List[str] = Field(
        default_factory=lambda: ["github", "slack", "jira", "linear", "notion", "google_drive", "google_calendar", "gmail", "salesforce", "hubspot"],
        description="Composio apps to enable"
    )
    
    # Connection settings
    base_url: str = Field(default="https://backend.composio.dev/api", description="Composio backend URL")
    timeout: float = Field(default=30.0, gt=0)
    
    # Features
    streaming: bool = Field(default=False)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=False)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=False,
            tools=True,
            structured_output=True,
            multimodal=False,
        )
    )
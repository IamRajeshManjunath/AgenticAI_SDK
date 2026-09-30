"""Databricks integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class DatabricksConfig(BaseModel):
    """Configuration for Databricks chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Databricks token")
    host: str = Field(..., description="Databricks workspace URL")
    
    # Model parameters
    model: str = Field(default="databricks-meta-llama-3-1-70b-instruct", description="Databricks model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=False)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=False,
        )
    )


class DatabricksEmbeddingsConfig(BaseModel):
    """Configuration for Databricks embeddings."""
    
    api_key_env: str = Field(..., description="Environment variable for Databricks token")
    host: str = Field(..., description="Databricks workspace URL")
    model: str = Field(default="databricks-bge-large-en", description="Databricks embedding model")
    dimensions: Optional[int] = Field(default=None)
    batch_size: int = Field(default=100, ge=1, le=2048)
    timeout: float = Field(default=60.0, gt=0)

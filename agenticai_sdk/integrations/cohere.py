"""Cohere integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class CohereConfig(BaseModel):
    """Configuration for Cohere chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Cohere API key")
    
    # Model parameters
    model: str = Field(default="command-r-plus", description="Cohere model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
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


class CohereEmbeddingsConfig(BaseModel):
    """Configuration for Cohere embeddings."""
    
    api_key_env: str = Field(..., description="Environment variable for Cohere API key")
    model: str = Field(default="embed-english-v3.0", description="Cohere embedding model")
    dimensions: Optional[int] = Field(default=None)
    batch_size: int = Field(default=100, ge=1, le=2048)
    timeout: float = Field(default=60.0, gt=0)

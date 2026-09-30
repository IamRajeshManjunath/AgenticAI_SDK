"""Together AI integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class TogetherConfig(BaseModel):
    """Configuration for Together AI chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for Together AI API key")
    
    # Model parameters
    model: str = Field(default="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo", description="Together model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=True)
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=True)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )


class TogetherEmbeddingsConfig(BaseModel):
    """Configuration for Together AI embeddings."""
    
    api_key_env: str = Field(..., description="Environment variable for Together AI API key")
    model: str = Field(default="togethercomputer/m2-bert-80M-8k-retrieval", description="Together embedding model")
    dimensions: Optional[int] = Field(default=None)
    batch_size: int = Field(default=100, ge=1, le=2048)
    timeout: float = Field(default=60.0, gt=0)

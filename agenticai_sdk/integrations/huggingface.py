"""HuggingFace integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class HuggingFaceConfig(BaseModel):
    """Configuration for HuggingFace chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for HuggingFace API key")
    
    # Model parameters
    model: str = Field(default="meta-llama/Meta-Llama-3.1-70B-Instruct", description="HuggingFace model ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    timeout: float = Field(default=120.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Features
    streaming: bool = Field(default=False)  # HF TGI doesn't always support streaming
    tools: bool = Field(default=True)
    structured_output: bool = Field(default=True)
    multimodal: bool = Field(default=True)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=False,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )


class HuggingFaceEmbeddingsConfig(BaseModel):
    """Configuration for HuggingFace embeddings."""
    
    model: str = Field(default="sentence-transformers/all-mpnet-base-v2", description="Sentence transformer model")
    api_key_env: Optional[str] = Field(default=None, description="HuggingFace API key (for private models)")
    dimensions: Optional[int] = Field(default=None)
    batch_size: int = Field(default=100, ge=1, le=2048)
    device: str = Field(default="cpu", pattern="^(cpu|cuda|mps)$")
    timeout: float = Field(default=60.0, gt=0)

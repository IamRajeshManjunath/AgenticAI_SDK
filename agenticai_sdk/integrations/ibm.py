"""IBM WatsonX integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class WatsonXConfig(BaseModel):
    """Configuration for IBM WatsonX chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable for WatsonX API key")
    project_id: str = Field(..., description="WatsonX project ID")
    url: str = Field(default="https://us-south.ml.cloud.ibm.com", description="WatsonX URL")
    
    # Model parameters
    model: str = Field(default="meta-llama/llama-3-1-70b-instruct", description="WatsonX model ID")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
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


class WatsonXEmbeddingsConfig(BaseModel):
    """Configuration for IBM WatsonX embeddings."""
    
    api_key_env: str = Field(..., description="Environment variable for WatsonX API key")
    project_id: str = Field(..., description="WatsonX project ID")
    url: str = Field(default="https://us-south.ml.cloud.ibm.com")
    model: str = Field(default="ibm/slate-125m-english-rtrvr", description="WatsonX embedding model")
    dimensions: Optional[int] = Field(default=None)
    batch_size: int = Field(default=100, ge=1, le=2048)
    timeout: float = Field(default=60.0, gt=0)

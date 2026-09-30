"""Google/Gemini integration configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class GoogleGenAIConfig(BaseModel):
    """Configuration for Google Generative AI (Gemini) chat models."""
    
    # Required
    api_key_env: str = Field(..., description="Environment variable name for Google API key")
    
    # Model parameters
    model: str = Field(default="gemini-1.5-pro", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Safety settings
    safety_settings: Optional[dict] = Field(default=None)
    
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


class GoogleVertexAIConfig(BaseModel):
    """Configuration for Google Vertex AI (Gemini Enterprise)."""
    
    # Required
    project_id: str = Field(..., description="Google Cloud project ID")
    location: str = Field(default="us-central1", description="Vertex AI location")
    credentials_env: Optional[str] = Field(default=None, description="Environment variable for credentials JSON")
    
    # Model parameters
    model: str = Field(default="gemini-1.5-pro-001", description="Model name")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    top_k: Optional[int] = Field(default=None, ge=1)
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=True,
            tools=True,
            structured_output=True,
            multimodal=True,
        )
    )


class GoogleEmbeddingsConfig(BaseModel):
    """Configuration for Google Generative AI embeddings."""
    
    api_key_env: str = Field(..., description="Environment variable for Google API key")
    model: str = Field(default="models/gemini-embedding-001", description="Embedding model")
    dimensions: Optional[int] = Field(default=None, description="Output dimensions")
    batch_size: int = Field(default=100, ge=1, le=2048)
    timeout: float = Field(default=60.0, gt=0)

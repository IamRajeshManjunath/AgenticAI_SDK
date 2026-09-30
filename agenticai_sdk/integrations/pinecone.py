"""Pinecone vector store configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class PineconeVectorStoreConfig(BaseModel):
    """Configuration for Pinecone vector store."""
    
    # Connection
    api_key_env: str = Field(..., description="Pinecone API key environment variable")
    environment: Optional[str] = Field(default=None, description="Pinecone environment (deprecated)")
    index_name: str = Field(..., description="Index name")
    
    # Index config (for creation)
    dimension: int = Field(..., ge=1, description="Vector dimension")
    metric: str = Field(default="cosine", pattern="^(cosine|euclidean|dotproduct)$")
    cloud: str = Field(default="aws", pattern="^(aws|gcp|azure)$")
    region: str = Field(default="us-east-1")
    
    # Pod config (for legacy)
    pod_type: Optional[str] = Field(default=None)
    pods: int = Field(default=1)
    replicas: int = Field(default=1)
    
    # Serverless
    serverless: bool = Field(default=True)
    
    # Timeouts
    timeout: float = Field(default=30.0, gt=0)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=False,
            tools=False,
            structured_output=False,
            multimodal=False,
        )
    )

"""Qdrant vector store configuration."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from agenticai_sdk.config.schemas import FeatureFlags


class QdrantVectorStoreConfig(BaseModel):
    """Configuration for Qdrant vector store."""
    
    # Connection
    url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    api_key_env: Optional[str] = Field(default=None, description="API key env var (for cloud)")
    
    # Collection
    collection_name: str = Field(..., description="Collection name")
    vector_dimension: int = Field(..., ge=1, description="Vector dimension (must match embedding model)")
    distance: str = Field(default="Cosine", pattern="^(Cosine|Euclid|Dot|Manhattan)$")
    
    # Performance
    hnsw_config: Optional[dict] = Field(default=None)
    quantization_config: Optional[dict] = Field(default=None)
    on_disk_payload: bool = Field(default=False)
    
    # Timeouts
    timeout: float = Field(default=30.0, gt=0)
    prefer_grpc: bool = Field(default=False)
    
    features: FeatureFlags = Field(
        default_factory=lambda: FeatureFlags(
            stream=False,
            tools=False,
            structured_output=False,
            multimodal=False,
        )
    )


class QdrantCheckpointerConfig(BaseModel):
    """Configuration for Qdrant as LangGraph checkpointer (if supported)."""
    
    url: str = Field(default="http://localhost:6333")
    api_key_env: Optional[str] = None
    collection_name: str = Field(default="langgraph_checkpoints")
    timeout: float = Field(default=30.0)

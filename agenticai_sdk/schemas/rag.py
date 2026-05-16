"""RAG (Retrieval-Augmented Generation) configuration schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class VectorDBProvider(str, Enum):
    """Supported vector database backends."""

    QDRANT = "qdrant"
    PINECONE = "pinecone"
    PGVECTOR = "pgvector"
    CHROMADB = "chromadb"
    FIAAS = "fiaas"


class EmbeddingProvider(str, Enum):
    """Supported embedding model providers."""

    OPENAI = "openai"
    HUGGINGFACE = "huggingface"


class RAGConfig(BaseModel):
    """Knowledge base and semantic retrieval configuration.

    Attributes:
        rag_id: Unique identifier for this RAG source.
        vector_db: Vector database backend.
        connection_uri: Connection URI for the vector DB instance.
        api_key_env_var: Optional env var holding the vector DB API key.
        embedding_provider: Provider for text-to-embedding conversion.
        embedding_model: Specific embedding model identifier.
        collection_name: Name of the target collection/index.
        top_k: Number of top results to retrieve per query.
        similarity_threshold: Minimum similarity score for inclusion.
    """

    rag_id: str = Field(
        ...,
        min_length=1,
        description="Globally unique RAG source identifier.",
    )
    vector_db: VectorDBProvider = Field(
        ...,
        description="Vector database backend (qdrant, pinecone, pgvector).",
    )
    connection_uri: str = Field(
        ...,
        min_length=1,
        description="Connection URI for the vector database.",
    )
    api_key_env_var: str | None = Field(
        default=None,
        description="Env var name holding the vector DB API key (optional).",
    )
    embedding_provider: EmbeddingProvider = Field(
        ...,
        description="Embedding provider (openai, huggingface).",
    )
    embedding_model: str = Field(
        ...,
        min_length=1,
        description="Embedding model identifier (e.g. text-embedding-3-small).",
    )
    collection_name: str = Field(
        ...,
        min_length=1,
        description="Target collection or index name in the vector DB.",
    )
    top_k: int = Field(
        default=5,
        ge=1,
        le=100,
        description="Number of top results to retrieve per query.",
    )
    similarity_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum cosine similarity score for result inclusion.",
    )
    hybrid_search: bool = Field(
        default=False,
        description="Enable hybrid (dense + sparse BM25) search if supported by the vector DB.",
    )

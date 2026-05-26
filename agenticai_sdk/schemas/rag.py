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
    UNIVERSAL = "universal"


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
        default="text-embedding-3-small",
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

    # Universal connector fields (only used when vector_db == "universal")
    universal_base_url: str | None = Field(
        default=None,
        description="Base URL for the universal RAG connector.",
    )
    universal_search_endpoint: str | None = Field(
        default=None,
        description="Search endpoint path for the universal connector.",
    )
    universal_upsert_endpoint: str | None = Field(
        default=None,
        description="Upsert endpoint path for the universal connector.",
    )
    universal_request_template: dict | None = Field(
        default=None,
        description="JSON request template with {query}, {vector}, {top_k} placeholders.",
    )
    universal_response_path: str | None = Field(
        default=None,
        description="Dot-notation path to extract results from the response.",
    )
    universal_content_field: str | None = Field(
        default=None,
        description="Field name for document text in results.",
    )
    universal_score_field: str | None = Field(
        default=None,
        description="Field name for similarity score in results.",
    )
    universal_headers: dict[str, str] | None = Field(
        default=None,
        description="Additional HTTP headers for universal connector requests.",
    )
    universal_auth_type: str | None = Field(
        default=None,
        description="Auth type for universal connector (bearer, basic, api-key).",
    )
    universal_auth_value: str | None = Field(
        default=None,
        description="Auth value for universal connector.",
    )

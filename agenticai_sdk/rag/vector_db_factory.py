"""
VectorDBClientFactory — resolves RAGConfig into initialized async-capable
vector database clients and embeddings providers.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from agenticai_sdk.exceptions import EmbeddingError, VectorDBConnectionError
from agenticai_sdk.schemas.rag import EmbeddingProvider, RAGConfig, VectorDBProvider

logger = structlog.get_logger(__name__)


class VectorDBClientFactory:
    """Factory that resolves ``RAGConfig`` into a usable vector DB client
    and the corresponding LangChain ``Embeddings`` instance.

    Usage::

        factory = VectorDBClientFactory()
        client, embeddings = await factory.create(rag_config)
    """

    async def create(self, config: RAGConfig) -> tuple[Any, Any]:
        """Create and return ``(vector_db_client, embeddings_instance)``.

        Args:
            config: Validated RAGConfig describing the vector DB and embedding backend.

        Returns:
            A 2-tuple of (vector_db_client, LangChain Embeddings instance).

        Raises:
            VectorDBConnectionError: If the DB client cannot be initialised.
            EmbeddingError: If the embeddings provider cannot be initialised.
        """
        client = await self._resolve_vector_db(config)
        embeddings = self._resolve_embeddings(config)
        logger.info(
            "vector_db_client_created",
            provider=config.vector_db.value,
            collection=config.collection_name,
            embedding_provider=config.embedding_provider.value,
        )
        return client, embeddings

    # ── Vector DB resolution ─────────────────────────────────────────────

    async def _resolve_vector_db(self, config: RAGConfig) -> Any:
        """Instantiate the async vector DB client based on provider type."""
        api_key = os.getenv(config.api_key_env_var) if config.api_key_env_var else None

        try:
            if config.vector_db == VectorDBProvider.QDRANT:
                return await self._create_qdrant_client(config.connection_uri, api_key)
            elif config.vector_db == VectorDBProvider.PINECONE:
                return await self._create_pinecone_client(config.connection_uri, api_key)
            elif config.vector_db == VectorDBProvider.PGVECTOR:
                return await self._create_pgvector_client(config.connection_uri)
            elif config.vector_db == VectorDBProvider.CHROMADB:
                return await self._create_chroma_client(config.connection_uri)
            elif config.vector_db == VectorDBProvider.FIAAS:
                return await self._create_fiaas_client(config.connection_uri)
            else:
                raise VectorDBConnectionError(
                    f"Unsupported vector DB provider: {config.vector_db}",
                    detail={"provider": config.vector_db.value},
                )
        except VectorDBConnectionError:
            raise
        except Exception as exc:
            raise VectorDBConnectionError(
                f"Failed to create vector DB client for '{config.vector_db.value}': {exc}",
                detail={"provider": config.vector_db.value, "error": str(exc)},
            ) from exc

    async def _create_qdrant_client(self, uri: str, api_key: str | None) -> Any:
        """Create an async Qdrant client."""
        try:
            from qdrant_client import AsyncQdrantClient

            return AsyncQdrantClient(url=uri, api_key=api_key)
        except ImportError:
            logger.warning("qdrant_client not installed — returning mock client")
            return _MockVectorDBClient("qdrant", uri)

    async def _create_pinecone_client(self, uri: str, api_key: str | None) -> Any:
        """Create a Pinecone client."""
        try:
            from pinecone import Pinecone

            return Pinecone(api_key=api_key)
        except ImportError:
            logger.warning("pinecone-client not installed — returning mock client")
            return _MockVectorDBClient("pinecone", uri)

    async def _create_pgvector_client(self, uri: str) -> Any:
        """Create a PgVector connection (mock for now)."""
        logger.info("pgvector_client_stub", uri=uri)
        return _MockVectorDBClient("pgvector", uri)

    async def _create_chroma_client(self, uri: str) -> Any:
        """Create a ChromaDB client."""
        try:
            import chromadb
            from chromadb.config import Settings
            
            # If URI is a path, use PersistentClient; otherwise use HttpClient
            if "://" in uri:
                host, port = uri.split("://")[1].split(":")
                return chromadb.HttpClient(host=host, port=port)
            else:
                return chromadb.PersistentClient(path=uri)
        except ImportError:
            logger.warning("chromadb not installed — returning mock client")
            return _MockVectorDBClient("chromadb", uri)

    async def _create_fiaas_client(self, uri: str) -> Any:
        """Create a FIAAS (FAISS) client."""
        try:
            import faiss
            logger.info("faiss_client_initialized", path=uri)
            # FAISS is a library; usually wrapped by LangChain. 
            # We return a stub that points to the local index.
            return _MockVectorDBClient("fiaas", uri)
        except ImportError:
            logger.warning("faiss-cpu not installed — returning mock client")
            return _MockVectorDBClient("fiaas", uri)

    # ── Embeddings resolution ────────────────────────────────────────────

    def _resolve_embeddings(self, config: RAGConfig) -> Any:
        """Instantiate the LangChain Embeddings provider."""
        try:
            if config.embedding_provider == EmbeddingProvider.OPENAI:
                return self._create_openai_embeddings(config)
            elif config.embedding_provider == EmbeddingProvider.HUGGINGFACE:
                return self._create_huggingface_embeddings(config)
            else:
                raise EmbeddingError(
                    f"Unsupported embedding provider: {config.embedding_provider}",
                    detail={"provider": config.embedding_provider.value},
                )
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                f"Failed to create embeddings for '{config.embedding_provider.value}': {exc}",
                detail={"provider": config.embedding_provider.value, "error": str(exc)},
            ) from exc

    def _create_openai_embeddings(self, config: RAGConfig) -> Any:
        """Create OpenAI embeddings via LangChain."""
        try:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(model=config.embedding_model)
        except ImportError:
            logger.warning("langchain-openai not installed — returning mock embeddings")
            return _MockEmbeddings(config.embedding_model)

    def _create_huggingface_embeddings(self, config: RAGConfig) -> Any:
        """Create HuggingFace embeddings via LangChain."""
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings

            return HuggingFaceEmbeddings(model_name=config.embedding_model)
        except ImportError:
            logger.warning("langchain-community HuggingFace embeddings not available — returning mock")
            return _MockEmbeddings(config.embedding_model)


# ── Mock implementations for graceful degradation ────────────────────────────


class _MockVectorDBClient:
    """Lightweight mock vector DB client for development and testing."""

    def __init__(self, provider: str, uri: str) -> None:
        self.provider = provider
        self.uri = uri

    async def search(self, *args: Any, **kwargs: Any) -> list:
        logger.debug("mock_vector_db_search", provider=self.provider)
        return []

    def __repr__(self) -> str:
        return f"<MockVectorDBClient provider={self.provider!r}>"


class _MockEmbeddings:
    """Lightweight mock embeddings for development and testing."""

    def __init__(self, model: str) -> None:
        self.model = model

    async def aembed_query(self, text: str) -> list[float]:
        return [0.0] * 384

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[0.0] * 384 for _ in texts]

    def __repr__(self) -> str:
        return f"<MockEmbeddings model={self.model!r}>"

"""
KnowledgeRetrieverEngine — exposes vector store instances as unified
LangChain BaseRetriever components with async retrieval and score filtering.
"""

from __future__ import annotations

from typing import Any

import structlog
from langchain_core.documents import Document

from agenticai_sdk.exceptions import RAGFetchException
from agenticai_sdk.schemas.rag import RAGConfig

logger = structlog.get_logger(__name__)


class KnowledgeRetrieverEngine:
    """Unified retrieval engine wrapping vector DB clients behind a
    consistent async interface.

    Usage::

        engine = KnowledgeRetrieverEngine(db_client, embeddings)
        docs = await engine.retrieve_context("How does X work?", rag_config)
    """

    def __init__(self, db_client: Any, embeddings: Any) -> None:
        self._db_client = db_client
        self._embeddings = embeddings

    async def retrieve_context(
        self,
        query: str,
        config: RAGConfig,
    ) -> list[Document]:
        """Retrieve relevant documents from the vector store.

        Args:
            query: The natural language query to search for.
            config: RAGConfig specifying collection, top_k, and threshold.

        Returns:
            List of LangChain Document objects that pass the similarity threshold.

        Raises:
            RAGFetchException: If the retrieval operation fails.
        """
        try:
            logger.info(
                "rag_retrieve_start",
                query_preview=query[:80],
                collection=config.collection_name,
                top_k=config.top_k,
            )

            # Step 1: Embed the query
            query_embedding = await self._embed_query(query)

            # Step 2: Search the vector store
            raw_results = await self._search_vector_store(
                query_embedding=query_embedding,
                collection_name=config.collection_name,
                top_k=config.top_k,
            )

            # Step 3: Filter by similarity threshold
            filtered = self._apply_threshold(raw_results, config.similarity_threshold)

            logger.info(
                "rag_retrieve_complete",
                total_results=len(raw_results),
                filtered_results=len(filtered),
                threshold=config.similarity_threshold,
            )

            return filtered

        except RAGFetchException:
            raise
        except Exception as exc:
            raise RAGFetchException(
                f"Failed to retrieve context from '{config.collection_name}': {exc}",
                detail={
                    "collection": config.collection_name,
                    "error": str(exc),
                },
            ) from exc

    async def _embed_query(self, query: str) -> list[float]:
        """Embed the query string using the configured embeddings provider."""
        if hasattr(self._embeddings, "aembed_query"):
            return await self._embeddings.aembed_query(query)
        elif hasattr(self._embeddings, "embed_query"):
            return self._embeddings.embed_query(query)
        else:
            logger.warning("embeddings_provider_has_no_embed_method")
            return [0.0] * 384

    async def _search_vector_store(
        self,
        query_embedding: list[float],
        collection_name: str,
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Execute the vector similarity search.

        Returns raw results as dicts with 'content', 'metadata', and 'score' keys.
        """
        # Attempt async search if available
        if hasattr(self._db_client, "search"):
            results = await self._db_client.search(
                collection_name=collection_name,
                query_vector=query_embedding,
                limit=top_k,
            )
            # Normalize results to a common format
            return [
                {
                    "content": getattr(r, "payload", {}).get("content", str(r)),
                    "metadata": getattr(r, "payload", {}),
                    "score": getattr(r, "score", 0.0),
                }
                for r in results
            ]
        else:
            logger.debug("vector_db_client_has_no_search — returning empty results")
            return []

    def _apply_threshold(
        self,
        results: list[dict[str, Any]],
        threshold: float,
    ) -> list[Document]:
        """Filter results by similarity score and convert to LangChain Documents."""
        documents: list[Document] = []
        for result in results:
            score = result.get("score", 0.0)
            if score >= threshold:
                documents.append(
                    Document(
                        page_content=result.get("content", ""),
                        metadata={
                            **result.get("metadata", {}),
                            "similarity_score": score,
                        },
                    )
                )
        return documents

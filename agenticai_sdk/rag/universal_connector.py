"""Universal RAG Connector — generic HTTP client for any RAG database.

Lets users connect to any vector database that exposes an HTTP API
by providing endpoint URLs, authentication, and a request/response template.
"""

from __future__ import annotations

from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class UniversalRAGConnectorConfig(BaseModel):
    """Configuration for the universal HTTP RAG connector.

    Attributes:
        base_url: Root URL of the RAG service (e.g. http://my-rag:8080).
        search_endpoint: Path for similarity search (e.g. /api/search).
        upsert_endpoint: Path for inserting documents (e.g. /api/upsert).
        delete_endpoint: Path for deleting documents (e.g. /api/delete).
        auth_type: Authentication method — bearer, basic, api-key, or null.
        auth_value: Token, key, or credentials for authentication.
        headers: Additional HTTP headers to include on every request.
        request_template: JSON body template with {query}, {vector}, {top_k} placeholders.
        response_path: Dot-notation path to extract results array (e.g. results.hits).
        content_field: Field name for document text within each result.
        score_field: Field name for similarity score within each result.
    """

    base_url: str = Field(..., description="Root URL of the RAG service.")
    search_endpoint: str = Field("/search", description="Path for similarity search.")
    upsert_endpoint: str = Field("/upsert", description="Path for inserting documents.")
    delete_endpoint: str | None = Field(None, description="Path for deleting documents.")
    auth_type: str | None = Field(None, description="Authentication method: bearer, basic, api-key.")
    auth_value: str | None = Field(None, description="Token, key, or credentials.")
    headers: dict[str, str] = Field(default_factory=dict, description="Additional HTTP headers.")
    request_template: dict[str, Any] = Field(
        default_factory=lambda: {"query": "{query}", "top_k": "{top_k}"},
        description="JSON body template with {placeholders}.",
    )
    response_path: str = Field(
        "results",
        description="Dot-notation path to extract results array.",
    )
    content_field: str = Field("content", description="Field name for document text.")
    score_field: str = Field("score", description="Field name for similarity score.")


class UniversalRAGConnector:
    """Generic HTTP RAG connector — works with any REST-based vector database.

    Usage::

        config = UniversalRAGConnectorConfig(
            base_url="http://localhost:8080",
            search_endpoint="/v1/query",
            request_template={"text": "{query}", "limit": "{top_k}"},
            response_path="data.matches",
        )
        connector = UniversalRAGConnector(config)
        results = await connector.search("What is LangGraph?", top_k=5)
    """

    def __init__(self, config: UniversalRAGConnectorConfig) -> None:
        self.config = config
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            headers = dict(self.config.headers)
            if self.config.auth_type == "bearer" and self.config.auth_value:
                headers["Authorization"] = f"Bearer {self.config.auth_value}"
            elif self.config.auth_type == "api-key" and self.config.auth_value:
                headers["X-API-Key"] = self.config.auth_value

            auth: httpx.Auth | None = None
            if self.config.auth_type == "basic" and self.config.auth_value:
                parts = self.config.auth_value.split(":", 1)
                if len(parts) == 2:
                    auth = httpx.BasicAuth(parts[0], parts[1])

            self._client = httpx.AsyncClient(base_url=self.config.base_url, headers=headers, auth=auth)
        return self._client

    async def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Search the RAG database with a text query."""
        client = await self._get_client()
        body = self._fill_template(self.config.request_template, query=query, top_k=top_k)
        url = self.config.search_endpoint

        logger.info("universal_rag_search", url=url, top_k=top_k)
        try:
            resp = await client.post(url, json=body, timeout=30.0)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPStatusError as exc:
            logger.error("universal_rag_http_error", status=exc.response.status_code, body=exc.response.text)
            return []
        except Exception as exc:
            logger.error("universal_rag_search_failed", error=str(exc))
            return []

        results = self._extract_results(data)
        return results

    async def upsert(self, documents: list[dict[str, Any]]) -> bool:
        """Insert or update documents."""
        client = await self._get_client()
        url = self.config.upsert_endpoint
        try:
            resp = await client.post(url, json={"documents": documents}, timeout=60.0)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("universal_rag_upsert_failed", error=str(exc))
            return False

    async def delete(self, ids: list[str]) -> bool:
        """Delete documents by ID."""
        if not self.config.delete_endpoint:
            logger.warning("universal_rag_no_delete_endpoint")
            return False
        client = await self._get_client()
        try:
            resp = await client.post(self.config.delete_endpoint, json={"ids": ids}, timeout=30.0)
            resp.raise_for_status()
            return True
        except Exception as exc:
            logger.error("universal_rag_delete_failed", error=str(exc))
            return False

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    def _fill_template(self, template: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        import json
        raw = json.dumps(template)
        for key, val in kwargs.items():
            raw = raw.replace(f"{{{key}}}", str(val))
        return json.loads(raw)

    def _extract_results(self, data: Any) -> list[dict[str, Any]]:
        """Extract results from response using dot-notation response_path."""
        current = data
        for part in self.config.response_path.split("."):
            if isinstance(current, dict):
                current = current.get(part, [])
            else:
                return []

        if not isinstance(current, list):
            return []

        normalized: list[dict[str, Any]] = []
        for item in current:
            if isinstance(item, dict):
                normalized.append({
                    "content": item.get(self.config.content_field, str(item)),
                    "score": item.get(self.config.score_field, 0.0),
                    "metadata": {k: v for k, v in item.items()
                                 if k not in (self.config.content_field, self.config.score_field)},
                })
        return normalized

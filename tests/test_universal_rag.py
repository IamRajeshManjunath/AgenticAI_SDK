"""Tests for the Universal RAG Connector."""

from __future__ import annotations

import pytest

from agenticai_sdk.rag.universal_connector import (
    UniversalRAGConnector,
    UniversalRAGConnectorConfig,
)


class TestUniversalRAGConnectorConfig:
    def test_default_template(self):
        config = UniversalRAGConnectorConfig(base_url="http://localhost:8080")
        assert config.base_url == "http://localhost:8080"
        assert config.search_endpoint == "/search"
        assert config.request_template == {"query": "{query}", "top_k": "{top_k}"}
        assert config.response_path == "results"

    def test_custom_config(self):
        config = UniversalRAGConnectorConfig(
            base_url="http://my-rag:8000",
            search_endpoint="/v1/query",
            request_template={"text": "{query}", "limit": "{top_k}"},
            response_path="data.matches",
            content_field="text",
            score_field="relevance",
        )
        assert config.search_endpoint == "/v1/query"
        assert config.content_field == "text"
        assert config.score_field == "relevance"


class TestUniversalRAGConnector:
    @pytest.mark.asyncio
    async def test_fill_template(self):
        config = UniversalRAGConnectorConfig(base_url="http://localhost:8080")
        connector = UniversalRAGConnector(config)
        filled = connector._fill_template(
            {"query": "{query}", "top_k": "{top_k}"},
            query="hello", top_k=5,
        )
        assert filled["query"] == "hello"
        assert str(filled["top_k"]) == "5"

    def test_extract_results_dot_path(self):
        config = UniversalRAGConnectorConfig(
            base_url="http://localhost:8080",
            response_path="data.results",
            content_field="content",
            score_field="score",
        )
        connector = UniversalRAGConnector(config)
        response = {
            "data": {
                "results": [
                    {"content": "doc1", "score": 0.9, "id": "1"},
                    {"content": "doc2", "score": 0.8, "id": "2"},
                ]
            }
        }
        results = connector._extract_results(response)
        assert len(results) == 2
        assert results[0]["content"] == "doc1"
        assert results[0]["score"] == 0.9
        assert results[0]["metadata"]["id"] == "1"

    def test_extract_results_flat_path(self):
        config = UniversalRAGConnectorConfig(
            base_url="http://localhost:8080",
            response_path="results",
        )
        connector = UniversalRAGConnector(config)
        response = {"results": [{"content": "doc1", "score": 0.95}]}
        results = connector._extract_results(response)
        assert len(results) == 1
        assert results[0]["content"] == "doc1"

    def test_extract_results_empty(self):
        config = UniversalRAGConnectorConfig(base_url="http://localhost:8080")
        connector = UniversalRAGConnector(config)
        assert connector._extract_results({}) == []
        assert connector._extract_results({"results": []}) == []
        assert connector._extract_results({"results": "not_a_list"}) == []

    @pytest.mark.asyncio
    async def test_search_http_error(self):
        config = UniversalRAGConnectorConfig(base_url="http://localhost:1")
        connector = UniversalRAGConnector(config)
        results = await connector.search("test query", top_k=3)
        assert results == []

    @pytest.mark.asyncio
    async def test_close(self):
        config = UniversalRAGConnectorConfig(base_url="http://localhost:8080")
        connector = UniversalRAGConnector(config)
        await connector.close()
        assert connector._client is None or connector._client.is_closed

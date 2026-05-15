"""Tests for the RAG subsystem components."""

from __future__ import annotations

import pytest

from agenticai_sdk.rag.context_injector import ContextInjector

# Use langchain_core Documents for testing
from langchain_core.documents import Document


class TestContextInjector:
    def test_format_empty_documents(self):
        result = ContextInjector.format_documents([])
        assert result == ""

    def test_format_single_document(self):
        docs = [
            Document(
                page_content="LangGraph is a framework for building stateful agents.",
                metadata={"source": "langgraph_docs", "similarity_score": 0.92},
            )
        ]
        result = ContextInjector.format_documents(docs)
        assert "=== Retrieved Knowledge Context ===" in result
        assert "[Source: langgraph_docs]" in result
        assert "(relevance: 0.920)" in result
        assert "LangGraph is a framework" in result
        assert "=== End Knowledge Context ===" in result

    def test_format_multiple_documents(self):
        docs = [
            Document(page_content="Doc 1 content", metadata={"source": "a", "similarity_score": 0.9}),
            Document(page_content="Doc 2 content", metadata={"source": "b", "similarity_score": 0.8}),
            Document(page_content="Doc 3 content", metadata={"source": "c", "similarity_score": 0.7}),
        ]
        result = ContextInjector.format_documents(docs)
        assert result.count("[Source:") == 3

    def test_format_without_scores(self):
        docs = [
            Document(page_content="Content", metadata={"source": "test", "similarity_score": 0.85}),
        ]
        result = ContextInjector.format_documents(docs, include_scores=False)
        assert "relevance" not in result

    def test_format_truncates_long_content(self):
        long_content = "x" * 5000
        docs = [Document(page_content=long_content, metadata={"source": "big"})]
        result = ContextInjector.format_documents(docs, max_chars_per_doc=100)
        # The formatted content should not contain all 5000 chars
        assert len(result) < 500

    def test_format_as_dicts(self):
        docs = [
            Document(
                page_content="Hello world",
                metadata={"source": "test_src", "similarity_score": 0.88, "page": 5},
            ),
        ]
        result = ContextInjector.format_as_dicts(docs)
        assert len(result) == 1
        assert result[0]["content"] == "Hello world"
        assert result[0]["source"] == "test_src"
        assert result[0]["score"] == 0.88
        assert "page" in result[0]["metadata"]
        # similarity_score should be excluded from the nested metadata
        assert "similarity_score" not in result[0]["metadata"]

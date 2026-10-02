"""Tests for the Python client SDK (agenticai_sdk/client.py)."""
from __future__ import annotations

import json
from unittest import mock

import httpx
import pytest

from agenticai_sdk.client import AgenticAI


def _mock_run_response():
    request = httpx.Request("POST", "http://test/api/v1/workflow/run")
    return httpx.Response(
        200,
        json={
            "thread_id": "thr_abc123",
            "status": "complete",
            "messages": [
                {"type": "human", "content": "Hello"},
                {"type": "ai", "content": "Hi! How can I help you?"},
            ],
            "scratchpad": {"result": "done"},
            "retrieved_context": [],
            "inner_thoughts": [],
            "next_step": None,
        },
        request=request,
    )


class TestAgenticAIInit:
    def test_init_sets_headers(self):
        client = AgenticAI(api_key="wfk_test123", base_url="http://example.com")
        assert client.api_key == "wfk_test123"
        assert client._client.headers["X-API-Key"] == "wfk_test123"
        assert client._client.headers["Content-Type"] == "application/json"
        client.close()

    def test_init_custom_timeout(self):
        client = AgenticAI(api_key="wfk_test", timeout=60.0)
        assert client._client.timeout == httpx.Timeout(60.0)
        client.close()


class TestRun:
    def test_run_sends_request(self):
        client = AgenticAI(api_key="wfk_test123")

        with mock.patch.object(client._client, "post", return_value=_mock_run_response()) as mock_post:
            result = client.run("Hello")

        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["json"]["input_message"] == "Hello"
        assert result["status"] == "complete"
        client.close()

    def test_run_with_workflow_id(self):
        client = AgenticAI(api_key="agk_test123")

        with mock.patch.object(client._client, "post", return_value=_mock_run_response()) as mock_post:
            result = client.run("Hello", workflow_id="wf_123")

        mock_post.assert_called_once()
        assert mock_post.call_args[0][0] == "/api/v1/workflow/run"
        assert mock_post.call_args[1]["json"]["workflow_id"] == "wf_123"
        assert result["status"] == "complete"
        client.close()

    def test_run_with_thread_id(self):
        client = AgenticAI(api_key="wfk_test")

        with mock.patch.object(client._client, "post", return_value=_mock_run_response()) as mock_post:
            client.run("Task", thread_id="thr_custom")

        assert mock_post.call_args[1]["json"]["thread_id"] == "thr_custom"
        client.close()

    def test_run_with_scratchpad(self):
        client = AgenticAI(api_key="wfk_test")

        with mock.patch.object(client._client, "post", return_value=_mock_run_response()) as mock_post:
            client.run("Task", initial_scratchpad={"key": "val"})

        assert mock_post.call_args[1]["json"]["initial_scratchpad"] == {"key": "val"}
        client.close()

    def test_run_raises_on_error(self):
        client = AgenticAI(api_key="wfk_test")

        error_request = httpx.Request("POST", "http://test/api/v1/workflow/run")
        error_resp = httpx.Response(404, json={"detail": "Not found"}, request=error_request)
        with mock.patch.object(client._client, "post", return_value=error_resp):
            with pytest.raises(httpx.HTTPStatusError):
                client.run("Hello")

        client.close()


class TestRunById:
    def test_run_by_id_sends_request(self):
        client = AgenticAI(api_key="wfk_test")

        with mock.patch.object(client._client, "post", return_value=_mock_run_response()) as mock_post:
            result = client.run_by_id("wf_456", "Hello")

        mock_post.assert_called_once_with(
            "/api/v1/workflow/run/wf_456",
            json={"input_message": "Hello"},
        )
        assert result["status"] == "complete"
        client.close()

    def test_run_by_id_with_optional_params(self):
        client = AgenticAI(api_key="wfk_test")

        with mock.patch.object(client._client, "post", return_value=_mock_run_response()) as mock_post:
            client.run_by_id("wf_789", "Task", thread_id="thr_1", initial_scratchpad={"x": 1})

        assert mock_post.call_args[1]["json"] == {
            "input_message": "Task",
            "thread_id": "thr_1",
            "initial_scratchpad": {"x": 1},
        }
        client.close()

    def test_run_by_id_raises_on_error(self):
        client = AgenticAI(api_key="wfk_test")

        error_request = httpx.Request("POST", "http://test/api/v1/workflow/run/wf_bad")
        error_resp = httpx.Response(500, json={"detail": "Server error"}, request=error_request)
        with mock.patch.object(client._client, "post", return_value=error_resp):
            with pytest.raises(httpx.HTTPStatusError):
                client.run_by_id("wf_bad", "Hello")

        client.close()


class TestLastMessage:
    def test_last_message_returns_content(self):
        result = {
            "messages": [
                {"type": "human", "content": "Hello"},
                {"type": "ai", "content": "Hi!"},
            ]
        }
        client = AgenticAI(api_key="wfk_test")
        assert client.last_message(result) == "Hi!"
        client.close()

    def test_last_message_empty(self):
        client = AgenticAI(api_key="wfk_test")
        assert client.last_message({"messages": []}) == ""
        client.close()

    def test_last_message_no_messages_key(self):
        client = AgenticAI(api_key="wfk_test")
        assert client.last_message({}) == ""
        client.close()

    def test_last_message_missing_content(self):
        result = {"messages": [{"type": "ai"}]}
        client = AgenticAI(api_key="wfk_test")
        assert client.last_message(result) == ""
        client.close()


class TestClose:
    def test_close_called(self):
        client = AgenticAI(api_key="wfk_test")
        with mock.patch.object(client._client, "close") as mock_close:
            client.close()
        mock_close.assert_called_once()

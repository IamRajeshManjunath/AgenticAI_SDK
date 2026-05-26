"""Python client SDK for AgenticAI — run workflows from any application."""

from __future__ import annotations

from typing import Any

import httpx


class AgenticAI:
    """Client for invoking AgenticAI workflows programmatically.

    Usage:
        client = AgenticAI(api_key="wfk_a1b2c3d4e5f6...")
        result = client.run("What are your business hours?")
        print(result["messages"][-1]["content"])
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "http://localhost:8000",
        timeout: float = 120.0,
    ) -> None:
        self.api_key = api_key
        self._client = httpx.Client(
            base_url=base_url,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
            timeout=timeout,
        )

    def run(
        self,
        input_message: str,
        *,
        workflow_id: str | None = None,
        thread_id: str | None = None,
        initial_scratchpad: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a workflow and return the full result.

        With a workflow key (wfk_), the workflow is auto-resolved.
        With a workspace key (agk_), pass workflow_id explicitly.
        """
        body: dict[str, Any] = {"input_message": input_message}
        if workflow_id:
            body["workflow_id"] = workflow_id
        if thread_id:
            body["thread_id"] = thread_id
        if initial_scratchpad:
            body["initial_scratchpad"] = initial_scratchpad

        resp = self._client.post("/api/v1/workflow/run", json=body)
        resp.raise_for_status()
        return resp.json()

    def run_by_id(
        self,
        workflow_id: str,
        input_message: str,
        *,
        thread_id: str | None = None,
        initial_scratchpad: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a specific deployed workflow by its ID."""
        body: dict[str, Any] = {"input_message": input_message}
        if thread_id:
            body["thread_id"] = thread_id
        if initial_scratchpad:
            body["initial_scratchpad"] = initial_scratchpad

        resp = self._client.post(f"/api/v1/workflow/run/{workflow_id}", json=body)
        resp.raise_for_status()
        return resp.json()

    def last_message(self, result: dict[str, Any]) -> str:
        """Convenience: return the content of the last message in the result."""
        messages = result.get("messages", [])
        if not messages:
            return ""
        return messages[-1].get("content", "")

    def close(self) -> None:
        self._client.close()

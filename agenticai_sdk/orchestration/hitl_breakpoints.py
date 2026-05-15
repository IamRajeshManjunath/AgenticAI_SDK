"""
HITL Breakpoint Manager — freeze execution states to a persistence layer
and dispatch structured interactive payloads/webhooks to communication
endpoints (Slack / MS Teams) for manager approvals.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

import structlog
from pydantic import BaseModel, Field

from agenticai_sdk.exceptions import HITLDispatchError, HITLTimeoutError

logger = structlog.get_logger(__name__)


class HITLApprovalPayload(BaseModel):
    """Structured webhook payload for HITL approval requests."""

    workflow_id: str
    agent_id: str
    thread_id: str
    freeze_token: str
    state_summary: str
    action_url: str
    timestamp: str
    timeout_seconds: int = 3600


class HITLApprovalResult(BaseModel):
    """Result of a HITL approval request."""

    approved: bool
    reviewer: str | None = None
    comments: str | None = None
    state_overrides: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = ""


class HITLBreakpointManager:
    """Manages HITL breakpoints with state persistence and webhook dispatch.

    Provides:
      - State freeze/thaw via JSON file persistence
      - Webhook dispatch to Slack and MS Teams
      - Polling-based approval awaiting with timeout
    """

    def __init__(self, storage_dir: str = "./.hitl_states") -> None:
        self._storage_dir = Path(storage_dir)
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        self._pending_approvals: dict[str, HITLApprovalResult | None] = {}

    async def freeze_state(
        self,
        state: dict[str, Any],
        checkpoint_id: str,
        workflow_id: str = "",
        agent_id: str = "",
    ) -> str:
        """Serialize and persist the full workflow state."""
        freeze_token = f"hitl_{uuid.uuid4().hex[:12]}_{checkpoint_id}"

        serializable_state = self._make_serializable(state)
        freeze_record = {
            "freeze_token": freeze_token,
            "checkpoint_id": checkpoint_id,
            "workflow_id": workflow_id,
            "agent_id": agent_id,
            "frozen_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "state": serializable_state,
        }

        file_path = self._storage_dir / f"{freeze_token}.json"
        file_path.write_text(json.dumps(freeze_record, indent=2, default=str))
        self._pending_approvals[freeze_token] = None

        logger.info(
            "hitl_state_frozen",
            freeze_token=freeze_token,
            workflow_id=workflow_id,
            agent_id=agent_id,
        )
        return freeze_token

    async def dispatch_approval_request(
        self, channel: str, payload: HITLApprovalPayload
    ) -> bool:
        """Send an approval request to the specified notification channel."""
        try:
            if channel == "slack":
                return await self._dispatch_slack(payload)
            elif channel == "ms_teams":
                return await self._dispatch_teams(payload)
            elif channel == "web_hook":
                return await self._dispatch_webhook(payload)
            elif channel == "api_wait":
                logger.info("hitl_api_wait_mode", freeze_token=payload.freeze_token)
                return True
            else:
                logger.warning("hitl_unknown_channel", channel=channel)
                return False
        except HITLDispatchError:
            raise
        except Exception as exc:
            raise HITLDispatchError(
                f"Failed to dispatch HITL approval to '{channel}': {exc}",
                detail={"channel": channel, "freeze_token": payload.freeze_token},
            ) from exc

    async def await_approval(self, freeze_token: str, timeout: int = 3600) -> HITLApprovalResult:
        """Wait for an approval decision (polling-based)."""
        import asyncio

        start = time.perf_counter()
        poll_interval = 2.0

        while time.perf_counter() - start < timeout:
            result = self._pending_approvals.get(freeze_token)
            if result is not None:
                logger.info("hitl_approval_received", freeze_token=freeze_token, approved=result.approved)
                return result
            await asyncio.sleep(poll_interval)

        raise HITLTimeoutError(
            f"HITL approval timed out after {timeout}s for token '{freeze_token}'.",
            detail={"freeze_token": freeze_token, "timeout": timeout},
        )

    def submit_approval(
        self,
        freeze_token: str,
        approved: bool,
        reviewer: str | None = None,
        comments: str | None = None,
        state_overrides: dict[str, Any] | None = None,
    ) -> None:
        """Submit an approval decision (called by the API endpoint)."""
        self._pending_approvals[freeze_token] = HITLApprovalResult(
            approved=approved,
            reviewer=reviewer,
            comments=comments,
            state_overrides=state_overrides or {},
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        logger.info("hitl_approval_submitted", freeze_token=freeze_token, approved=approved)

    async def thaw_state(
        self, freeze_token: str, overrides: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Restore a frozen state with optional overrides."""
        file_path = self._storage_dir / f"{freeze_token}.json"
        if not file_path.exists():
            raise HITLDispatchError(
                f"Frozen state not found for token '{freeze_token}'.",
                detail={"freeze_token": freeze_token},
            )

        freeze_record = json.loads(file_path.read_text())
        state = freeze_record.get("state", {})

        if overrides:
            state.update(overrides)
            logger.info("hitl_state_thawed_with_overrides", freeze_token=freeze_token)
        else:
            logger.info("hitl_state_thawed", freeze_token=freeze_token)

        self._pending_approvals.pop(freeze_token, None)
        return state

    async def _dispatch_slack(self, payload: HITLApprovalPayload) -> bool:
        """Send a Slack notification with approval buttons."""
        webhook_url = os.getenv("HITL_SLACK_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("hitl_slack_webhook_not_configured")
            return False

        import httpx

        slack_message = {
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"🔔 HITL Approval — {payload.workflow_id}"},
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Agent:* `{payload.agent_id}`"},
                        {"type": "mrkdwn", "text": f"*Thread:* `{payload.thread_id}`"},
                        {"type": "mrkdwn", "text": f"*Token:* `{payload.freeze_token}`"},
                    ],
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Summary:*\n{payload.state_summary[:500]}"},
                },
            ],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(webhook_url, json=slack_message)
            resp.raise_for_status()

        logger.info("hitl_slack_dispatched", freeze_token=payload.freeze_token)
        return True

    async def _dispatch_teams(self, payload: HITLApprovalPayload) -> bool:
        """Send an MS Teams adaptive card for approval."""
        webhook_url = os.getenv("HITL_TEAMS_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("hitl_teams_webhook_not_configured")
            return False

        import httpx

        teams_card = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "summary": f"HITL Approval — {payload.workflow_id}",
            "themeColor": "0076D7",
            "title": f"🔔 HITL Approval Required — {payload.workflow_id}",
            "sections": [
                {
                    "activityTitle": f"Agent: {payload.agent_id}",
                    "facts": [
                        {"name": "Thread", "value": payload.thread_id},
                        {"name": "Token", "value": payload.freeze_token},
                    ],
                    "text": payload.state_summary[:500],
                }
            ],
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(webhook_url, json=teams_card)
            resp.raise_for_status()

        logger.info("hitl_teams_dispatched", freeze_token=payload.freeze_token)
        return True

    async def _dispatch_webhook(self, payload: HITLApprovalPayload) -> bool:
        """Send a generic webhook POST with the approval payload."""
        webhook_url = os.getenv("HITL_WEBHOOK_URL")
        if not webhook_url:
            logger.warning("hitl_webhook_not_configured")
            return False

        import httpx

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(webhook_url, json=payload.model_dump())
            resp.raise_for_status()

        logger.info("hitl_webhook_dispatched", freeze_token=payload.freeze_token)
        return True

    @staticmethod
    def _make_serializable(state: dict[str, Any]) -> dict[str, Any]:
        """Convert a WorkflowState to a JSON-serializable dict."""
        result: dict[str, Any] = {}
        for key, value in state.items():
            if key == "messages":
                serialized_msgs = []
                for msg in value:
                    if hasattr(msg, "content"):
                        serialized_msgs.append({
                            "type": getattr(msg, "type", "message"),
                            "content": str(msg.content),
                        })
                    else:
                        serialized_msgs.append(str(msg))
                result[key] = serialized_msgs
            elif isinstance(value, (str, int, float, bool, type(None))):
                result[key] = value
            elif isinstance(value, (dict, list)):
                try:
                    json.dumps(value)
                    result[key] = value
                except (TypeError, ValueError):
                    result[key] = str(value)
            else:
                result[key] = str(value)
        return result

"""Human-in-the-loop (HITL) configuration schema."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    """Communication channel for HITL approval notifications."""

    SLACK = "slack"
    WEB_HOOK = "web_hook"
    API_WAIT = "api_wait"


class HITLConfig(BaseModel):
    """Human-in-the-loop validation checkpoint configuration.

    Attributes:
        interruption_points: Node IDs where execution must pause for human approval.
        approval_timeout: Maximum seconds to wait for approval before timing out.
        notification_channel: How the system notifies the reviewer.
    """

    interruption_points: list[str] = Field(
        default_factory=list,
        description="List of agent node IDs where the graph should interrupt for human review.",
    )
    approval_timeout: int = Field(
        default=3600,
        gt=0,
        description="Maximum wait time (seconds) for human approval before timeout.",
    )
    notification_channel: NotificationChannel = Field(
        default=NotificationChannel.API_WAIT,
        description="Channel used to notify the human reviewer.",
    )

"""Third-party integration configuration schema."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class IntegrationType(str, Enum):
    SLACK = "slack"
    TEAMS = "teams"
    OUTLOOK = "outlook"
    WHATSAPP = "whatsapp"


class IntegrationConfig(BaseModel):
    integration_type: IntegrationType = Field(
        ...,
        description="Third-party integration platform.",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable name for this connection.",
    )
    auth_state: dict[str, Any] = Field(
        default_factory=dict,
        description="OAuth tokens, webhook URLs, or API keys for authentication.",
    )
    rate_limits: dict[str, Any] | None = Field(
        default=None,
        description="Rate limiting configuration per connection.",
    )

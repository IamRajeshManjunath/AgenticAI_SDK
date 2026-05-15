"""Tool configuration schema."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ToolType(str, Enum):
    """Supported tool integration types."""

    MCP = "mcp"
    CUSTOM_PYTHON = "custom_python"
    REST_API = "rest_api"
    BUILT_IN = "built_in"


class ToolConfig(BaseModel):
    """External execution interface configuration.

    Attributes:
        tool_id: Unique identifier used to reference this tool across the workflow.
        type: Integration mechanism for the tool.
        connection_string: URI, module path, or endpoint used to locate the tool.
        arguments: Optional static arguments forwarded on every invocation.
    """

    tool_id: str = Field(
        ...,
        min_length=1,
        description="Globally unique tool identifier.",
    )
    type: ToolType = Field(
        ...,
        description="Tool integration type (mcp, custom_python, rest_api, built_in).",
    )
    connection_string: str = Field(
        ...,
        min_length=1,
        description="URI, module path, or endpoint for tool resolution.",
    )
    arguments: dict[str, Any] | None = Field(
        default=None,
        description="Optional static keyword arguments forwarded to the tool on every call.",
    )

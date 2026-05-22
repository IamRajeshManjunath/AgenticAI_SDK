"""Tool configuration schema."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


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
    connection_string: str | None = Field(
        default=None,
        description="URI, module path, or endpoint for tool resolution.",
    )
    arguments: dict[str, Any] | None = Field(
        default=None,
        description="Optional static keyword arguments forwarded to the tool on every call.",
    )
    name: str | None = Field(
        default=None,
        description="Optional human-readable name of the tool.",
    )
    description: str | None = Field(
        default=None,
        description="Optional tool description.",
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description="Nested configuration block for integration parameters.",
    )

    @model_validator(mode="before")
    @classmethod
    def _unwrap_config(cls, data: Any) -> Any:
        if isinstance(data, dict):
            cfg = data.get("config")
            if isinstance(cfg, dict):
                if "connection_string" in cfg and "connection_string" not in data:
                    data["connection_string"] = cfg["connection_string"]
                if "arguments" in cfg and "arguments" not in data:
                    data["arguments"] = cfg["arguments"]
                if "code" in cfg and "connection_string" not in data:
                    data["connection_string"] = cfg["code"]
                if "endpoint" in cfg and "connection_string" not in data:
                    data["connection_string"] = cfg["endpoint"]
            # Fallback for custom_python tool and others if connection_string is not set but exists in top level config
            if data.get("type") == "built_in" and "connection_string" not in data:
                # Use tool_id or default web_search as connection_string if not set
                data["connection_string"] = data.get("tool_id")
        return data

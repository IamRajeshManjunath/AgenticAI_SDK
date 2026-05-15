"""
ToolRegistry — instantiates and exposes tools via LangChain @tool / BaseTool.

Includes concrete mock implementations for MCP and REST API endpoints
to allow workflow testing without live external services.
"""

from __future__ import annotations

import httpx
import structlog
from langchain_core.tools import BaseTool, tool

from agenticai_sdk.exceptions import ToolResolutionError
from agenticai_sdk.schemas.tools import ToolConfig, ToolType

logger = structlog.get_logger(__name__)

# Global in-memory tool cache (shared across registry instances)
_TOOL_CACHE: dict[str, BaseTool] = {}


class ToolRegistry:
    """Resolves ``ToolConfig`` definitions into runnable LangChain ``BaseTool`` instances.

    Supports four tool types:
    - ``mcp``: Mock MCP protocol endpoint (async HTTP stub)
    - ``rest_api``: Async REST API caller via httpx
    - ``custom_python``: Dynamically imports a Python callable
    - ``built_in``: SDK-bundled utility tools

    Usage::

        registry = ToolRegistry()
        tools = registry.resolve_all(workflow_schema.tools)
        agent_tools = registry.get_tools_for_agent(agent_config.tools)
    """

    def __init__(self) -> None:
        self._registry: dict[str, BaseTool] = {}

    def resolve_all(self, tool_configs: list[ToolConfig]) -> "ToolRegistry":
        """Instantiate and register all tools from a list of ToolConfigs.

        Args:
            tool_configs: List of ToolConfig definitions from the WorkflowSchema.

        Returns:
            self (fluent interface).

        Raises:
            ToolResolutionError: If any tool cannot be instantiated.
        """
        for config in tool_configs:
            self._register(config)
        logger.info("tool_registry_loaded", count=len(self._registry), tool_ids=list(self._registry.keys()))
        return self

    def get_tools_for_agent(self, tool_ids: list[str]) -> list[BaseTool]:
        """Return the resolved tool instances for a given list of tool IDs.

        Args:
            tool_ids: List of tool_id strings from an AgentNodeConfig.

        Returns:
            List of resolved BaseTool instances.

        Raises:
            ToolResolutionError: If a referenced tool_id is not registered.
        """
        resolved: list[BaseTool] = []
        for tid in tool_ids:
            if tid not in self._registry:
                raise ToolResolutionError(
                    f"Tool '{tid}' is referenced by an agent but is not in the registry.",
                    detail={"tool_id": tid, "available": list(self._registry.keys())},
                )
            resolved.append(self._registry[tid])
        return resolved

    def _register(self, config: ToolConfig) -> None:
        """Instantiate a single tool and add it to the registry."""
        logger.debug("tool_registering", tool_id=config.tool_id, type=config.type.value)
        try:
            if config.type == ToolType.MCP:
                instance = _build_mcp_tool(config)
            elif config.type == ToolType.REST_API:
                instance = _build_rest_api_tool(config)
            elif config.type == ToolType.CUSTOM_PYTHON:
                instance = _build_custom_python_tool(config)
            elif config.type == ToolType.BUILT_IN:
                instance = _build_built_in_tool(config)
            else:
                raise ToolResolutionError(
                    f"Unknown tool type '{config.type}'",
                    detail={"tool_id": config.tool_id, "type": config.type.value},
                )

            self._registry[config.tool_id] = instance
            logger.info("tool_registered", tool_id=config.tool_id, type=config.type.value)

        except ToolResolutionError:
            raise
        except Exception as exc:
            raise ToolResolutionError(
                f"Failed to instantiate tool '{config.tool_id}': {exc}",
                detail={"tool_id": config.tool_id, "error": str(exc)},
            ) from exc


# ── Tool builder functions ────────────────────────────────────────────────────


def _build_mcp_tool(config: ToolConfig) -> BaseTool:
    """Build a mock MCP protocol tool that sends async HTTP requests."""
    connection = config.connection_string
    static_args = config.arguments or {}
    tool_id = config.tool_id

    class MCPTool(BaseTool):
        name: str = tool_id
        description: str = f"MCP tool connecting to {connection}"

        def _run(self, input_str: str, **kwargs) -> str:
            return f"[MCP Sync] Called {connection} with input: {input_str}"

        async def _arun(self, input_str: str, **kwargs) -> str:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    payload = {"input": input_str, **static_args}
                    response = await client.post(connection, json=payload)
                    response.raise_for_status()
                    return response.text
            except Exception as exc:
                return f"[MCP Error] {connection} returned: {exc}"

    return MCPTool()


def _build_rest_api_tool(config: ToolConfig) -> BaseTool:
    """Build an async REST API tool via httpx."""
    endpoint = config.connection_string
    static_args = config.arguments or {}
    tool_id = config.tool_id
    method = static_args.get("method", "POST").upper()

    class RestApiTool(BaseTool):
        name: str = tool_id
        description: str = f"REST API tool for {method} {endpoint}"

        def _run(self, input_str: str, **kwargs) -> str:
            return f"[REST Sync] {method} {endpoint} with: {input_str}"

        async def _arun(self, input_str: str, **kwargs) -> str:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method == "GET":
                        response = await client.get(endpoint, params={"q": input_str})
                    else:
                        response = await client.post(endpoint, json={"input": input_str, **static_args})
                    response.raise_for_status()
                    return response.text
            except Exception as exc:
                return f"[REST Error] {endpoint} → {exc}"

    return RestApiTool()


def _build_custom_python_tool(config: ToolConfig) -> BaseTool:
    """Dynamically import a Python callable at ``module:function`` connection_string."""
    connection = config.connection_string  # e.g. "my_package.tools:my_function"
    tool_id = config.tool_id

    try:
        module_path, func_name = connection.rsplit(":", 1)
        import importlib

        module = importlib.import_module(module_path)
        func = getattr(module, func_name)

        class CustomPythonTool(BaseTool):
            name: str = tool_id
            description: str = f"Custom Python tool: {connection}"

            def _run(self, input_str: str, **kwargs) -> str:
                return str(func(input_str, **(config.arguments or {})))

            async def _arun(self, input_str: str, **kwargs) -> str:
                import asyncio
                if asyncio.iscoroutinefunction(func):
                    return str(await func(input_str, **(config.arguments or {})))
                return str(func(input_str, **(config.arguments or {})))

        return CustomPythonTool()

    except (ImportError, AttributeError, ValueError) as exc:
        raise ToolResolutionError(
            f"Cannot import custom Python tool '{connection}': {exc}",
            detail={"tool_id": tool_id, "connection_string": connection, "error": str(exc)},
        ) from exc


def _build_built_in_tool(config: ToolConfig) -> BaseTool:
    """Resolve SDK-bundled utility tools by name."""
    built_ins: dict[str, BaseTool] = {
        "web_search": _web_search_tool(),
        "calculator": _calculator_tool(),
        "text_summarizer": _text_summarizer_tool(),
    }

    name = config.connection_string
    if name not in built_ins:
        raise ToolResolutionError(
            f"Built-in tool '{name}' not found. Available: {list(built_ins.keys())}",
            detail={"tool_id": config.tool_id, "connection_string": name},
        )
    return built_ins[name]


# ── SDK built-in tool implementations ────────────────────────────────────────


def _web_search_tool() -> BaseTool:
    @tool
    def web_search(query: str) -> str:
        """Search the web for information about the given query."""
        return f"[Mock Web Search] Results for: '{query}' — (Replace with real search API)"

    return web_search


def _calculator_tool() -> BaseTool:
    @tool
    def calculator(expression: str) -> str:
        """Evaluate a mathematical expression and return the result."""
        try:
            # Safe eval limited to math operations
            import math
            safe_globals = {"__builtins__": {}, "math": math}
            result = eval(expression, safe_globals)  # noqa: S307
            return str(result)
        except Exception as exc:
            return f"[Calculator Error] {exc}"

    return calculator


def _text_summarizer_tool() -> BaseTool:
    @tool
    def text_summarizer(text: str) -> str:
        """Summarize a long text into a concise paragraph."""
        word_count = len(text.split())
        return f"[Mock Summary] Text has {word_count} words. (Replace with real summarizer)"

    return text_summarizer

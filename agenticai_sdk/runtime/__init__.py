"""Runtime sub-package — LLM factory, tool registry, context engine, and orchestrator."""

from agenticai_sdk.runtime.llm_factory import LLMClientFactory
from agenticai_sdk.runtime.tool_registry import ToolRegistry
from agenticai_sdk.runtime.context_engine import ContextEngine


def __getattr__(name: str):
    """Lazy-load Orchestrator to avoid circular imports with orchestration sub-package."""
    if name == "Orchestrator":
        from agenticai_sdk.runtime.orchestrator import Orchestrator
        return Orchestrator
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "LLMClientFactory",
    "ToolRegistry",
    "ContextEngine",
    "Orchestrator",
]


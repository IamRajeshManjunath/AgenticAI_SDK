"""Runtime sub-package — LLM factory, tool registry, context engine, orchestrator, and registries."""

from agenticai_sdk.runtime.llm_factory import LLMClientFactory
from agenticai_sdk.runtime.tool_registry import ToolRegistry
from agenticai_sdk.runtime.context_engine import ContextEngine
from agenticai_sdk.runtime.integration_registry import IntegrationRegistry
from agenticai_sdk.middleware.registry import MiddlewareRegistry, MiddlewarePipelineBuilder, create_default_pipeline
from agenticai_sdk.runtime.sandbox_registry import SandboxRegistry
from agenticai_sdk.runtime.backend_registry import BackendRegistry, BackendType


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
    "IntegrationRegistry",
    "MiddlewareRegistry",
    "MiddlewarePipelineBuilder",
    "create_default_pipeline",
    "SandboxRegistry",
    "BackendRegistry",
    "BackendType",
    "Orchestrator",
]
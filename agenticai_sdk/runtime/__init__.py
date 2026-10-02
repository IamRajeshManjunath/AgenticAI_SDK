"""Runtime sub-package — LLM factory, tool registry, context engine, orchestrator, and registries."""

"""Runtime sub-package — LLM factory, tool registry, context engine, orchestrator, and registries."""

from agenticai_sdk.runtime.llm_factory import LLMClientFactory
from agenticai_sdk.runtime.tool_registry import ToolRegistry
from agenticai_sdk.runtime.context_engine import ContextEngine
from agenticai_sdk.runtime.integration_registry import IntegrationRegistry
from agenticai_sdk.middleware.registry import MiddlewareRegistry, MiddlewarePipelineBuilder, create_default_pipeline
from agenticai_sdk.runtime.sandbox_registry import SandboxRegistry
from agenticai_sdk.runtime.backend_registry import BackendRegistry, BackendType
from agenticai_sdk.runtime.postgres_checkpointer import PostgresCheckpointer


def __getattr__(name: str):
    """Lazy-load to avoid circular imports."""
    if name == "Orchestrator":
        from agenticai_sdk.runtime.orchestrator import Orchestrator
        return Orchestrator
    if name == "RunManager":
        from agenticai_sdk.runtime.run_manager import RunManager
        return RunManager
    if name == "ModelRegistry":
        from agenticai_sdk.runtime.model_registry import ModelRegistry
        return ModelRegistry
    if name == "FallbackRouter":
        from agenticai_sdk.runtime.model_registry import FallbackRouter
        return FallbackRouter
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
    "PostgresCheckpointer",
    "RunManager",
    "ModelRegistry",
    "FallbackRouter",
]
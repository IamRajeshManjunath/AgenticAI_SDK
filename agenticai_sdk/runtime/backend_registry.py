"""Backend registry for Deep Agents."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agenticai_sdk.plugins import get_global_registry, IntegrationType

import structlog

logger = structlog.get_logger(__name__)


class BackendType(str):
    """Types of Deep Agents backends."""
    STATE = "state"
    FILESYSTEM = "filesystem"
    STORE = "store"
    CONTEXT_HUB = "contexthub"
    SANDBOX = "sandbox"
    LOCAL_SHELL = "localshell"
    COMPOSITE = "composite"


class BackendRegistry:
    """Registry for Deep Agents backend providers."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
    
    def create_backend(self, config: Dict[str, Any]) -> Any:
        """Create backend instance from config."""
        backend_type = config.get("backend_type")
        if not backend_type:
            raise ValueError("Backend config must include 'backend_type'")
        
        plugin = self._registry.get_plugin(IntegrationType.BACKEND, backend_type)
        if not plugin:
            raise ValueError(f"No backend plugin for type: {backend_type}")
        
        return plugin.create_instance(config)
    
    def create_composite(self, routes: Dict[str, str]) -> Any:
        """Create composite backend with routing."""
        # This would create a composite backend that routes to different backends
        # based on path patterns
        raise NotImplementedError("Composite backend not yet implemented")
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available backend types."""
        return [
            {
                "type": BackendType.STATE,
                "name": "State Backend",
                "description": "Thread-scoped state storage via LangGraph checkpointer",
            },
            {
                "type": BackendType.FILESYSTEM,
                "name": "Filesystem Backend",
                "description": "Local filesystem persistence",
            },
            {
                "type": BackendType.STORE,
                "name": "Store Backend",
                "description": "Long-term memory via LangGraph store",
            },
            {
                "type": BackendType.CONTEXT_HUB,
                "name": "Context Hub Backend",
                "description": "LangSmith Hub backed storage",
            },
            {
                "type": BackendType.SANDBOX,
                "name": "Sandbox Backend",
                "description": "Code execution sandbox with filesystem",
            },
            {
                "type": BackendType.LOCAL_SHELL,
                "name": "Local Shell Backend",
                "description": "Direct host filesystem and shell access",
            },
            {
                "type": BackendType.COMPOSITE,
                "name": "Composite Backend",
                "description": "Routes different paths to different backends",
            },
        ]
    
    def get_default_backend(self) -> str:
        """Get default backend type."""
        return BackendType.STATE
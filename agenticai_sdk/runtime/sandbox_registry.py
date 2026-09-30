"""Sandbox registry for AgenticAI SDK."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agenticai_sdk.plugins import get_global_registry, IntegrationType

import structlog

logger = structlog.get_logger(__name__)


class SandboxRegistry:
    """Registry for sandbox providers."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
    
    def create_sandbox(self, config: Dict[str, Any]) -> Any:
        """Create sandbox instance from config."""
        provider = config.get("provider")
        if not provider:
            raise ValueError("Sandbox config must include 'provider'")
        
        plugin = self._registry.get_plugin(IntegrationType.SANDBOX, provider)
        if not plugin:
            raise ValueError(f"No sandbox plugin for provider: {provider}")
        
        return plugin.create_instance(config)
    
    def create_from_config(self, sandbox_config) -> Any:
        """Create from SandboxConfig object."""
        config_dict = sandbox_config.model_dump()
        return self.create_sandbox(config_dict)
    
    def create_multiple(self, sandbox_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create multiple sandboxes, return dict by name/id."""
        sandboxes = {}
        for config in config_dict:
            if config.get("enabled", True):
                sandbox = self.create_sandbox(config)
                sandbox_id = config.get("id", config.get("provider"))
                sandboxes[sandbox_id] = sandbox
        return sandboxes
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available sandbox providers."""
        plugins = self._registry.list_available(IntegrationType.SANDBOX)
        return [
            {
                "provider": p.provider,
                "name": p.name,
                "description": p.description,
                "package": p.package_name,
                "version": p.version,
                "downloads_per_month": p.downloads_per_month,
            }
            for p in plugins
        ]
    
    def health_check(self, provider: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run health check for sandbox provider."""
        plugin = self._registry.get_plugin(IntegrationType.SANDBOX, provider)
        if not plugin:
            return {"healthy": False, "message": f"No sandbox plugin for provider: {provider}"}
        
        return plugin.health_check(config)
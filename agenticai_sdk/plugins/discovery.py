"""Plugin discovery for AgenticAI SDK.

Discovers plugins from entry points and installed packages.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
from typing import List, Optional

import structlog

from .base import IntegrationType, PluginMetadata, FeatureFlags
from .registry import IntegrationRegistry, get_global_registry

logger = structlog.get_logger(__name__)


def discover_plugins(registry: Optional[IntegrationRegistry] = None) -> List[PluginMetadata]:
    """Discover all available plugins from entry points and installed packages."""
    if registry is None:
        registry = get_global_registry()
    
    # Load entry points
    registry.load_entry_points()
    
    # Discover installed packages
    discovered = registry.discover_installed_packages()
    
    # Register discovered
    for metadata in discovered:
        registry.register_metadata(metadata)
    
    logger.info("plugins_discovered", count=len(discovered))
    return discovered


def register_plugin_from_entry_point(entry_point_name: str) -> Optional[PluginMetadata]:
    """Register a specific plugin from entry point by name."""
    try:
        eps = importlib.metadata.entry_points(group="agenticai.plugins")
        for ep in eps:
            if ep.name == entry_point_name:
                metadata = ep.load()
                if isinstance(metadata, PluginMetadata):
                    registry = get_global_registry()
                    registry.register_metadata(metadata)
                    return metadata
    except Exception as e:
        logger.error("entry_point_register_failed", entry_point=entry_point_name, error=str(e))
    return None


def get_plugin_info(type: IntegrationType, provider: str) -> Optional[PluginMetadata]:
    """Get plugin metadata by type and provider."""
    registry = get_global_registry()
    return registry.get_metadata(type, provider)


def list_plugins(type: Optional[IntegrationType] = None) -> List[PluginMetadata]:
    """List all available plugins."""
    registry = get_global_registry()
    return registry.list_available(type)


def create_integration(
    type: IntegrationType,
    provider: str,
    config: dict,
    registry: Optional[IntegrationRegistry] = None,
) -> Any:
    """Create integration instance."""
    if registry is None:
        registry = get_global_registry()
    return registry.create_instance(type, provider, config)


def health_check_integration(
    type: IntegrationType,
    provider: str,
    config: dict,
    registry: Optional[IntegrationRegistry] = None,
) -> Any:
    """Run health check for integration."""
    if registry is None:
        registry = get_global_registry()
    return registry.health_check(type, provider, config)
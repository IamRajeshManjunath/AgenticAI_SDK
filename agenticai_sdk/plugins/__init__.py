"""Plugin registry for AgenticAI SDK.

Provides dynamic discovery and registration of integration plugins.
Supports entry point auto-discovery and explicit YAML registration.
"""

from .registry import IntegrationRegistry, IntegrationPlugin, get_global_registry
from .base import IntegrationType, PluginMetadata, FeatureFlags
from .discovery import discover_plugins, register_plugin_from_entry_point

__all__ = [
    "IntegrationRegistry",
    "IntegrationPlugin",
    "get_global_registry",
    "IntegrationType",
    "PluginMetadata",
    "FeatureFlags",
    "discover_plugins",
    "register_plugin_from_entry_point",
]
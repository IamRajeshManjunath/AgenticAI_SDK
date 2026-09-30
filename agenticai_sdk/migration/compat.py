"""Compatibility layer for AgenticAI SDK.

Provides backward-compatible interfaces for legacy code.
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List, Optional, Union

from .legacy import LegacyConfigMigrator, migrate_legacy_config, MigrationReport
from ..config.schemas import AgenticAIConfig, ChatModelConfig, DatabaseRouteConfig, LLMConfig
from ..config.loader import load_config as load_config_v03


class CompatLayer:
    """Compatibility layer for legacy AgenticAI APIs."""
    
    def __init__(self, config: Optional[AgenticAIConfig] = None):
        self._config = config
        self._migrator = LegacyConfigMigrator()
    
    @property
    def config(self) -> AgenticAIConfig:
        if self._config is None:
            self._config = load_config_v03()
        return self._config
    
    # Legacy LLMConfig compatibility
    def get_llm_config(self, name: str = "primary") -> LLMConfig:
        """Get legacy LLMConfig for backward compatibility."""
        warnings.warn(
            "get_llm_config is deprecated. Use config.chat_models instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        chat_model = self.config.chat_models.get(name)
        if not chat_model:
            raise KeyError(f"Chat model '{name}' not found")
        
        return LLMConfig(
            provider=chat_model.provider,
            model=chat_model.model,
            api_key_env=chat_model.api_key_env,
            temperature=chat_model.temperature,
            max_tokens=chat_model.max_tokens,
        )
    
    def get_all_llm_configs(self) -> Dict[str, LLMConfig]:
        """Get all legacy LLMConfigs."""
        warnings.warn(
            "get_all_llm_configs is deprecated. Use config.chat_models instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        return {
            name: self.get_llm_config(name)
            for name in self.config.chat_models
        }
    
    # Legacy database compatibility
    def get_database_config(self, name: str = "primary") -> DatabaseRouteConfig:
        """Get database route config (v0.3 native)."""
        route = self.config.database_routes.get(name)
        if not route:
            raise KeyError(f"Database route '{name}' not found")
        return route
    
    def get_vector_store_config(self) -> DatabaseRouteConfig:
        """Get vector store config (legacy alias)."""
        warnings.warn(
            "get_vector_store_config is deprecated. Use get_database_config with purpose=vector_store.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        for route in self.config.database_routes.values():
            if route.purpose.value == "vector_store":
                return route
        raise KeyError("No vector store route configured")
    
    def get_checkpointer_config(self) -> DatabaseRouteConfig:
        """Get checkpointer config (legacy alias)."""
        warnings.warn(
            "get_checkpointer_config is deprecated. Use get_database_config with purpose=checkpointer.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        for route in self.config.database_routes.values():
            if route.purpose.value == "checkpointer":
                return route
        raise KeyError("No checkpointer route configured")
    
    def get_store_config(self) -> DatabaseRouteConfig:
        """Get store config (legacy alias)."""
        warnings.warn(
            "get_store_config is deprecated. Use get_database_config with purpose=store.",
            DeprecationWarning,
            stacklevel=2,
        )
        
        for route in self.config.database_routes.values():
            if route.purpose.value == "store":
                return route
        raise KeyError("No store route configured")
    
    # Legacy tool compatibility
    def get_tool_config(self, name: str) -> Dict[str, Any]:
        """Get tool configuration."""
        return self.config.tools.get(name, {})
    
    def get_enabled_tools(self) -> List[str]:
        """Get list of enabled tools."""
        return list(self.config.tools.keys())
    
    # Legacy feature flags
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled."""
        return self.config.features.get(feature, False)
    
    # Config loading with migration
    @classmethod
    def load_config(cls, path: Optional[str] = None, **overrides) -> "CompatLayer":
        """Load config with automatic legacy migration."""
        if path:
            migrator = LegacyConfigMigrator()
            config = migrator.migrate_file(path)
        else:
            config = load_config_v03(**overrides)
        
        return cls(config)
    
    def migrate_and_save(self, output_path: str) -> MigrationReport:
        """Migrate current config and save as v0.3 format."""
        # This would be used to upgrade legacy config files
        pass


_compat_layer: Optional[CompatLayer] = None


def get_compat_layer(config: Optional[AgenticAIConfig] = None) -> CompatLayer:
    """Get global compatibility layer instance."""
    global _compat_layer
    if _compat_layer is None:
        _compat_layer = CompatLayer(config)
    return _compat_layer


def set_compat_layer(layer: CompatLayer) -> None:
    """Set global compatibility layer instance."""
    global _compat_layer
    _compat_layer = layer


# Legacy function aliases for backward compatibility
def load_llm_config(name: str = "primary") -> LLMConfig:
    """Legacy function to load LLM config."""
    return get_compat_layer().get_llm_config(name)


def load_database_config(name: str = "primary") -> DatabaseRouteConfig:
    """Legacy function to load database config."""
    return get_compat_layer().get_database_config(name)
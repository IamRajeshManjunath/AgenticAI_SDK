"""Configuration loader for AgenticAI SDK.

Loads YAML static defaults, merges with JSON runtime overrides,
supports environment variable interpolation.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import ValidationError

from .schemas import AgenticAIConfig, IntegrationsConfig, PluginMetadata, IntegrationType


# Environment variable pattern: ${VAR_NAME} or ${VAR_NAME:-default}
ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::-([^}]*))?\}')


def interpolate_env_vars(value: Any) -> Any:
    """Recursively interpolate environment variables in config values."""
    if isinstance(value, str):
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1)
            default = match.group(2)
            env_value = os.getenv(var_name)
            if env_value is not None:
                return env_value
            if default is not None:
                return default
            return match.group(0)  # Keep original if not found and no default
        
        return ENV_VAR_PATTERN.sub(replace_var, value)
    
    elif isinstance(value, dict):
        return {k: interpolate_env_vars(v) for k, v in value.items()}
    
    elif isinstance(value, list):
        return [interpolate_env_vars(item) for item in value]
    
    return value


def load_yaml_config(path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse YAML config file with env var interpolation."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, "r") as f:
        raw_config = yaml.safe_load(f) or {}
    
    return interpolate_env_vars(raw_config)


def merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two configuration dictionaries.
    
    Override takes precedence. Lists are merged by 'id' field for known keys.
    """
    # Keys where lists should be merged by 'id' instead of replaced
    MERGE_BY_ID_KEYS = {
        "chat_models", "tools", "middleware", "sandboxes", "backends", 
        "skills", "plugins", "document_loaders"
    }
    
    result = base.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        elif key in result and isinstance(result[key], list) and isinstance(value, list) and key in MERGE_BY_ID_KEYS:
            # Merge lists by 'id' field
            result[key] = _merge_lists_by_id(result[key], value)
        else:
            result[key] = value
    
    return result


def _merge_lists_by_id(base_list: List[Dict[str, Any]], override_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge two lists of objects by 'id' field.
    
    Objects with matching 'id' are deep merged.
    Objects only in override are added.
    Objects only in base are kept.
    """
    # Build dict by id for easy lookup
    base_by_id = {item.get("id"): item for item in base_list if item.get("id")}
    override_by_id = {item.get("id"): item for item in override_list if item.get("id")}
    
    # Start with base items
    result = list(base_list)
    
    # Process override items
    for override_id, override_item in override_by_id.items():
        if override_id in base_by_id:
            # Merge with existing
            base_item = base_by_id[override_id]
            merged = merge_configs(base_item, override_item)
            # Replace in result
            for i, item in enumerate(result):
                if item.get("id") == override_id:
                    result[i] = merged
                    break
        else:
            # New item
            result.append(override_item)
    
    return result


class ConfigLoader:
    """Loads and validates AgenticAI configuration."""
    
    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        env_prefix: str = "AGENTICAI_",
    ):
        self.config_path = Path(config_path) if config_path else None
        self.env_prefix = env_prefix
        self._config: Optional[AgenticAIConfig] = None
    
    def find_config_file(self) -> Optional[Path]:
        """Find config file in standard locations."""
        search_paths = [
            self.config_path,
            Path.cwd() / "agenticai.yaml",
            Path.cwd() / "agenticai.yml",
            Path.cwd() / "config" / "agenticai.yaml",
            Path("/etc/agenticai") / "agenticai.yaml",
            Path.home() / ".agenticai" / "agenticai.yaml",
        ]
        
        for path in search_paths:
            if path and path.exists():
                return path
        
        return None
    
    def load_static_config(self) -> Dict[str, Any]:
        """Load static configuration from YAML file."""
        config_path = self.find_config_file()
        if not config_path:
            return self._get_default_config()
        
        return load_yaml_config(config_path)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return minimal default configuration."""
        return {
            "platform": {
                "name": "agenticai",
                "environment": "development",
                "database_url": "sqlite:///agenticai.db",
            },
            "integrations": {
                "chat_models": [
                    {
                        "id": "default-openai",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "config": {"api_key_env": "OPENAI_API_KEY"},
                        "features": {"stream": True, "tools": True, "structured_output": True, "multimodal": True},
                        "priority": 1,
                    }
                ],
                "tools": [],
                "middleware": [
                    {"type": "rate_limiter", "id": "rate-limit", "config": {"requests_per_minute": 60}},
                    {"type": "pii_masking", "id": "pii-mask"},
                    {"type": "prompt_injection_firewall", "id": "firewall"},
                    {"type": "schema_validation", "id": "schema-validation"},
                ],
                "persistence": {},
                "sandboxes": [],
                "backends": [],
                "skills": [],
            }
        }
    
    def load(self, runtime_overrides: Optional[Dict[str, Any]] = None) -> AgenticAIConfig:
        """Load complete configuration with validation."""
        # Load static config
        static_config = self.load_static_config()
        
        # Merge runtime overrides
        if runtime_overrides:
            static_config = merge_configs(static_config, runtime_overrides)
        
        # Validate and create config object
        try:
            config = AgenticAIConfig(**static_config)
        except ValidationError as e:
            raise ValueError(f"Configuration validation failed: {e}")
        
        # Apply runtime overrides to config object
        if runtime_overrides:
            config = config.apply_runtime_overrides(runtime_overrides)
        
        self._config = config
        return config
    
    def get_config(self) -> AgenticAIConfig:
        """Get loaded config (must call load() first)."""
        if self._config is None:
            return self.load()
        return self._config
    
    def reload(self, runtime_overrides: Optional[Dict[str, Any]] = None) -> AgenticAIConfig:
        """Reload configuration from file."""
        self._config = None
        return self.load(runtime_overrides)


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    runtime_overrides: Optional[Dict[str, Any]] = None,
) -> AgenticAIConfig:
    """Convenience function to load configuration."""
    loader = ConfigLoader(config_path)
    return loader.load(runtime_overrides)


def get_config_loader() -> ConfigLoader:
    """Get global config loader instance."""
    return ConfigLoader()
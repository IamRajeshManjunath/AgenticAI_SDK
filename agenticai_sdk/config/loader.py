"""Configuration loader for AgenticAI SDK.

Loads JSON static defaults (agenticai.json), merges with JSON runtime overrides,
supports environment variable interpolation.
JSON Schema validation is the first validation gate per v0.3.0 spec.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

import jsonschema
import structlog
from pydantic import ValidationError

from .schemas import AgenticAIConfig, IntegrationsConfig, PluginMetadata, IntegrationType

logger = structlog.get_logger(__name__)

# Environment variable pattern: ${VAR_NAME} or ${VAR_NAME:-default}
ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::-([^}]*))?\}')

# Default schema path
DEFAULT_SCHEMA_PATH = Path(__file__).parent.parent.parent / "schemas" / "agenticai.schema.json"


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


def load_json_config(path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse JSON config file with env var interpolation."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")
    
    with open(path, "r") as f:
        raw_config = json.load(f)
    
    return interpolate_env_vars(raw_config)


def validate_json_schema(config: Dict[str, Any], schema_path: Optional[Path] = None) -> List[str]:
    """Validate configuration against JSON Schema.
    
    Returns list of error messages (empty if valid).
    """
    schema_path = schema_path or DEFAULT_SCHEMA_PATH
    if not schema_path.exists():
        logger.warning("json_schema_not_found", path=str(schema_path))
        return []
    
    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
    except Exception as e:
        logger.error("json_schema_load_failed", error=str(e))
        return [f"Failed to load JSON schema: {e}"]
    
    try:
        jsonschema.validate(instance=config, schema=schema)
        return []
    except jsonschema.ValidationError as e:
        return [f"JSON Schema validation failed at {' -> '.join(str(p) for p in e.path)}: {e.message}"]
    except Exception as e:
        logger.error("json_schema_validation_error", error=str(e))
        return [f"JSON Schema validation error: {e}"]


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
    """Loads and validates AgenticAI configuration with JSON Schema as first gate."""
    
    def __init__(
        self,
        config_path: Optional[Union[str, Path]] = None,
        env_prefix: str = "AGENTICAI_",
        schema_path: Optional[Union[str, Path]] = None,
    ):
        self.config_path = Path(config_path) if config_path else None
        self.env_prefix = env_prefix
        self.schema_path = Path(schema_path) if schema_path else DEFAULT_SCHEMA_PATH
        self._config: Optional[AgenticAIConfig] = None
        self._change_callbacks: List[Callable[[AgenticAIConfig], Any]] = []
        self._reload_event = asyncio.Event()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._watch_task: Optional[asyncio.Task] = None
    
    def find_config_file(self) -> Optional[Path]:
        """Find config file in standard locations (JSON only)."""
        search_paths = [
            self.config_path,
            Path.cwd() / "agenticai.json",
            Path.cwd() / "config" / "agenticai.json",
            Path("/etc/agenticai") / "agenticai.json",
            Path.home() / ".agenticai" / "agenticai.json",
        ]
        
        for path in search_paths:
            if path and path.exists():
                return path
        
        return None
    
    def load_static_config(self) -> Dict[str, Any]:
        """Load static configuration from JSON file with JSON Schema validation."""
        config_path = self.find_config_file()
        if not config_path:
            logger.info("config_file_not_found_using_defaults")
            return self._get_default_config()
        
        # Load and parse JSON
        raw_config = load_json_config(config_path)
        
        # JSON Schema validation (first gate)
        schema_errors = validate_json_schema(raw_config, self.schema_path)
        if schema_errors:
            raise ValueError(f"JSON Schema validation failed: {'; '.join(schema_errors)}")
        
        logger.info("config_loaded_and_validated", path=str(config_path))
        return raw_config
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return minimal default configuration matching agenticai.json structure."""
        return {
            "apiVersion": "agenticai/v1",
            "kind": "Workflow",
            "metadata": {
                "name": "default-workflow",
                "version": "1.0.0"
            },
            "platform": {
                "name": "agenticai",
                "environment": "development",
                "version": "0.3.0"
            },
            "integrations": {
                "chat_models": {
                    "primary": {
                        "provider": "openai",
                        "model": "gpt-4o",
                        "parameters": {
                            "temperature": 0.1,
                            "maxTokens": 4096
                        }
                    },
                    "fallback": {
                        "provider": "anthropic",
                        "model": "claude-3-5-sonnet-latest",
                        "parameters": {
                            "temperature": 0.1,
                            "maxTokens": 4096
                        }
                    }
                },
                "nodes": [
                    {
                        "id": "default-agent",
                        "type": "llm",
                        "model": "primary",
                        "prompt": "You are a helpful assistant. {input}",
                        "parameters": {"input": "{input}"}
                    }
                ],
                "edges": [
                    {"from": "default-agent", "to": "__end__"}
                ],
                "policies": {
                    "budget": {
                        "maxIterations": 100,
                        "maxInputTokens": 100000,
                        "maxOutputTokens": 50000,
                        "maxCostUsd": 10.0,
                        "maxWallTimeSeconds": 3600
                    },
                    "hitl": {"enabled": false},
                    "pii": {"enabled": true, "action": "tokenize", "restoreAtBoundaries": true},
                    "injection": {"enabled": true, "mode": "block"},
                    "compression": {"enabled": true, "strategy": "progressive", "maxContextTokens": 8192},
                    "consensus": {"enabled": true, "strategy": "majority", "instances": 3, "threshold": 0.7}
                },
                "variables": {}
            }
        }
    
    async def initialize(self):
        """Initialize the config loader with file watching."""
        self._loop = asyncio.get_running_loop()
        self._start_watching()
        logger.info("config_loader_initialized", 
                   config_path=str(self.config_path) if self.config_path else "auto-detect",
                   schema_path=str(self.schema_path))
    
    def _start_watching(self):
        """Start file system watcher for config file changes."""
        config_path = self.find_config_file()
        if not config_path:
            return
        
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
            
            class ConfigChangeHandler(FileSystemEventHandler):
                def __init__(self, loader):
                    self.loader = loader
                    self._debounce_timer = None
                    self._lock = asyncio.Lock() if hasattr(asyncio, 'Lock') else None
                
                def on_modified(self, event):
                    if event.is_directory:
                        return
                    path = Path(event.src_path)
                    if path.resolve() == config_path.resolve():
                        if self._debounce_timer:
                            self._debounce_timer.cancel()
                        self._debounce_timer = asyncio.get_event_loop().call_later(0.5, self._trigger_reload)
                
                def _trigger_reload(self):
                    if self.loader._loop and not self.loader._loop.is_closed():
                        asyncio.run_coroutine_threadsafe(self.loader._notify_change(), self.loader._loop)
            
            self._handler = ConfigChangeHandler(self)
            self._observer = Observer()
            self._observer.schedule(self._handler, str(config_path.parent), recursive=False)
            self._observer.start()
            logger.info("config_file_watcher_started", path=str(config_path))
        except ImportError:
            logger.warning("watchdog_not_installed_file_watching_disabled")
        except Exception as e:
            logger.warning("config_file_watcher_failed", error=str(e))
    
    def stop_watching(self):
        """Stop file system watcher."""
        if hasattr(self, '_observer') and self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            self._observer = None
            logger.info("config_file_watcher_stopped")
        
        if self._watch_task:
            self._watch_task.cancel()
            self._watch_task = None
    
    def on_change(self, callback: Callable[[AgenticAIConfig], Any]):
        """Register a callback to be called when config changes."""
        self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[AgenticAIConfig], Any]):
        """Remove a change callback."""
        if callback in self._change_callbacks:
            self._change_callbacks.remove(callback)
    
    async def _notify_change(self):
        """Notify all callbacks of config change."""
        new_config = self.load()
        
        for cb in self._change_callbacks:
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(new_config)
                else:
                    cb(new_config)
            except Exception as e:
                logger.error("config_change_callback_failed", error=str(e))
        
        self._reload_event.set()
        self._reload_event.clear()
        
        logger.info("config_reloaded_and_notified")
    
    def load(self, runtime_overrides: Optional[Dict[str, Any]] = None) -> AgenticAIConfig:
        """Load complete configuration with validation."""
        # Load static config (includes JSON Schema validation)
        static_config = self.load_static_config()
        
        # Merge runtime overrides
        if runtime_overrides:
            static_config = merge_configs(static_config, runtime_overrides)
        
        # Validate and create config object (Pydantic validation - second gate)
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
        """Reload configuration from file (synchronous)."""
        self._config = None
        return self.load(runtime_overrides)
    
    async def reload_async(self, runtime_overrides: Optional[Dict[str, Any]] = None) -> AgenticAIConfig:
        """Reload configuration and notify callbacks."""
        self._config = None
        config = self.load(runtime_overrides)
        await self._notify_change()
        return config
    
    async def wait_for_reload(self, timeout: float = 30.0) -> bool:
        """Wait for a config reload event."""
        try:
            await asyncio.wait_for(self._reload_event.wait(), timeout=timeout)
            return True
        except asyncio.TimeoutError:
            return False


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    runtime_overrides: Optional[Dict[str, Any]] = None,
) -> AgenticAIConfig:
    """Convenience function to load configuration."""
    loader = ConfigLoader(config_path)
    return loader.load(runtime_overrides)


async def load_config_async(
    config_path: Optional[Union[str, Path]] = None,
    runtime_overrides: Optional[Dict[str, Any]] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> ConfigLoader:
    """Convenience function to load configuration with async initialization."""
    loader = ConfigLoader(config_path, schema_path=schema_path)
    await loader.initialize()
    return loader


def get_config_loader() -> ConfigLoader:
    """Get global config loader instance."""
    return ConfigLoader()
"""Configuration Manager - Validate-before-write, JSON Merge Patch, atomic writes (JSON-only)."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import ValidationError

from .schemas import AgenticAIConfig
from .loader import validate_json_schema, interpolate_env_vars

logger = structlog.get_logger(__name__)

# fcntl is Unix-only; use msvcrt on Windows for file locking
if sys.platform == "win32":
    import msvcrt
    def lock_file(fileno: int, exclusive: bool = True):
        if exclusive:
            msvcrt.locking(fileno, msvcrt.LK_NBLCK, 1)
        else:
            msvcrt.locking(fileno, msvcrt.LK_UNLCK, 1)
else:
    import fcntl
    def lock_file(fileno: int, exclusive: bool = True):
        if exclusive:
            fcntl.flock(fileno, fcntl.LOCK_EX)
        else:
            fcntl.flock(fileno, fcntl.LOCK_UN)


class ConfigurationManager:
    """Manages configuration file with validation, atomic writes, and JSON Merge Patch support (JSON-only)."""
    
    def __init__(self, target_path: Union[str, Path], schema_path: Optional[Union[str, Path]] = None):
        self.target_path = Path(target_path)
        self.schema_path = Path(schema_path) if schema_path else None
        self._config_cache: Optional[Dict[str, Any]] = None
        self._config_hash: Optional[str] = None
    
    def get_config_path(self) -> Path:
        """Get the resolved config file path."""
        return self.target_path
    
    def load_current(self) -> Dict[str, Any]:
        """Load current configuration from JSON file."""
        if not self.target_path.exists():
            return self._get_default_config()
        
        with open(self.target_path, "r") as f:
            raw_config = json.load(f)
        
        return interpolate_env_vars(raw_config)
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Return minimal default configuration matching agenticai.json structure."""
        return {
            "apiVersion": "agenticai/v1",
            "kind": "Workflow",
            "metadata": {
                "name": "default-workflow",
                "version": "1.0.0"
            },
            "spec": {
                "models": {
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
                    "hitl": {"enabled": False},
                    "pii": {"enabled": True, "action": "tokenize", "restoreAtBoundaries": True},
                    "injection": {"enabled": True, "mode": "block"},
                    "compression": {"enabled": True, "strategy": "progressive", "maxContextTokens": 8192},
                    "consensus": {"enabled": True, "strategy": "majority", "instances": 3, "threshold": 0.7}
                },
                "variables": {}
            }
        }
    
    def _compute_hash(self, config: Dict[str, Any]) -> str:
        """Compute SHA256 hash of config for change detection."""
        config_str = json.dumps(config, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def validate_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate configuration against JSON Schema and Pydantic. Returns list of errors (empty if valid)."""
        errors = []
        
        # JSON Schema validation (first gate)
        if self.schema_path:
            schema_errors = validate_json_schema(config, self.schema_path)
            errors.extend(schema_errors)
        
        # Pydantic validation (second gate)
        try:
            AgenticAIConfig(**config)
        except ValidationError as e:
            for err in e.errors():
                loc = ".".join(str(x) for x in err["loc"])
                errors.append(f"{loc}: {err['msg']}")
        except Exception as e:
            errors.append(f"Validation error: {str(e)}")
        
        return errors
    
    def apply_json_merge_patch(self, current: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        """Apply JSON Merge Patch (RFC 7396) to current config.
        
        - null values in patch delete keys from current
        - objects are merged recursively
        - arrays are replaced (not merged) unless special handling
        """
        result = current.copy()
        
        for key, value in patch.items():
            if value is None:
                # null means delete
                result.pop(key, None)
            elif isinstance(value, dict) and key in result and isinstance(result[key], dict):
                # Recursive merge for objects
                result[key] = self.apply_json_merge_patch(result[key], value)
            else:
                # Replace (including arrays)
                result[key] = value
        
        return result
    
    def apply_merge_with_id_handling(self, current: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
        """Apply merge with special handling for ID-keyed lists."""
        # Keys where lists should be merged by 'id' instead of replaced
        MERGE_BY_ID_KEYS = {
            "chat_models", "tools", "middleware", "sandboxes", "backends", 
            "skills", "plugins", "document_loaders",
            "nodes", "edges", "models", "policies"
        }
        
        result = current.copy()
        
        for key, value in patch.items():
            if value is None:
                result.pop(key, None)
            elif isinstance(value, dict) and key in result and isinstance(result[key], dict):
                result[key] = self.apply_merge_with_id_handling(result[key], value)
            elif isinstance(value, list) and key in result and isinstance(result[key], list) and key in MERGE_BY_ID_KEYS:
                # Merge lists by 'id' field
                result[key] = self._merge_lists_by_id(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _merge_lists_by_id(self, base_list: List[Dict[str, Any]], override_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merge two lists of objects by 'id' field."""
        base_by_id = {item.get("id"): item for item in base_list if item.get("id")}
        override_by_id = {item.get("id"): item for item in override_list if item.get("id")}
        
        result = list(base_list)
        
        for override_id, override_item in override_by_id.items():
            if override_id in base_by_id:
                base_item = base_by_id[override_id]
                merged = self.apply_merge_with_id_handling(base_item, override_item)
                for i, item in enumerate(result):
                    if item.get("id") == override_id:
                        result[i] = merged
                        break
            else:
                result.append(override_item)
        
        return result
    
    def validate_and_save(self, patch: Dict[str, Any], merge_strategy: str = "id_aware") -> Dict[str, Any]:
        """Validate configuration and save atomically.
        
        Args:
            patch: Partial configuration to merge (JSON Merge Patch)
            merge_strategy: "json_merge" (RFC 7396), "id_aware" (merge lists by id), or "replace"
        
        Returns:
            Updated configuration dict
        
        Raises:
            ValueError: If validation fails
        """
        current = self.load_current()
        
        # Apply merge based on strategy
        if merge_strategy == "json_merge":
            updated = self.apply_json_merge_patch(current, patch)
        elif merge_strategy == "id_aware":
            updated = self.apply_merge_with_id_handling(current, patch)
        elif merge_strategy == "replace":
            updated = {**current, **patch}
        else:
            raise ValueError(f"Unknown merge strategy: {merge_strategy}")
        
        # Validate before write (JSON Schema + Pydantic)
        errors = self.validate_config(updated)
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        # Atomic write with file locking
        self._atomic_write(updated)
        
        # Update cache
        self._config_cache = updated
        self._config_hash = self._compute_hash(updated)
        
        return updated
    
    def _atomic_write(self, config: Dict[str, Any]):
        """Write config atomically using temp file + rename with file locking."""
        # Ensure parent directory exists
        self.target_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create temp file in same directory for atomic rename
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.target_path.parent,
            prefix=f".{self.target_path.name}.tmp.",
            suffix=".json",
            delete=False
        ) as tmp:
            try:
                # Acquire exclusive lock
                lock_file(tmp.fileno(), exclusive=True)
                
                # Write JSON
                json.dump(config, tmp, indent=2, sort_keys=False)
                tmp.flush()
                os.fsync(tmp.fileno())
                
                # Release lock
                lock_file(tmp.fileno(), exclusive=False)
                
                # Atomic rename
                os.replace(tmp.name, self.target_path)
                
            except Exception:
                # Clean up temp file on error
                try:
                    os.unlink(tmp.name)
                except Exception:
                    pass
                raise
    
    def save_full(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Save full configuration (replaces entire file)."""
        errors = self.validate_config(config)
        if errors:
            raise ValueError(f"Configuration validation failed: {'; '.join(errors)}")
        
        self._atomic_write(config)
        self._config_cache = config
        self._config_hash = self._compute_hash(config)
        return config
    
    def get_config_hash(self) -> Optional[str]:
        """Get hash of current config for change detection."""
        if self._config_hash is None:
            current = self.load_current()
            self._config_hash = self._compute_hash(current)
        return self._config_hash
    
    def has_changed(self) -> bool:
        """Check if file has changed since last load."""
        current_hash = self._compute_hash(self.load_current())
        return current_hash != self._config_hash
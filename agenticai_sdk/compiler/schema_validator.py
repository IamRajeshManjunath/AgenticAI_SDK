"""Schema Validator - JSON Schema + Pydantic validation gates.

Provides two-stage validation:
1. JSON Schema validation (structural)
2. Pydantic validation (semantic + type constraints)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import json
import jsonschema
import structlog
from pydantic import ValidationError

from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.schemas.workflow import WorkflowSchema

logger = structlog.get_logger(__name__)


class SchemaValidationError(Exception):
    """Raised when schema validation fails."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Schema validation failed: {'; '.join(errors)}")


class SchemaValidator:
    """Two-stage schema validator for AgenticAI configuration."""
    
    def __init__(self, schema_path: Optional[Union[str, Path]] = None):
        self.schema_path = Path(schema_path) if schema_path else None
        self._schema_cache: Optional[Dict[str, Any]] = None
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load and cache JSON Schema."""
        if self._schema_cache is not None:
            return self._schema_cache
        
        if not self.schema_path or not self.schema_path.exists():
            logger.warning("json_schema_not_found", path=str(self.schema_path))
            return {}
        
        try:
            with open(self.schema_path, "r") as f:
                self._schema_cache = json.load(f)
            return self._schema_cache
        except Exception as e:
            logger.error("json_schema_load_failed", error=str(e))
            return {}
    
    def validate_json_schema(self, config: Dict[str, Any]) -> List[str]:
        """Validate against JSON Schema (first gate).
        
        Returns list of error messages (empty if valid).
        """
        schema = self._load_schema()
        if not schema:
            logger.warning("json_schema_not_available_skipping")
            return []
        
        try:
            jsonschema.validate(instance=config, schema=schema)
            return []
        except jsonschema.ValidationError as e:
            path = " -> ".join(str(p) for p in e.path)
            return [f"JSON Schema validation failed at {path}: {e.message}"]
        except Exception as e:
            logger.error("json_schema_validation_error", error=str(e))
            return [f"JSON Schema validation error: {e}"]
    
    def validate_pydantic(self, config: Dict[str, Any]) -> List[str]:
        """Validate against Pydantic models (second gate).
        
        Returns list of error messages (empty if valid).
        """
        errors = []
        
        try:
            from agenticai_sdk.config.schemas import AgenticAIConfig
            AgenticAIConfig(**config)
        except ValidationError as e:
            for err in e.errors():
                loc = " -> ".join(str(x) for x in err["loc"])
                errors.append(f"{loc}: {err['msg']}")
        except Exception as e:
            errors.append(f"Pydantic validation error: {e}")
        
        return errors
    
    def validate_workflow_schema(self, workflow: Dict[str, Any]) -> List[str]:
        """Validate workflow schema specifically."""
        errors = []
        
        try:
            from agenticai_sdk.schemas.workflow import WorkflowSchema
            WorkflowSchema(**workflow)
        except ValidationError as e:
            for err in e.errors():
                loc = " -> ".join(str(x) for x in err["loc"])
                errors.append(f"{loc}: {err['msg']}")
        except Exception as e:
            errors.append(f"Workflow schema validation error: {e}")
        
        return errors
    
    def validate_all(self, config: Dict[str, Any]) -> List[str]:
        """Run all validation gates."""
        all_errors = []
        
        # Gate 1: JSON Schema
        schema_errors = self.validate_json_schema(config)
        all_errors.extend(schema_errors)
        
        # Gate 2: Pydantic
        if not schema_errors:  # Only run Pydantic if JSON Schema passes
            pydantic_errors = self.validate_pydantic(config)
            all_errors.extend(pydantic_errors)
        
        return all_errors
    
    def validate_and_raise(self, config: Dict[str, Any]) -> None:
        """Validate and raise exception if any errors."""
        errors = self.validate_all(config)
        if errors:
            raise SchemaValidationError(errors)


def validate_json_schema(config: Dict[str, Any], schema_path: Optional[Union[str, Path]] = None) -> List[str]:
    """Convenience function for JSON Schema validation."""
    validator = SchemaValidator(schema_path)
    return validator.validate_json_schema(config)


def validate_pydantic(config: Dict[str, Any]) -> List[str]:
    """Convenience function for Pydantic validation."""
    validator = SchemaValidator()
    return validator.validate_pydantic(config)


def validate_all(config: Dict[str, Any], schema_path: Optional[Union[str, Path]] = None) -> List[str]:
    """Convenience function for all validation gates."""
    validator = SchemaValidator(schema_path)
    return validator.validate_all(config)
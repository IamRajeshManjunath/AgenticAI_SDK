"""Parser - Converts JSON configuration to Pydantic models.

First stage of the compiler pipeline: validates JSON structure and converts
to canonical Pydantic models for type-safe downstream processing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union

import structlog
from pydantic import ValidationError

from agenticai_sdk.config.loader import load_json_config, validate_json_schema
from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.schemas.workflow import WorkflowSchema

logger = structlog.get_logger(__name__)


class ParseError(Exception):
    """Raised when JSON parsing fails."""
    pass


class ValidationError(Exception):
    """Raised when schema validation fails."""
    pass


def parse_config_file(path: Union[str, Path]) -> Dict[str, Any]:
    """Load and parse JSON config file."""
    return load_json_config(path)


def parse_config_dict(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate config dict structure."""
    return config


def parse_to_pydantic(config: Dict[str, Any]) -> AgenticAIConfig:
    """Convert validated config dict to Pydantic model (second validation gate)."""
    try:
        return AgenticAIConfig(**config)
    except ValidationError as e:
        raise ValidationError(f"Pydantic validation failed: {e}")


def parse_workflow_schema(config: Dict[str, Any]) -> WorkflowSchema:
    """Extract and validate workflow schema from config."""
    try:
        return WorkflowSchema(**config)
    except ValidationError as e:
        raise ValidationError(f"Workflow schema validation failed: {e}")


def load_and_validate(
    path: Optional[Union[str, Path]] = None,
    config_dict: Optional[Dict[str, Any]] = None,
    schema_path: Optional[Union[str, Path]] = None,
) -> AgenticAIConfig:
    """Load config from file or dict, validate through both gates.
    
    Args:
        path: Path to JSON config file
        config_dict: Pre-loaded config dict
        schema_path: Path to JSON Schema file
    
    Returns:
        Validated AgenticAIConfig
    
    Raises:
        ParseError: If file not found or invalid JSON
        ValidationError: If schema or Pydantic validation fails
    """
    if config_dict is not None:
        raw_config = config_dict
    elif path is not None:
        raw_config = load_json_config(path)
    else:
        raise ParseError("Either path or config_dict must be provided")
    
    # Gate 1: JSON Schema validation
    schema_errors = validate_json_schema(raw_config, schema_path)
    if schema_errors:
        raise ValidationError(f"JSON Schema validation failed: {'; '.join(schema_errors)}")
    
    # Gate 2: Pydantic validation
    try:
        config = AgenticAIConfig(**raw_config)
    except ValidationError as e:
        raise ValidationError(f"Pydantic validation failed: {e}")
    
    return config
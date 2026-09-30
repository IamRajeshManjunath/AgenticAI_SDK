"""Configuration system for AgenticAI SDK.

Supports:
- YAML static defaults (agenticai.yaml)
- JSON runtime overrides (from frontend/gateway)
- Pydantic validation
- Environment variable interpolation
"""

from .loader import load_config, merge_configs, ConfigLoader
from .schemas import (
    AgenticAIConfig,
    PlatformConfig,
    IntegrationsConfig,
    ChatModelConfig,
    ToolConfig,
    MiddlewareConfig,
    PersistenceConfig,
    DatabaseRouteConfig,
    RAGConfig,
    SandboxConfig,
    SkillConfig,
)

__all__ = [
    "load_config",
    "merge_configs",
    "ConfigLoader",
    "AgenticAIConfig",
    "PlatformConfig",
    "IntegrationsConfig",
    "ChatModelConfig",
    "ToolConfig",
    "MiddlewareConfig",
    "PersistenceConfig",
    "DatabaseRouteConfig",
    "RAGConfig",
    "SandboxConfig",
    "SkillConfig",
]
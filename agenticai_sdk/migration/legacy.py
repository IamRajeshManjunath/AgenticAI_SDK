"""Legacy configuration migration utilities."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field

from ..config.schemas import (
    AgenticAIConfig,
    ChatModelConfig,
    DatabaseRouteConfig,
    DatabasePurpose,
    FeatureFlags,
    IntegrationType,
    LLMConfig,
)

logger = logging.getLogger(__name__)


class LegacyConfigMigrator:
    """Migrates legacy configuration formats to AgenticAI v0.3 format."""

    def __init__(self):
        self.migrations_applied: List[str] = []

    def migrate(self, config: Dict[str, Any]) -> AgenticAIConfig:
        """Migrate a legacy config dict to AgenticAIConfig."""
        # Detect legacy format
        if self._is_legacy_llm_config(config):
            return self._migrate_llm_config(config)
        
        if self._is_legacy_agenticai_config(config):
            return self._migrate_agenticai_v02_config(config)
        
        # Already v0.3 format
        return AgenticAIConfig(**config)

    def migrate_file(self, path: Union[str, Path]) -> AgenticAIConfig:
        """Migrate a legacy config file."""
        path = Path(path)
        with open(path) as f:
            if path.suffix in (".yaml", ".yml"):
                config = yaml.safe_load(f)
            elif path.suffix == ".json":
                import json
                config = json.load(f)
            else:
                raise ValueError(f"Unsupported config format: {path.suffix}")
        
        return self.migrate(config)

    def _is_legacy_llm_config(self, config: Dict[str, Any]) -> bool:
        """Check if config is legacy LLMConfig format."""
        return "provider" in config and "model" in config and "type" not in config

    def _is_legacy_agenticai_config(self, config: Dict[str, Any]) -> bool:
        """Check if config is legacy AgenticAI v0.1/v0.2 format."""
        return "platform" in config or "llm" in config or "database" in config

    def _migrate_llm_config(self, config: Dict[str, Any]) -> AgenticAIConfig:
        """Migrate legacy LLMConfig to AgenticAIConfig."""
        self.migrations_applied.append("llm_config_to_agenticai")
        
        provider = config.get("provider", "openai")
        model = config.get("model", "gpt-4o")
        
        # Map legacy provider to integration type
        provider_map = {
            "openai": IntegrationType.OPENAI,
            "anthropic": IntegrationType.ANTHROPIC,
            "google": IntegrationType.GOOGLE_GENAI,
            "groq": IntegrationType.GROQ,
            "mistral": IntegrationType.MISTRAL,
            "cohere": IntegrationType.COHERE,
        }
        
        chat_model = ChatModelConfig(
            type=provider_map.get(provider, IntegrationType.OPENAI),
            provider=provider,
            model=model,
            api_key_env=config.get("api_key_env", f"{provider.upper()}_API_KEY"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens"),
            features=FeatureFlags(
                stream=config.get("stream", True),
                tools=config.get("tools", True),
                structured_output=config.get("structured_output", True),
            ),
        )
        
        return AgenticAIConfig(
            platform={"default_chat_model": "primary"},
            chat_models={"primary": chat_model},
        )

    def _migrate_agenticai_v02_config(self, config: Dict[str, Any]) -> AgenticAIConfig:
        """Migrate AgenticAI v0.1/v0.2 config to v0.3."""
        self.migrations_applied.append("agenticai_v02_to_v03")
        
        # Extract platform config
        platform = config.get("platform", {})
        
        # Migrate chat models
        chat_models = {}
        legacy_llm = config.get("llm", {})
        if legacy_llm:
            chat_models["primary"] = self._migrate_legacy_llm(legacy_llm)
        
        # Migrate additional llms
        for key, llm_config in config.get("llms", {}).items():
            chat_models[key] = self._migrate_legacy_llm(llm_config)
        
        # Migrate databases
        database_routes = {}
        legacy_db = config.get("database", {})
        if legacy_db:
            database_routes["primary"] = self._migrate_legacy_database(legacy_db)
        
        for key, db_config in config.get("databases", {}).items():
            database_routes[key] = self._migrate_legacy_database(db_config)
        
        # Migrate tools
        tools = config.get("tools", {})
        
        # Migrate middleware
        middleware = config.get("middleware", [])
        
        return AgenticAIConfig(
            platform=platform,
            chat_models=chat_models,
            database_routes=database_routes,
            tools=tools,
            middleware=middleware,
            features=config.get("features", {}),
        )

    def _migrate_legacy_llm(self, config: Dict[str, Any]) -> ChatModelConfig:
        """Migrate a single legacy LLM config."""
        provider = config.get("provider", "openai")
        provider_map = {
            "openai": IntegrationType.OPENAI,
            "anthropic": IntegrationType.ANTHROPIC,
            "google": IntegrationType.GOOGLE_GENAI,
            "groq": IntegrationType.GROQ,
            "mistral": IntegrationType.MISTRAL,
            "cohere": IntegrationType.COHERE,
        }
        
        return ChatModelConfig(
            type=provider_map.get(provider, IntegrationType.OPENAI),
            provider=provider,
            model=config.get("model", "gpt-4o"),
            api_key_env=config.get("api_key_env", f"{provider.upper()}_API_KEY"),
            temperature=config.get("temperature", 0.7),
            max_tokens=config.get("max_tokens"),
            features=FeatureFlags(
                stream=config.get("stream", True),
                tools=config.get("tools", True),
                structured_output=config.get("structured_output", True),
            ),
        )

    def _migrate_legacy_database(self, config: Dict[str, Any]) -> DatabaseRouteConfig:
        """Migrate a single legacy database config."""
        db_type = config.get("type", "postgresql")
        purpose_map = {
            "vector": DatabasePurpose.VECTOR_STORE,
            "checkpointer": DatabasePurpose.CHECKPOINTER,
            "store": DatabasePurpose.STORE,
            "analytics": DatabasePurpose.ANALYTICS,
            "audit": DatabasePurpose.AUDIT_LOG,
            "cache": DatabasePurpose.CACHE,
            "rate_limit": DatabasePurpose.RATE_LIMIT,
        }
        
        return DatabaseRouteConfig(
            purpose=purpose_map.get(config.get("purpose", "vector"), DatabasePurpose.VECTOR_STORE),
            provider=db_type,
            config=config.get("config", {}),
            schema_contract=config.get("schema", {}),
        )


def migrate_legacy_config(config: Dict[str, Any]) -> AgenticAIConfig:
    """Convenience function to migrate legacy config."""
    migrator = LegacyConfigMigrator()
    return migrator.migrate(config)


class MigrationReport(BaseModel):
    """Report of migrations applied."""
    migrations_applied: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    original_config: Dict[str, Any] = Field(default_factory=dict)
    migrated_config: Optional[AgenticAIConfig] = None
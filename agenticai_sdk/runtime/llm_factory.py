"""
LLMClientFactory — resolves LLMConfig into initialized, async-capable
LangChain chat model objects with configured retry handlers.

Supports both legacy LLMConfig and new plugin-based ChatModelConfig.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional, Union

import structlog
from langchain_core.language_models import BaseChatModel

from agenticai_sdk.exceptions import LLMProviderError
from agenticai_sdk.schemas.llm import LLMConfig, LLMProvider
from agenticai_sdk.config.schemas import ChatModelConfig, FeatureFlags
from agenticai_sdk.plugins import get_global_registry, IntegrationType

logger = structlog.get_logger(__name__)


# Legacy provider feature flags (for backward compat)
LEGACY_FEATURES: Dict[LLMProvider, FeatureFlags] = {
    LLMProvider.OPENAI: FeatureFlags(stream=True, tools=True, structured_output=True, multimodal=True),
    LLMProvider.ANTHROPIC: FeatureFlags(stream=True, tools=True, structured_output=True, multimodal=True),
    LLMProvider.OLLAMA: FeatureFlags(stream=True, tools=True, structured_output=True, multimodal=False),
}


class LLMClientFactory:
    """Resolves ``LLMConfig`` or ``ChatModelConfig`` into an initialized LangChain ``BaseChatModel``.
    
    Supports:
    - Legacy LLMConfig (backward compatible)
    - New plugin-based ChatModelConfig (50+ providers)
    - Dynamic plugin registry discovery
    
    Usage::
    
        factory = LLMClientFactory()
        llm = factory.create(llm_config)  # Legacy
        llm = factory.create_from_config(chat_model_config)  # New
    """
    
    def __init__(self, registry=None):
        self.registry = registry or get_global_registry()
        # Ensure plugins are loaded
        self.registry.load_entry_points()
    
    # -------------------------------------------------------------------------
    # Legacy API (backward compatible)
    # -------------------------------------------------------------------------
    
    def create(self, config: LLMConfig) -> BaseChatModel:
        """Create LLM from legacy LLMConfig."""
        try:
            api_key = self._resolve_api_key(config)
            
            if config.provider == LLMProvider.OPENAI:
                model = self._create_openai(config, api_key)
            elif config.provider == LLMProvider.ANTHROPIC:
                model = self._create_anthropic(config, api_key)
            elif config.provider == LLMProvider.OLLAMA:
                model = self._create_ollama(config)
            else:
                raise LLMProviderError(
                    f"Unsupported LLM provider: {config.provider}",
                    detail={"provider": config.provider.value},
                )
            
            logger.info(
                "llm_client_created",
                provider=config.provider.value,
                model=config.model_name,
                temperature=config.temperature,
            )
            return model
        
        except LLMProviderError:
            raise
        except Exception as exc:
            raise LLMProviderError(
                f"Failed to create LLM client for provider '{config.provider.value}': {exc}",
                detail={"provider": config.provider.value, "model": config.model_name, "error": str(exc)},
            ) from exc
    
    def get_provider_features(self, provider: LLMProvider) -> FeatureFlags:
        """Get feature flags for legacy provider."""
        return LEGACY_FEATURES.get(provider, FeatureFlags())
    
    # -------------------------------------------------------------------------
    # New Plugin-Based API
    # -------------------------------------------------------------------------
    
    def create_from_config(self, config: ChatModelConfig) -> BaseChatModel:
        """Create LLM from new plugin-based ChatModelConfig."""
        # Try plugin registry first
        plugin = self.registry.get_plugin(IntegrationType.CHAT_MODEL, config.provider)
        if plugin:
            return self._create_from_plugin(plugin, config)
        
        # Fallback to legacy providers
        return self._create_legacy_fallback(config)
    
    def _create_from_plugin(self, plugin, config: ChatModelConfig) -> BaseChatModel:
        """Create LLM instance from plugin."""
        try:
            # Convert config to dict for plugin
            config_dict = config.model_dump()
            
            # Resolve API key from environment
            if "config" in config_dict and "api_key_env" in config_dict["config"]:
                api_key_env = config_dict["config"]["api_key_env"]
                api_key = os.getenv(api_key_env)
                if not api_key:
                    logger.warning("api_key_env_var_not_set", env_var=api_key_env, provider=config.provider)
                    api_key = "mock-key"
                config_dict["config"]["api_key"] = api_key
                del config_dict["config"]["api_key_env"]
            
            # Create instance via plugin
            instance = plugin.create_instance(config_dict)
            
            logger.info(
                "llm_client_created_plugin",
                provider=config.provider,
                model=config.model,
                temperature=config.temperature,
            )
            return instance
        
        except Exception as exc:
            raise LLMProviderError(
                f"Failed to create LLM client for provider '{config.provider}': {exc}",
                detail={"provider": config.provider, "model": config.model, "error": str(exc)},
            ) from exc
    
    def _create_legacy_fallback(self, config: ChatModelConfig) -> BaseChatModel:
        """Fallback to legacy creation for built-in providers."""
        # Map provider string to legacy enum
        provider_map = {
            "openai": LLMProvider.OPENAI,
            "anthropic": LLMProvider.ANTHROPIC,
            "ollama": LLMProvider.OLLAMA,
        }
        
        legacy_provider = provider_map.get(config.provider)
        if legacy_provider is None:
            raise LLMProviderError(
                f"Unsupported LLM provider: {config.provider}",
                detail={"provider": config.provider},
            )
        
        # Convert to legacy config
        legacy_config = LLMConfig(
            provider=legacy_provider,
            model_name=config.model,
            temperature=config.temperature,
            api_key_env_var=config.config.get("api_key_env", ""),
            max_retries=config.max_retries,
            request_timeout=config.timeout,
        )
        
        return self.create(legacy_config)
    
    def create_from_json(self, json_config: Dict[str, Any]) -> BaseChatModel:
        """Create LLM from JSON configuration (runtime override)."""
        config = ChatModelConfig(**json_config)
        return self.create_from_config(config)
    
    # -------------------------------------------------------------------------
    # Legacy Implementation Methods
    # -------------------------------------------------------------------------
    
    def _resolve_api_key(self, config: LLMConfig) -> str | None:
        """Read the API key from the environment."""
        key = os.getenv(config.api_key_env_var)
        if not key:
            logger.warning(
                "api_key_env_var_not_set",
                env_var=config.api_key_env_var,
                provider=config.provider.value,
            )
            return "mock-key"
        return key
    
    def _create_openai(self, config: LLMConfig, api_key: str | None) -> BaseChatModel:
        """Create a ChatOpenAI instance."""
        try:
            from langchain_openai import ChatOpenAI
            
            return ChatOpenAI(
                model=config.model_name,
                temperature=config.temperature,
                api_key=api_key,
                max_retries=config.max_retries,
                request_timeout=config.request_timeout,
            )
        except ImportError as exc:
            raise LLMProviderError(
                "langchain-openai is not installed. Run: pip install langchain-openai",
                detail={"provider": "openai"},
            ) from exc
    
    def _create_anthropic(self, config: LLMConfig, api_key: str | None) -> BaseChatModel:
        """Create a ChatAnthropic instance."""
        try:
            from langchain_anthropic import ChatAnthropic
            
            return ChatAnthropic(
                model=config.model_name,
                temperature=config.temperature,
                api_key=api_key,
                max_retries=config.max_retries,
                timeout=config.request_timeout,
            )
        except ImportError as exc:
            raise LLMProviderError(
                "langchain-anthropic is not installed. Run: pip install langchain-anthropic",
                detail={"provider": "anthropic"},
            ) from exc
    
    def _create_ollama(self, config: LLMConfig) -> BaseChatModel:
        """Create a ChatOllama instance (local inference, no API key required)."""
        try:
            from langchain_ollama import ChatOllama
            
            return ChatOllama(
                model=config.model_name,
                temperature=config.temperature,
            )
        except ImportError as exc:
            raise LLMProviderError(
                "langchain-ollama is not installed. Run: pip install langchain-ollama",
                detail={"provider": "ollama"},
            ) from exc
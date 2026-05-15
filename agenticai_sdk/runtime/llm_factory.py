"""
LLMClientFactory — resolves LLMConfig into initialized, async-capable
LangChain chat model objects with configured retry handlers.
"""

from __future__ import annotations

import os

import structlog
from langchain_core.language_models import BaseChatModel

from agenticai_sdk.exceptions import LLMProviderError
from agenticai_sdk.schemas.llm import LLMConfig, LLMProvider

logger = structlog.get_logger(__name__)


class LLMClientFactory:
    """Resolves ``LLMConfig`` into an initialized LangChain ``BaseChatModel``.

    Supports OpenAI, Anthropic, and Ollama providers with automatic retry
    configuration applied at the LangChain level.

    Usage::

        factory = LLMClientFactory()
        llm = factory.create(llm_config)
    """

    def create(self, config: LLMConfig) -> BaseChatModel:
        """Instantiate and return the appropriate LangChain chat model.

        Args:
            config: Validated ``LLMConfig`` specifying provider, model, and credentials.

        Returns:
            Configured ``BaseChatModel`` instance ready for async invocation.

        Raises:
            LLMProviderError: If the provider cannot be instantiated.
        """
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

    def _resolve_api_key(self, config: LLMConfig) -> str | None:
        """Read the API key from the environment."""
        key = os.getenv(config.api_key_env_var)
        if not key:
            logger.warning(
                "api_key_env_var_not_set",
                env_var=config.api_key_env_var,
                provider=config.provider.value,
            )
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
            from langchain_community.chat_models import ChatOllama

            return ChatOllama(
                model=config.model_name,
                temperature=config.temperature,
            )
        except ImportError as exc:
            raise LLMProviderError(
                "langchain-community is not installed. Run: pip install langchain-community",
                detail={"provider": "ollama"},
            ) from exc

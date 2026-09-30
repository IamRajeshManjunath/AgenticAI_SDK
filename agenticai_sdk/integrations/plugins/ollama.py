"""Ollama plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


OllamaPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="ollama",
    name="Ollama",
    description="Local LLM inference via Ollama",
    package_name="langchain-ollama",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.ollama.OllamaConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/ollama",
    downloads_per_month=3000000,
    tags=["ollama", "local", "llama", "privacy", "offline"],
)

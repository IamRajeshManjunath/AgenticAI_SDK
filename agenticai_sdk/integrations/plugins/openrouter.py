"""OpenRouter plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


OpenRouterPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="openrouter",
    name="OpenRouter",
    description="OpenRouter unified API for 200+ models",
    package_name="langchain-openrouter",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.openrouter.OpenRouterConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/openrouter",
    downloads_per_month=935000,
    tags=["openrouter", "gateway", "unified", "200+ models"],
)

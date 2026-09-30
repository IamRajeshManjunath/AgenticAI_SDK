"""Mistral AI plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


MistralPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="mistral",
    name="Mistral AI",
    description="Mistral AI chat models (Mistral Large, Mixtral, etc.)",
    package_name="langchain-mistralai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.mistral.MistralConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/mistralai",
    downloads_per_month=960000,
    tags=["mistral", "mixtral", "chat", "open-weights"],
)

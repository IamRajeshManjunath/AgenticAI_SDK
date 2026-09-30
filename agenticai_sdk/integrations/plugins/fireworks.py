"""Fireworks AI plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


FireworksPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="fireworks",
    name="Fireworks AI",
    description="Fireworks AI inference (Llama, Mixtral, etc.)",
    package_name="langchain-fireworks",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.fireworks.FireworksConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/fireworks",
    downloads_per_month=971000,
    tags=["fireworks", "llama", "mixtral", "inference"],
)

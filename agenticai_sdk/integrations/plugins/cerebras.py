"""Cerebras plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


CerebrasPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="cerebras",
    name="Cerebras",
    description="Cerebras ultra-fast inference (Llama 3.1)",
    package_name="langchain-cerebras",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.cerebras.CerebrasConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/cerebras",
    downloads_per_month=188000,
    tags=["cerebras", "fast", "inference", "llama", "wafer-scale"],
)

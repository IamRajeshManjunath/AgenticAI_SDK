"""xAI (Grok) plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


XAIPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="xai",
    name="xAI Grok",
    description="xAI Grok chat models",
    package_name="langchain-xai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.xai.XAIConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/xai",
    downloads_per_month=769000,
    tags=["xai", "grok", "chat", "elon-musk"],
)

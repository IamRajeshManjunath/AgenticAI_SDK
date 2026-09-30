"""DeepSeek plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


DeepSeekPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="deepseek",
    name="DeepSeek",
    description="DeepSeek chat models (DeepSeek-V3, DeepSeek-R1)",
    package_name="langchain-deepseek",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.deepseek.DeepSeekConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/deepseek",
    downloads_per_month=616000,
    tags=["deepseek", "chat", "reasoning", "open-source"],
)

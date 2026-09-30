"""LiteLLM plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


LiteLLMPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="litellm",
    name="LiteLLM",
    description="LiteLLM unified proxy for 100+ LLM providers",
    package_name="langchain-litellm",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.litellm.LiteLLMConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/litellm",
    downloads_per_month=1000000,
    tags=["litellm", "proxy", "unified", "gateway"],
)

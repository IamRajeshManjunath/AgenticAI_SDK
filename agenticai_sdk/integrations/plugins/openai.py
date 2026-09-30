"""OpenAI plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


OpenAIPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="openai",
    name="OpenAI",
    description="OpenAI chat models (GPT-4o, GPT-4, GPT-3.5)",
    package_name="langchain-openai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.openai.OpenAIConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/openai",
    downloads_per_month=64000000,
    tags=["openai", "gpt", "chat", "multimodal"],
)


AzureOpenAIPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="azure_openai",
    name="Azure OpenAI",
    description="OpenAI models hosted on Microsoft Azure",
    package_name="langchain-openai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.openai.AzureOpenAIConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/azure_chat_openai",
    downloads_per_month=64000000,
    tags=["azure", "openai", "gpt", "enterprise"],
)

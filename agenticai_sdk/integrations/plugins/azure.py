"""Azure AI plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


AzureAIPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="azure_ai",
    name="Azure AI",
    description="Azure AI model catalog (Phi, Llama, Mistral, etc.)",
    package_name="langchain-azure-ai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.azure.AzureAIConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/azure_ai",
    downloads_per_month=973000,
    tags=["azure", "ai", "phi", "llama", "mistral", "catalog"],
)

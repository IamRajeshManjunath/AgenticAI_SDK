"""IBM WatsonX plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


WatsonXPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="watsonx",
    name="IBM WatsonX",
    description="IBM WatsonX foundation models (Granite, Llama, etc.)",
    package_name="langchain-ibm",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.ibm.WatsonXConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/ibm_watsonx",
    downloads_per_month=481000,
    tags=["ibm", "watsonx", "granite", "enterprise"],
)


WatsonXEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="watsonx",
    name="IBM WatsonX Embeddings",
    description="IBM WatsonX embedding models",
    package_name="langchain-ibm",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.ibm.WatsonXEmbeddingsConfig",
    downloads_per_month=481000,
    tags=["ibm", "watsonx", "embeddings"],
)

"""Together AI plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


TogetherPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="together",
    name="Together AI",
    description="Together AI inference (Llama, Mixtral, Qwen, etc.)",
    package_name="langchain-together",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.together.TogetherConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/together",
    downloads_per_month=96000,
    tags=["together", "llama", "mixtral", "qwen", "inference"],
)


TogetherEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="together",
    name="Together AI Embeddings",
    description="Together AI embedding models",
    package_name="langchain-together",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.together.TogetherEmbeddingsConfig",
    downloads_per_month=96000,
    tags=["together", "embeddings"],
)

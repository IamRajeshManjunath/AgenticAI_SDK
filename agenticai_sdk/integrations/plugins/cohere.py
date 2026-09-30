"""Cohere plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


CoherePluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="cohere",
    name="Cohere",
    description="Cohere chat models (Command R+, Command R)",
    package_name="langchain-cohere",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.cohere.CohereConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/cohere",
    downloads_per_month=790000,
    tags=["cohere", "command", "chat", "rag"],
)


CohereEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="cohere",
    name="Cohere Embeddings",
    description="Cohere embedding models",
    package_name="langchain-cohere",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.cohere.CohereEmbeddingsConfig",
    downloads_per_month=790000,
    tags=["cohere", "embeddings"],
)

"""Pinecone plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


PineconePluginMetadata = PluginMetadata(
    type=IntegrationType.VECTOR_STORE,
    provider="pinecone",
    name="Pinecone",
    description="Pinecone managed vector database",
    package_name="langchain-pinecone",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=False,
        structured_output=False,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.pinecone.PineconeVectorStoreConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/vectorstores/pinecone",
    downloads_per_month=744000,
    tags=["pinecone", "vector", "database", "managed", "rag"],
)

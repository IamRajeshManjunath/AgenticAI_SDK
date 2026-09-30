"""Qdrant plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


QdrantPluginMetadata = PluginMetadata(
    type=IntegrationType.VECTOR_STORE,
    provider="qdrant",
    name="Qdrant",
    description="Qdrant vector database for similarity search",
    package_name="langchain-qdrant",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=False,
        structured_output=False,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.qdrant.QdrantVectorStoreConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant",
    downloads_per_month=765000,
    tags=["qdrant", "vector", "database", "search", "rag"],
)


QdrantCheckpointerPluginMetadata = PluginMetadata(
    type=IntegrationType.CHECKPOINTER,
    provider="qdrant",
    name="Qdrant Checkpointer",
    description="Qdrant as LangGraph checkpointer",
    package_name="langchain-qdrant",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.qdrant.QdrantCheckpointerConfig",
    downloads_per_month=765000,
    tags=["qdrant", "checkpointer", "langgraph"],
)

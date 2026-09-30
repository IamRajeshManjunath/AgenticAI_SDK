"""Databricks plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


DatabricksPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="databricks",
    name="Databricks",
    description="Databricks Mosaic AI models (Llama, DBRX, etc.)",
    package_name="databricks-langchain",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.databricks.DatabricksConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/databricks",
    downloads_per_month=2000000,
    tags=["databricks", "mosaic", "dbrx", "llama", "enterprise"],
)


DatabricksEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="databricks",
    name="Databricks Embeddings",
    description="Databricks embedding models",
    package_name="databricks-langchain",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.databricks.DatabricksEmbeddingsConfig",
    downloads_per_month=2000000,
    tags=["databricks", "embeddings"],
)

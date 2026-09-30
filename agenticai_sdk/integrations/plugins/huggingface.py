"""HuggingFace plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


HuggingFacePluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="huggingface",
    name="HuggingFace",
    description="HuggingFace Inference Endpoints (TGI, etc.)",
    package_name="langchain-huggingface",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.huggingface.HuggingFaceConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/huggingface",
    downloads_per_month=1000000,
    tags=["huggingface", "tgi", "inference", "open-source"],
)


HuggingFaceEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="huggingface",
    name="HuggingFace Embeddings",
    description="HuggingFace sentence transformers",
    package_name="langchain-huggingface",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.huggingface.HuggingFaceEmbeddingsConfig",
    downloads_per_month=1000000,
    tags=["huggingface", "sentence-transformers", "embeddings"],
)

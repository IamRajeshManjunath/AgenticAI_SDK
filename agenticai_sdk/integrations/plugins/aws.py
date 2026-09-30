"""AWS plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


BedrockPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="bedrock",
    name="AWS Bedrock",
    description="AWS Bedrock foundation models (Claude, Titan, Llama, etc.)",
    package_name="langchain-aws",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.aws.BedrockConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/bedrock",
    downloads_per_month=11000000,
    tags=["aws", "bedrock", "claude", "titan", "llama", "multimodal"],
)


BedrockEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="bedrock",
    name="AWS Bedrock Embeddings",
    description="AWS Bedrock embedding models (Titan, Cohere)",
    package_name="langchain-aws",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.aws.BedrockEmbeddingsConfig",
    downloads_per_month=11000000,
    tags=["aws", "bedrock", "embeddings"],
)

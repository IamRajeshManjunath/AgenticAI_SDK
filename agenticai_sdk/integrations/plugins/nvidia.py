"""NVIDIA plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


NVIDIAPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="nvidia",
    name="NVIDIA AI Endpoints",
    description="NVIDIA AI Foundation models (Nemotron, Llama, etc.)",
    package_name="langchain-nvidia-ai-endpoints",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.nvidia.NVIDIAConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/nvidia_ai_endpoints",
    downloads_per_month=749000,
    tags=["nvidia", "nemotron", "llama", "foundation", "multimodal"],
)


NVIDIAEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="nvidia",
    name="NVIDIA Embeddings",
    description="NVIDIA embedding models (NV-Embed, etc.)",
    package_name="langchain-nvidia-ai-endpoints",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.nvidia.NVIDIAEmbeddingsConfig",
    downloads_per_month=749000,
    tags=["nvidia", "embeddings", "nv-embed"],
)

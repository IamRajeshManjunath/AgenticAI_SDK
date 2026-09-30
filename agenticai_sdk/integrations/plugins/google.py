"""Google plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


GoogleGenAIPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="google_genai",
    name="Google Generative AI",
    description="Google Gemini models via Generative AI API",
    package_name="langchain-google-genai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.google.GoogleGenAIConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/google_generative_ai",
    downloads_per_month=16000000,
    tags=["google", "gemini", "chat", "multimodal"],
)


GoogleVertexAIPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="google_vertex",
    name="Google Vertex AI",
    description="Gemini Enterprise models on Vertex AI",
    package_name="langchain-google-vertexai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.google.GoogleVertexAIConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/google_vertex_ai",
    downloads_per_month=32000000,
    tags=["google", "vertex", "gemini", "enterprise"],
)


GoogleEmbeddingsPluginMetadata = PluginMetadata(
    type=IntegrationType.EMBEDDING,
    provider="google_genai",
    name="Google Generative AI Embeddings",
    description="Google Gemini embeddings",
    package_name="langchain-google-genai",
    version="0.3.0",
    features=FeatureFlags(),
    config_schema="agenticai_sdk.integrations.google.GoogleEmbeddingsConfig",
    downloads_per_month=16000000,
    tags=["google", "gemini", "embeddings"],
)

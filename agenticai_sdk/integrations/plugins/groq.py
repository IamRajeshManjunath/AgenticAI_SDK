"""Groq plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


GroqPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="groq",
    name="Groq",
    description="Groq fast inference (Llama, Mixtral, Gemma)",
    package_name="langchain-groq",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.groq.GroqConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/groq",
    downloads_per_month=2000000,
    tags=["groq", "llama", "mixtral", "fast", "inference"],
)

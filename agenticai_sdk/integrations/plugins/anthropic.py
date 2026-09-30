"""Anthropic plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


AnthropicPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="anthropic",
    name="Anthropic",
    description="Anthropic chat models (Claude 3.5 Sonnet, Claude 3 Opus, Claude 3 Haiku)",
    package_name="langchain-anthropic",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.anthropic.AnthropicConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/anthropic",
    downloads_per_month=22000000,
    tags=["anthropic", "claude", "chat", "multimodal"],
)


VertexAIAnthropicPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="vertex_anthropic",
    name="Vertex AI Anthropic",
    description="Anthropic models on Google Vertex AI",
    package_name="langchain-google-vertexai",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=True,
        structured_output=True,
        multimodal=True,
    ),
    config_schema="agenticai_sdk.integrations.anthropic.VertexAIAnthropicConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/google_anthropic_vertex",
    downloads_per_month=32000000,
    tags=["google", "vertex", "anthropic", "claude"],
)

"""Perplexity plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


PerplexityPluginMetadata = PluginMetadata(
    type=IntegrationType.CHAT_MODEL,
    provider="perplexity",
    name="Perplexity",
    description="Perplexity AI search-augmented models (Sonar)",
    package_name="langchain-perplexity",
    version="0.3.0",
    features=FeatureFlags(
        stream=True,
        tools=False,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.perplexity.PerplexityConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/chat/perplexity",
    downloads_per_month=312000,
    tags=["perplexity", "sonar", "search", "online"],
)

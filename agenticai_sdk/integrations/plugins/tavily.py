"""Tavily plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


TavilyPluginMetadata = PluginMetadata(
    type=IntegrationType.TOOL,
    provider="tavily",
    name="Tavily Search",
    description="Tavily AI-powered search API",
    package_name="langchain-tavily",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=False,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.tavily.TavilyConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/tools/tavily_search",
    downloads_per_month=645000,
    tags=["tavily", "search", "web", "research"],
)

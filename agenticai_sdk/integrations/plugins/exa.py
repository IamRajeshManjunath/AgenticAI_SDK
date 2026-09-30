"""Exa plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


ExaPluginMetadata = PluginMetadata(
    type=IntegrationType.TOOL,
    provider="exa",
    name="Exa Search",
    description="Exa AI-powered neural search",
    package_name="langchain-exa",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.exa.ExaConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/tools/exa_search",
    downloads_per_month=188000,
    tags=["exa", "search", "neural", "ai-powered"],
)
"""Google Search plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


GoogleSearchPluginMetadata = PluginMetadata(
    type=IntegrationType.TOOL,
    provider="google_search",
    name="Google Custom Search",
    description="Google Custom Search API",
    package_name="langchain-google-community",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.google_search.GoogleSearchConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/tools/google_search",
    downloads_per_month=11000000,
    tags=["google", "search", "custom-search", "cse"],
)
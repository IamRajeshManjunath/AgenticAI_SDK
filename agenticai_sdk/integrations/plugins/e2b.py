"""E2B plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


E2BPluginMetadata = PluginMetadata(
    type=IntegrationType.SANDBOX,
    provider="e2b",
    name="E2B",
    description="E2B secure code interpreter sandbox",
    package_name="langchain-e2b",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=False,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.e2b.E2BConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/sandboxes/e2b",
    downloads_per_month=13000,
    tags=["e2b", "sandbox", "code-interpreter", "secure"],
)
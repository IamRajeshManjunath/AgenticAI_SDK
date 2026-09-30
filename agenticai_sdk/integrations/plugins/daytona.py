"""Daytona plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


DaytonaPluginMetadata = PluginMetadata(
    type=IntegrationType.SANDBOX,
    provider="daytona",
    name="Daytona",
    description="Daytona secure development environment sandbox",
    package_name="langchain-daytona",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=False,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.daytona.DaytonaConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/sandboxes/daytona",
    downloads_per_month=200000,
    tags=["daytona", "sandbox", "development-environment", "secure"],
)
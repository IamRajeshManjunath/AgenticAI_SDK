"""Composio plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


ComposioPluginMetadata = PluginMetadata(
    type=IntegrationType.TOOL,
    provider="composio",
    name="Composio",
    description="Composio integration platform (500+ tools: GitHub, Slack, Jira, Notion, Salesforce, etc.)",
    package_name="langchain-composio",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=True,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.composio.ComposioConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/tools/composio",
    downloads_per_month=301000,
    tags=["composio", "integration-platform", "github", "slack", "jira", "500+"],
)
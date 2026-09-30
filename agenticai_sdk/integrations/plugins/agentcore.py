"""AgentCore plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


AgentCorePluginMetadata = PluginMetadata(
    type=IntegrationType.SANDBOX,
    provider="agentcore",
    name="AWS Bedrock AgentCore",
    description="AWS Bedrock AgentCore code interpreter sandbox",
    package_name="langchain-agentcore-codeinterpreter",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=False,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.agentcore.AgentCoreConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/sandboxes/aws",
    downloads_per_month=53000,
    tags=["aws", "bedrock", "agentcore", "sandbox", "code-interpreter"],
)
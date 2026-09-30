"""Modal plugin metadata."""

from agenticai_sdk.plugins.base import PluginMetadata, IntegrationType, FeatureFlags


ModalPluginMetadata = PluginMetadata(
    type=IntegrationType.SANDBOX,
    provider="modal",
    name="Modal",
    description="Modal serverless compute sandbox",
    package_name="langchain-modal",
    version="0.3.0",
    features=FeatureFlags(
        stream=False,
        tools=True,
        structured_output=False,
        multimodal=False,
    ),
    config_schema="agenticai_sdk.integrations.modal.ModalConfig",
    docs_url="https://docs.langchain.com/oss/python/integrations/sandboxes/modal",
    downloads_per_month=61000,
    tags=["modal", "sandbox", "serverless", "gpu"],
)
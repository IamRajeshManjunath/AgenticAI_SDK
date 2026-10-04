"""Tests for installed plugin metadata discovery."""

from types import SimpleNamespace

from agenticai_sdk.plugins.registry import IntegrationRegistry


def test_discovery_keeps_multiple_integration_types_per_package(monkeypatch):
    monkeypatch.setattr(
        "agenticai_sdk.plugins.registry.importlib.metadata.distribution",
        lambda package: SimpleNamespace(version="1.0.0"),
    )

    registry = IntegrationRegistry()
    monkeypatch.setattr(registry, "_get_download_count", lambda _package: 0)

    discovered = registry.discover_installed_packages()
    openai_integrations = {
        metadata.type.value
        for metadata in discovered
        if metadata.package_name == "langchain-openai"
    }

    assert openai_integrations == {"chat_model", "embedding"}

"""Tests for provider discovery API serialization."""

import asyncio

from agenticai_sdk.gateway.routes.plugins import list_provider_options


def test_chat_model_provider_options_expose_runtime_metadata():
    response = asyncio.run(list_provider_options())
    providers = response["providers"]

    assert providers
    assert all(provider["type"] == "chat_model" for provider in providers)
    assert all({"provider", "name", "description", "features", "docs_url"} <= provider.keys() for provider in providers)
    assert len({provider["provider"] for provider in providers}) == len(providers)

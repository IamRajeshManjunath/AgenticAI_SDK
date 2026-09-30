"""Tests for configuration system."""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from agenticai_sdk.config import load_config, merge_configs, ConfigLoader
from agenticai_sdk.config.schemas import (
    AgenticAIConfig,
    PlatformConfig,
    ChatModelConfig,
    DatabasePurpose,
    DatabaseRouteConfig,
    FeatureFlags,
)
from agenticai_sdk.schemas.llm import LLMProvider, LLMConfig


class TestMergeConfigs:
    """Test configuration merging."""
    
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_configs(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}
    
    def test_nested_merge(self):
        base = {"db": {"host": "localhost", "port": 5432}}
        override = {"db": {"port": 5433, "ssl": True}}
        result = merge_configs(base, override)
        assert result == {"db": {"host": "localhost", "port": 5433, "ssl": True}}
    
    def test_list_replace(self):
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = merge_configs(base, override)
        assert result == {"items": [4, 5]}


class TestEnvVarInterpolation:
    """Test environment variable interpolation."""
    
    def test_basic_interpolation(self):
        os.environ["TEST_API_KEY"] = "secret123"
        config = {"api_key": "${TEST_API_KEY}"}
        
        loader = ConfigLoader()
        # The interpolation happens in load_yaml_config
        from agenticai_sdk.config.loader import interpolate_env_vars
        result = interpolate_env_vars(config)
        assert result == {"api_key": "secret123"}
        
        del os.environ["TEST_API_KEY"]
    
    def test_default_value(self):
        config = {"api_key": "${NONEXISTENT:-default_key}"}
        
        from agenticai_sdk.config.loader import interpolate_env_vars
        result = interpolate_env_vars(config)
        assert result == {"api_key": "default_key"}
    
    def test_no_interpolation(self):
        config = {"api_key": "static_key"}
        
        from agenticai_sdk.config.loader import interpolate_env_vars
        result = interpolate_env_vars(config)
        assert result == {"api_key": "static_key"}


class TestConfigLoading:
    """Test configuration loading from YAML."""
    
    def test_load_minimal_config(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "platform": {
                    "name": "test",
                    "environment": "testing",
                },
                "integrations": {
                    "chat_models": [
                        {
                            "id": "test-model",
                            "provider": "openai",
                            "model": "gpt-4o",
                            "config": {"api_key_env": "OPENAI_API_KEY"},
                            "priority": 1,
                        }
                    ],
                    "tools": [],
                    "middleware": [],
                    "persistence": {},
                }
            }, f)
            config_path = f.name
        
        try:
            config = load_config(config_path)
            assert isinstance(config, AgenticAIConfig)
            assert config.platform.name == "test"
            assert len(config.integrations.chat_models) == 1
            assert config.integrations.chat_models[0].id == "test-model"
        finally:
            Path(config_path).unlink()
    
    def test_runtime_overrides(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({
                "platform": {"name": "test"},
                "integrations": {
                    "chat_models": [
                        {
                            "id": "model-1",
                            "provider": "openai",
                            "model": "gpt-4o",
                            "config": {"api_key_env": "OPENAI_API_KEY"},
                            "priority": 1,
                        }
                    ],
                    "tools": [],
                    "middleware": [],
                    "persistence": {},
                }
            }, f)
            config_path = f.name
        
        try:
            # Apply runtime override
            overrides = {
                "integrations": {
                    "chat_models": [
                        {
                            "id": "model-1",
                            "model": "gpt-4o-mini",  # Override model
                            "temperature": 0.5,
                        }
                    ]
                }
            }
            
            config = load_config(config_path, runtime_overrides=overrides)
            
            model = config.get_chat_model("model-1")
            assert model is not None
            assert model.model == "gpt-4o-mini"
            assert model.temperature == 0.5
        finally:
            Path(config_path).unlink()


class TestChatModelConfig:
    """Test chat model configuration."""
    
    def test_valid_config(self):
        config = ChatModelConfig(
            id="test-openai",
            provider="openai",
            model="gpt-4o",
            config={"api_key_env": "OPENAI_API_KEY"},
            temperature=0.7,
        )
        assert config.id == "test-openai"
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
    
    def test_feature_flags(self):
        config = ChatModelConfig(
            id="test",
            provider="openai",
            model="gpt-4o",
            config={},
            features=FeatureFlags(stream=True, tools=True, structured_output=True, multimodal=True),
        )
        assert config.features.stream is True
        assert config.features.tools is True
        assert config.features.structured_output is True
        assert config.features.multimodal is True


class TestDatabaseRouteConfig:
    """Test database route configuration."""
    
    def test_vector_store_route(self):
        route = DatabaseRouteConfig(
            name="primary-vector",
            purpose=DatabasePurpose.VECTOR_STORE,
            provider="qdrant",
            config={"url": "http://localhost:6333", "collection": "docs"},
            schema_contract={
                "purpose": "vector_store",
                "collections": {
                    "docs": {
                        "columns": {
                            "vector": {"type": "vector", "dimension": 1536},
                            "content": {"type": "text"},
                            "metadata": {"type": "json"},
                        }
                    }
                }
            },
        )
        assert route.purpose == DatabasePurpose.VECTOR_STORE
        assert route.provider == "qdrant"
    
    def test_checkpointer_route(self):
        route = DatabaseRouteConfig(
            name="langgraph-checkpointer",
            purpose=DatabasePurpose.CHECKPOINTER,
            provider="postgresql",
            config={"connectionString": "postgresql://user:pass@localhost:5432/langgraph"},
            schema_contract={
                "purpose": "checkpointer",
                "tables": {
                    "checkpoints": "langgraph_standard",
                    "checkpoint_blobs": "langgraph_standard",
                    "checkpoint_writes": "langgraph_standard",
                }
            },
        )
        assert route.purpose == DatabasePurpose.CHECKPOINTER


class TestAgenticAIConfig:
    """Test main configuration validation."""
    
    def test_valid_full_config(self):
        config = AgenticAIConfig(
            platform=PlatformConfig(name="test"),
            integrations={
                "chat_models": [
                    {
                        "id": "primary",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "config": {"api_key_env": "OPENAI_API_KEY"},
                        "priority": 1,
                    }
                ],
                "tools": [],
                "middleware": [],
                "persistence": {},
            }
        )
        assert config.platform.name == "test"
        assert len(config.integrations.chat_models) == 1
    
    def test_get_primary_chat_model(self):
        config = AgenticAIConfig(
            platform=PlatformConfig(name="test"),
            integrations={
                "chat_models": [
                    {
                        "id": "primary",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "config": {"api_key_env": "OPENAI_API_KEY"},
                        "priority": 1,
                    },
                    {
                        "id": "fallback",
                        "provider": "anthropic",
                        "model": "claude-3-5-sonnet",
                        "config": {"api_key_env": "ANTHROPIC_API_KEY"},
                        "priority": 2,
                    }
                ],
                "tools": [],
                "middleware": [],
                "persistence": {},
            }
        )
        primary = config.get_primary_chat_model()
        assert primary is not None
        assert primary.id == "primary"
        assert primary.provider == "openai"
    
    def test_get_database_route(self):
        config = AgenticAIConfig(
            platform=PlatformConfig(name="test"),
            integrations={
                "chat_models": [
                    {
                        "id": "primary",
                        "provider": "openai",
                        "model": "gpt-4o",
                        "config": {"api_key_env": "OPENAI_API_KEY"},
                        "priority": 1,
                    }
                ],
                "tools": [],
                "middleware": [],
                "persistence": {
                    "vector_store": {
                        "name": "my-vectors",
                        "purpose": "vector_store",
                        "provider": "qdrant",
                        "config": {"url": "http://localhost:6333"},
                        "schema_contract": {"purpose": "vector_store", "collections": {}},
                    }
                },
            }
        )
        route = config.get_database_route(DatabasePurpose.VECTOR_STORE)
        assert route is not None
        assert route.name == "my-vectors"
        assert route.provider == "qdrant"


class TestLegacyLLMConfig:
    """Test legacy LLM configuration."""
    
    def test_valid_legacy_config(self):
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            model_name="gpt-4o",
            api_key_env_var="OPENAI_API_KEY",
        )
        assert config.provider == LLMProvider.OPENAI
        assert config.model_name == "gpt-4o"
    
    def test_new_providers_in_enum(self):
        # Test that new providers are in enum
        assert LLMProvider.AZURE_OPENAI == "azure_openai"
        assert LLMProvider.GROQ == "groq"
        assert LLMProvider.GOOGLE_GENAI == "google_genai"
        assert LLMProvider.AWS_BEDROCK == "aws_bedrock"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
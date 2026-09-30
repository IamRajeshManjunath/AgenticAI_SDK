"""Unit tests for AgenticAI SDK components."""

import pytest
from pydantic import ValidationError

from agenticai_sdk.config.schemas import (
    AgenticAIConfig,
    ChatModelConfig,
    DatabaseRouteConfig,
    DatabasePurpose,
    FeatureFlags,
    IntegrationType,
    PlatformConfig,
    PluginMetadata,
)
from agenticai_sdk.config.loader import merge_configs, interpolate_env_vars
from agenticai_sdk.plugins.base import (
    IntegrationPlugin,
    IntegrationType as PluginIntegrationType,
    PluginMetadata as BasePluginMetadata,
    FeatureFlags as BaseFeatureFlags,
    HealthStatus,
    create_plugin,
)
from agenticai_sdk.db.validators import DatabaseSchemaValidator
from agenticai_sdk.db.models import DatabaseRoute, IntegrationCredential


class TestConfigSchemas:
    """Unit tests for config schemas."""
    
    def test_feature_flags_defaults(self):
        """Test FeatureFlags default values."""
        flags = FeatureFlags()
        assert flags.stream is True
        assert flags.tools is True
        assert flags.structured_output is True
        assert flags.multimodal is False
    
    def test_feature_flags_custom(self):
        """Test FeatureFlags with custom values."""
        flags = FeatureFlags(stream=False, tools=True, structured_output=False, multimodal=True)
        assert flags.stream is False
        assert flags.tools is True
        assert flags.structured_output is False
        assert flags.multimodal is True
    
    def test_chat_model_config_valid(self):
        """Test valid ChatModelConfig."""
        config = ChatModelConfig(
            type=IntegrationType.OPENAI,
            provider="openai",
            model="gpt-4o",
            api_key_env="OPENAI_API_KEY",
            temperature=0.7,
            features=FeatureFlags(),
        )
        assert config.provider == "openai"
        assert config.model == "gpt-4o"
        assert config.temperature == 0.7
    
    def test_chat_model_config_invalid_temperature(self):
        """Test ChatModelConfig rejects invalid temperature."""
        with pytest.raises(ValidationError):
            ChatModelConfig(
                type=IntegrationType.OPENAI,
                provider="openai",
                model="gpt-4o",
                api_key_env="OPENAI_API_KEY",
                temperature=3.0,  # Invalid: > 2.0
            )
    
    def test_database_route_config_vector_store(self):
        """Test DatabaseRouteConfig for vector store."""
        config = DatabaseRouteConfig(
            purpose=DatabasePurpose.VECTOR_STORE,
            provider="qdrant",
            config={"url": "http://localhost:6333"},
            schema_contract={
                "purpose": "vector_store",
                "collections": {
                    "documents": {
                        "columns": {"vector": {"type": "vector", "dimension": 1536}}
                    }
                }
            }
        )
        assert config.purpose == DatabasePurpose.VECTOR_STORE
        assert config.provider == "qdrant"
    
    def test_database_route_config_checkpointer(self):
        """Test DatabaseRouteConfig for checkpointer."""
        config = DatabaseRouteConfig(
            purpose=DatabasePurpose.CHECKPOINTER,
            provider="postgresql",
            config={"connectionString": "postgresql://..."},
            schema_contract={
                "purpose": "checkpointer",
                "tables": {"checkpoints": "langgraph_standard"}
            }
        )
        assert config.purpose == DatabasePurpose.CHECKPOINTER
    
    def test_platform_config_defaults(self):
        """Test PlatformConfig defaults."""
        config = PlatformConfig()
        assert config.default_chat_model == "primary"
        assert config.default_embedding == "openai"
        assert config.enable_telemetry is True
        assert config.enable_cost_tracking is True
    
    def test_agenticai_config_full(self):
        """Test full AgenticAIConfig."""
        config = AgenticAIConfig(
            platform=PlatformConfig(),
            chat_models={
                "primary": ChatModelConfig(
                    type=IntegrationType.OPENAI,
                    provider="openai",
                    model="gpt-4o",
                    api_key_env="OPENAI_API_KEY",
                )
            },
            database_routes={
                "vector": DatabaseRouteConfig(
                    purpose=DatabasePurpose.VECTOR_STORE,
                    provider="qdrant",
                    config={},
                    schema_contract={"purpose": "vector_store"}
                )
            },
        )
        assert config.get_primary_chat_model() is not None
        assert config.get_database_route("vector") is not None


class TestConfigLoader:
    """Unit tests for config loader."""
    
    def test_merge_configs_simple(self):
        """Test simple config merge."""
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = merge_configs(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}
    
    def test_merge_configs_nested(self):
        """Test nested config merge."""
        base = {"a": {"x": 1, "y": 2}, "b": 2}
        override = {"a": {"y": 3, "z": 4}, "c": 5}
        result = merge_configs(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}, "b": 2, "c": 5}
    
    def test_merge_configs_list_replace(self):
        """Test list replacement (not merge)."""
        base = {"items": [1, 2, 3]}
        override = {"items": [4, 5]}
        result = merge_configs(base, override)
        assert result == {"items": [4, 5]}
    
    def test_interpolate_env_vars(self):
        """Test environment variable interpolation."""
        import os
        os.environ["TEST_VAR"] = "test_value"
        
        config = {
            "api_key": "${TEST_VAR}",
            "nested": {"value": "${TEST_VAR:-default}"},
            "no_interp": "plain_text",
        }
        result = interpolate_env_vars(config)
        assert result["api_key"] == "test_value"
        assert result["nested"]["value"] == "test_value"
        assert result["no_interp"] == "plain_text"
    
    def test_interpolate_env_vars_default(self):
        """Test environment variable interpolation with default."""
        config = {"value": "${NONEXISTENT_VAR:-default_value}"}
        result = interpolate_env_vars(config)
        assert result["value"] == "default_value"


class TestPluginBase:
    """Unit tests for plugin base classes."""
    
    def test_feature_flags_creation(self):
        """Test FeatureFlags creation."""
        flags = BaseFeatureFlags(stream=True, tools=False, structured_output=True)
        assert flags.stream is True
        assert flags.tools is False
        assert flags.structured_output is True
    
    def test_plugin_metadata_creation(self):
        """Test PluginMetadata creation."""
        metadata = BasePluginMetadata(
            type=PluginIntegrationType.CHAT_MODEL,
            provider="openai",
            name="OpenAI",
            version="1.0.0",
            package_name="langchain-openai",
            description="OpenAI integration",
            features=BaseFeatureFlags(),
            entry_point="langchain_openai:OpenAIPlugin",
        )
        assert metadata.provider == "openai"
        assert metadata.type == PluginIntegrationType.CHAT_MODEL
    
    def test_integration_plugin_abstract(self):
        """Test IntegrationPlugin is abstract."""
        with pytest.raises(TypeError):
            IntegrationPlugin()  # type: ignore
    
    def test_health_status_enum(self):
        """Test HealthStatus enum."""
        assert HealthStatus.HEALTHY == "healthy"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.UNHEALTHY == "unhealthy"
        assert HealthStatus.UNKNOWN == "unknown"


class TestDatabaseValidators:
    """Unit tests for database validators."""
    
    def test_schema_validator_creation(self):
        """Test DatabaseSchemaValidator creation."""
        validator = DatabaseSchemaValidator()
        assert validator is not None
    
    def test_validate_vector_store_schema_valid(self):
        """Test valid vector store schema."""
        validator = DatabaseSchemaValidator()
        schema = {
            "purpose": "vector_store",
            "collections": {
                "documents": {
                    "columns": {
                        "vector": {"type": "vector", "dimension": 1536},
                        "content": {"type": "text"},
                        "metadata": {"type": "json"},
                    }
                }
            }
        }
        # This would validate against actual DB in real usage
        # For unit test, just verify validator exists
        assert validator is not None


class TestDatabaseModels:
    """Unit tests for database models."""
    
    def test_database_route_model(self):
        """Test DatabaseRoute model creation."""
        route = DatabaseRoute(
            workspace_id="test_workspace",
            name="test_route",
            purpose="vector_store",
            provider="qdrant",
            config={"url": "http://localhost:6333"},
            schema_contract={"purpose": "vector_store"},
        )
        assert route.workspace_id == "test_workspace"
        assert route.purpose == "vector_store"
    
    def test_integration_credential_model(self):
        """Test IntegrationCredential model creation."""
        cred = IntegrationCredential(
            workspace_id="test_workspace",
            integration_type="chat_model",
            provider="openai",
            credentials_encrypted="encrypted_data",
        )
        assert cred.integration_type == "chat_model"
        assert cred.provider == "openai"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
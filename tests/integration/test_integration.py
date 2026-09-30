"""Integration tests for AgenticAI SDK core functionality."""

import pytest
from agenticai_sdk.config.loader import load_config
from agenticai_sdk.config.schemas import AgenticAIConfig, ChatModelConfig, DatabaseRouteConfig, DatabasePurpose
from agenticai_sdk.plugins import get_global_registry
from agenticai_sdk.db.factory import DynamicDatabaseFactory
from agenticai_sdk.rag.factories import RAGPipeline


class TestConfigIntegration:
    """Test config loading and validation integration."""
    
    def test_load_minimal_config(self):
        """Test loading minimal valid config."""
        config = load_config()
        assert isinstance(config, AgenticAIConfig)
        assert config.platform is not None
    
    def test_load_config_with_chat_models(self):
        """Test config with chat models."""
        config_dict = {
            "platform": {"default_chat_model": "gpt4"},
            "chat_models": {
                "gpt4": {
                    "type": "openai",
                    "provider": "openai",
                    "model": "gpt-4o",
                    "api_key_env": "OPENAI_API_KEY",
                }
            },
        }
        config = AgenticAIConfig(**config_dict)
        assert "gpt4" in config.chat_models
        assert config.chat_models["gpt4"].provider == "openai"
    
    def test_load_config_with_database_routes(self):
        """Test config with database routes."""
        config_dict = {
            "platform": {},
            "database_routes": {
                "vector": {
                    "purpose": "vector_store",
                    "provider": "qdrant",
                    "config": {"url": "http://localhost:6333"},
                    "schema_contract": {
                        "purpose": "vector_store",
                        "collections": {
                            "documents": {
                                "columns": {
                                    "vector": {"type": "vector", "dimension": 1536}
                                }
                            }
                        }
                    }
                }
            }
        }
        config = AgenticAIConfig(**config_dict)
        assert "vector" in config.database_routes
        assert config.database_routes["vector"].purpose == DatabasePurpose.VECTOR_STORE


class TestPluginRegistryIntegration:
    """Test plugin registry integration."""
    
    def test_plugin_registry_loads(self):
        """Test that plugin registry loads entry points."""
        registry = get_global_registry()
        registry.load_entry_points()
        assert len(registry._metadata) > 0
    
    def test_chat_model_plugins_available(self):
        """Test that chat model plugins are available."""
        registry = get_global_registry()
        registry.load_entry_points()
        
        chat_models = [p for p in registry._metadata.values() if p.type.value == "chat_model"]
        assert len(chat_models) >= 20
        
        providers = {p.provider for p in chat_models}
        expected = {"openai", "anthropic", "groq", "mistral", "cohere", "google_genai"}
        assert expected.issubset(providers)
    
    def test_tool_plugins_available(self):
        """Test that tool plugins are available."""
        registry = get_global_registry()
        registry.load_entry_points()
        
        tools = [p for p in registry._metadata.values() if p.type.value == "tool"]
        assert len(tools) >= 3
        
        providers = {p.provider for p in tools}
        assert "tavily" in providers
        assert "composio" in providers
    
    def test_vector_store_plugins_available(self):
        """Test that vector store plugins are available."""
        registry = get_global_registry()
        registry.load_entry_points()
        
        vector_stores = [p for p in registry._metadata.values() if p.type.value == "vector_store"]
        assert len(vector_stores) >= 2
        
        providers = {p.provider for p in vector_stores}
        assert "qdrant" in providers
        assert "pinecone" in providers
    
    def test_sandbox_plugins_available(self):
        """Test that sandbox plugins are available."""
        registry = get_global_registry()
        registry.load_entry_points()
        
        sandboxes = [p for p in registry._metadata.values() if p.type.value == "sandbox"]
        assert len(sandboxes) >= 3
        
        providers = {p.provider for p in sandboxes}
        assert "e2b" in providers
        assert "modal" in providers


class TestDatabaseFactoryIntegration:
    """Test database factory integration."""
    
    def test_database_factory_creation(self):
        """Test DynamicDatabaseFactory can be instantiated."""
        factory = DynamicDatabaseFactory()
        assert factory is not None
    
    def test_database_route_validation(self):
        """Test database route config validation."""
        route = DatabaseRouteConfig(
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
        assert route.purpose == DatabasePurpose.VECTOR_STORE


class TestRAGPipelineIntegration:
    """Test RAG pipeline integration."""
    
    def test_rag_pipeline_creation(self):
        """Test RAGPipeline can be instantiated."""
        pipeline = RAGPipeline()
        assert pipeline is not None
    
    def test_embedding_factory_available(self):
        """Test EmbeddingFactory is available."""
        from agenticai_sdk.rag.factories import EmbeddingFactory
        factory = EmbeddingFactory()
        assert factory is not None
    
    def test_vector_store_factory_available(self):
        """Test VectorStoreFactory is available."""
        from agenticai_sdk.rag.factories import VectorStoreFactory
        factory = VectorStoreFactory()
        assert factory is not None


class TestMiddlewareIntegration:
    """Test middleware integration."""
    
    def test_middleware_registry_available(self):
        """Test MiddlewareRegistry is available."""
        from agenticai_sdk.middleware.registry import MiddlewareRegistry
        registry = MiddlewareRegistry()
        assert registry is not None
    
    def test_default_pipeline_creation(self):
        """Test default middleware pipeline creation."""
        from agenticai_sdk.middleware.registry import create_default_pipeline
        pipeline = create_default_pipeline()
        assert pipeline is not None


class TestBackendIntegration:
    """Test backend integration."""
    
    def test_backend_registry_available(self):
        """Test BackendRegistry is available."""
        from agenticai_sdk.runtime.backend_registry import BackendRegistry
        registry = BackendRegistry()
        assert registry is not None


class TestSecurityIntegration:
    """Test security/IAM integration."""
    
    def test_permissions_available(self):
        """Test permissions are defined."""
        from agenticai_sdk.auth.permissions import (
            PERMISSION_INTEGRATION_CHAT_MODEL_READ,
            PERMISSION_INTEGRATION_CHAT_MODEL_WRITE,
            PERMISSION_DATABASE_ROUTE_READ,
            PERMISSION_DATABASE_ROUTE_WRITE,
        )
        assert PERMISSION_INTEGRATION_CHAT_MODEL_READ
        assert PERMISSION_INTEGRATION_CHAT_MODEL_WRITE
        assert PERMISSION_DATABASE_ROUTE_READ
        assert PERMISSION_DATABASE_ROUTE_WRITE
    
    def test_api_key_scopes(self):
        """Test API key scopes schema."""
        from agenticai_sdk.auth.schemas import ApiKeyCreateRequest
        
        request = ApiKeyCreateRequest(
            name="Test Key",
            scopes=["chat_model:read", "database:write"],
            expires_in_days=90,
        )
        assert request.name == "Test Key"
        assert "chat_model:read" in request.scopes


class TestObservabilityIntegration:
    """Test observability integration."""
    
    def test_unified_telemetry_available(self):
        """Test UnifiedTelemetry is available."""
        from agenticai_sdk.observability.unified import UnifiedTelemetry
        telemetry = UnifiedTelemetry()
        assert telemetry is not None
    
    def test_cost_governance_available(self):
        """Test CostGovernance is available."""
        from agenticai_sdk.observability.unified import CostGovernance
        governance = CostGovernance()
        assert governance is not None
    
    def test_health_monitor_available(self):
        """Test HealthMonitor is available."""
        from agenticai_sdk.observability.unified import HealthMonitor
        monitor = HealthMonitor()
        assert monitor is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
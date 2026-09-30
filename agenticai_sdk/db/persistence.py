"""Persistence factories for AgenticAI SDK."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agenticai_sdk.plugins import get_global_registry, IntegrationType
from agenticai_sdk.config.schemas import DatabasePurpose
from agenticai_sdk.db.factory import DynamicDatabaseFactory, ConfigurationError

import structlog

logger = structlog.get_logger(__name__)


class CheckpointerFactory:
    """Factory for creating LangGraph checkpointers from user-configured databases."""
    
    def __init__(self, db_factory: DynamicDatabaseFactory):
        self._db_factory = db_factory
        self._cache: Dict[str, Any] = {}
    
    def create(self) -> Any:
        """Create checkpointer from configured CHECKPOINTER database route."""
        # This uses the DynamicDatabaseFactory which enforces purpose-bound routing
        return self._db_factory.create_checkpointer()
    
    def create_from_route(self, route_name: str) -> Any:
        """Create checkpointer from specific named route (for testing/override)."""
        route = self._db_factory.get_route_by_name(route_name)
        if not route:
            raise ConfigurationError(f"Database route not found: {route_name}")
        if route.purpose != DatabasePurpose.CHECKPOINTER:
            raise ConfigurationError(f"Route '{route_name}' is not a CHECKPOINTER (is {route.purpose.value})")
        
        self._db_factory.validate_schema(route)
        
        from agenticai_sdk.plugins import get_global_registry, IntegrationType
        registry = get_global_registry()
        plugin = registry.get_plugin(IntegrationType.CHECKPOINTER, route.provider)
        if not plugin:
            raise ConfigurationError(f"No checkpointer plugin for provider: {route.provider}")
        
        config = self._db_factory._decrypt_config(route.config, route.config_encrypted)
        return plugin.create_instance(config)
    
    def list_available_providers(self) -> List[Dict[str, Any]]:
        """List available checkpointer providers."""
        from agenticai_sdk.plugins import get_global_registry, IntegrationType
        registry = get_global_registry()
        plugins = registry.list_available(IntegrationType.CHECKPOINTER)
        return [
            {
                "provider": p.provider,
                "name": p.name,
                "description": p.description,
                "package": p.package_name,
                "version": p.version,
            }
            for p in plugins
        ]


class StoreFactory:
    """Factory for creating LangGraph stores (long-term memory) from user-configured databases."""
    
    def __init__(self, db_factory: DynamicDatabaseFactory):
        self._db_factory = db_factory
        self._cache: Dict[str, Any] = {}
    
    def create(self) -> Any:
        """Create store from configured STORE database route."""
        return self._db_factory.create_store()
    
    def create_from_route(self, route_name: str) -> Any:
        """Create store from specific named route."""
        route = self._db_factory.get_route_by_name(route_name)
        if not route:
            raise ConfigurationError(f"Database route not found: {route_name}")
        if route.purpose != DatabasePurpose.STORE:
            raise ConfigurationError(f"Route '{route_name}' is not a STORE (is {route.purpose.value})")
        
        self._db_factory.validate_schema(route)
        
        from agenticai_sdk.plugins import get_global_registry, IntegrationType
        registry = get_global_registry()
        plugin = registry.get_plugin(IntegrationType.STORE, route.provider)
        if not plugin:
            raise ConfigurationError(f"No store plugin for provider: {route.provider}")
        
        config = self._db_factory._decrypt_config(route.config, route.config_encrypted)
        return plugin.create_instance(config)
    
    def list_available_providers(self) -> List[Dict[str, Any]]:
        """List available store providers."""
        from agenticai_sdk.plugins import get_global_registry, IntegrationType
        registry = get_global_registry()
        plugins = registry.list_available(IntegrationType.STORE)
        return [
            {
                "provider": p.provider,
                "name": p.name,
                "description": p.description,
                "package": p.package_name,
                "version": p.version,
            }
            for p in plugins
        ]


class PersistenceManager:
    """High-level manager for all persistence components."""
    
    def __init__(self, db_factory: DynamicDatabaseFactory):
        self.checkpointer_factory = CheckpointerFactory(db_factory)
        self.store_factory = StoreFactory(db_factory)
        self.db_factory = db_factory
    
    def get_checkpointer(self) -> Any:
        """Get the configured checkpointer."""
        return self.checkpointer_factory.create()
    
    def get_store(self) -> Any:
        """Get the configured store (long-term memory)."""
        return self.store_factory.create()
    
    def get_vector_store(self, embedding) -> Any:
        """Get the configured vector store."""
        return self.db_factory.create_vector_store(embedding)
    
    def health_check_all(self) -> Dict[str, Any]:
        """Run health checks on all persistence components."""
        results = {}
        
        # Check checkpointer
        try:
            cp_route = self.db_factory.get_route(DatabasePurpose.CHECKPOINTER)
            if cp_route:
                results["checkpointer"] = self.db_factory.health_check(cp_route)
            else:
                results["checkpointer"] = {"healthy": False, "message": "Not configured"}
        except Exception as e:
            results["checkpointer"] = {"healthy": False, "message": str(e)}
        
        # Check store
        try:
            store_route = self.db_factory.get_route(DatabasePurpose.STORE)
            if store_route:
                results["store"] = self.db_factory.health_check(store_route)
            else:
                results["store"] = {"healthy": False, "message": "Not configured"}
        except Exception as e:
            results["store"] = {"healthy": False, "message": str(e)}
        
        # Check vector store
        try:
            vs_route = self.db_factory.get_route(DatabasePurpose.VECTOR_STORE)
            if vs_route:
                results["vector_store"] = self.db_factory.health_check(vs_route)
            else:
                results["vector_store"] = {"healthy": False, "message": "Not configured"}
        except Exception as e:
            results["vector_store"] = {"healthy": False, "message": str(e)}
        
        return results
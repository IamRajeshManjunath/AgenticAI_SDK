"""Dynamic database factory for user-provided stores."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from sqlalchemy import create_engine, Engine, inspect
from sqlalchemy.orm import Session

from agenticai_sdk.config.schemas import DatabasePurpose, DatabaseRouteConfig
from agenticai_sdk.db.models import DatabaseRoute
from agenticai_sdk.plugins import get_global_registry, IntegrationType

import structlog

logger = structlog.get_logger(__name__)


class DynamicDatabaseFactory:
    """Creates connections to user-provided databases on-demand with schema validation."""
    
    def __init__(self, workspace_id: str, db_session: Session):
        self.workspace_id = workspace_id
        self.db = db_session
        self._engine_cache: Dict[str, Engine] = {}
        self._schema_hash_cache: Dict[str, str] = {}
        self._registry = get_global_registry()
    
    def get_route(self, purpose: DatabasePurpose) -> Optional[DatabaseRoute]:
        """Get route by PURPOSE - not by name. Purpose is the key."""
        return self.db.query(DatabaseRoute).filter(
            DatabaseRoute.workspace_id == self.workspace_id,
            DatabaseRoute.purpose == purpose,
            DatabaseRoute.is_active == 1
        ).first()
    
    def get_route_by_name(self, name: str) -> Optional[DatabaseRoute]:
        """Get route by name."""
        return self.db.query(DatabaseRoute).filter(
            DatabaseRoute.workspace_id == self.workspace_id,
            DatabaseRoute.name == name,
            DatabaseRoute.is_active == 1
        ).first()
    
    def list_routes(self) -> list[DatabaseRoute]:
        """List all routes for workspace."""
        return self.db.query(DatabaseRoute).filter(
            DatabaseRoute.workspace_id == self.workspace_id,
            DatabaseRoute.is_active == 1
        ).all()
    
    def create_route(self, config: DatabaseRouteConfig, schema_hash: str) -> DatabaseRoute:
        """Create a new database route."""
        route = DatabaseRoute(
            id=f"route_{config.name}_{self.workspace_id}",
            workspace_id=self.workspace_id,
            name=config.name,
            purpose=config.purpose,
            provider=config.provider,
            config=config.config,
            schema_contract=config.schema_contract,
            schema_hash=schema_hash,
            config_encrypted=config.config_encrypted,
            is_active=1 if config.is_active else 0,
        )
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route
    
    def update_route(self, route: DatabaseRoute, config: DatabaseRouteConfig, schema_hash: str) -> DatabaseRoute:
        """Update an existing database route."""
        route.config = config.config
        route.schema_contract = config.schema_contract
        route.schema_hash = schema_hash
        route.provider = config.provider
        route.config_encrypted = config.config_encrypted
        route.is_active = 1 if config.is_active else 0
        self.db.commit()
        self.db.refresh(route)
        return route
    
    def delete_route(self, purpose: DatabasePurpose) -> bool:
        """Delete a database route."""
        route = self.get_route(purpose)
        if route:
            self.db.delete(route)
            self.db.commit()
            return True
        return False
    
    def _get_engine(self, route: DatabaseRoute) -> Engine:
        """Get or create engine for route."""
        cache_key = f"{self.workspace_id}:{route.id}"
        
        if cache_key in self._engine_cache:
            return self._engine_cache[cache_key]
        
        # Decrypt sensitive config
        config = self._decrypt_config(route.config, route.config_encrypted)
        url = self._build_connection_url(route.provider, config)
        
        engine = create_engine(url, pool_pre_ping=True, pool_recycle=3600)
        self._engine_cache[cache_key] = engine
        return engine
    
    def _build_connection_url(self, provider: str, config: Dict[str, Any]) -> str:
        """Build connection URL from provider and config."""
        if provider == "postgresql":
            host = config.get("host", "localhost")
            port = config.get("port", 5432)
            database = config.get("database", "postgres")
            user = config.get("user", "postgres")
            password = config.get("password", "")
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        elif provider == "sqlite":
            path = config.get("path", "agenticai.db")
            return f"sqlite:///{path}"
        elif provider == "qdrant":
            url = config.get("url", "http://localhost:6333")
            api_key = config.get("api_key")
            if api_key:
                return f"{url}?api_key={api_key}"
            return url
        elif provider == "redis":
            url = config.get("url", "redis://localhost:6379")
            return url
        elif provider == "redis://":
            return config.get("url", "redis://localhost:6379")
        else:
            raise ValueError(f"Unsupported provider: {provider}")
    
    def _decrypt_config(self, config: Dict, encrypted: Optional[Dict]) -> Dict:
        """Decrypt sensitive config values."""
        # In production, implement proper decryption
        # For now, just merge (assuming encrypted values are already in config)
        result = dict(config)
        if encrypted:
            result.update(encrypted)
        return result
    
    def _encrypt_config(self, config: Dict) -> tuple[Dict, Dict]:
        """Split config into non-sensitive and sensitive (encrypted)."""
        # In production, encrypt sensitive fields
        # For now, return as-is
        return config, {}
    
    def validate_schema(self, route: DatabaseRoute) -> Dict[str, Any]:
        """Validate route schema against actual database."""
        from agenticai_sdk.db.validators import DatabaseSchemaValidator
        
        engine = self._get_engine(route)
        actual_schema = self._introspect_schema(route.provider, engine)
        
        expected = route.schema_contract
        from agenticai_sdk.db.validators import DatabaseSchemaValidator
        mismatches = DatabaseSchemaValidator._compare_schemas(
            route.purpose,
            expected,
            actual_schema,
            route.provider
        )
        
        if mismatches:
            route.schema_validation_status = "drift"
            route.health_status = "degraded"
            self.db.commit()
            
            logger.warning("schema_drift_detected", 
                          route_id=route.id, 
                          purpose=route.purpose.value,
                          mismatches=mismatches)
        else:
            route.schema_validation_status = "valid"
            route.last_schema_validation = "now"
            self.db.commit()
        
        return {
            "valid": len(mismatches) == 0,
            "mismatches": mismatches,
            "status": route.schema_validation_status,
        }
    
    def _introspect_schema(self, provider: str, engine) -> Dict[str, Any]:
        """Introspect actual database schema."""
        if provider == "pinecone":
            return {"provider": "pinecone", "note": "Vector store uses API, not SQL schema"}
        
        inspector = inspect(engine)
        tables = {}
        for table_name in inspector.get_table_names():
            columns = {}
            for col in inspector.get_columns(table_name):
                columns[col["name"]] = {
                    "type": str(col["type"]),
                    "nullable": col["nullable"],
                    "default": col["default"],
                }
            tables[table_name] = {"columns": columns}
        
        return {"tables": tables}
    
    def test_connection(self, route: DatabaseRoute) -> Dict[str, Any]:
        """Test connection to database."""
        try:
            engine = self._get_engine(route)
            with engine.connect() as conn:
                from sqlalchemy import text
                conn.execute(text("SELECT 1"))
            
            route.health_status = "healthy"
            route.last_health_check = "now"
            self.db.commit()
            
            return {"healthy": True, "message": "Connection successful"}
        except Exception as e:
            route.health_status = "error"
            self.db.commit()
            
            logger.error("connection_test_failed", route_id=route.id, error=str(e))
            return {"healthy": False, "message": str(e)}
    
    def health_check(self, route: DatabaseRoute) -> Dict[str, Any]:
        """Full health check including connection and schema validation."""
        conn_result = self.test_connection(route)
        if not conn_result["healthy"]:
            return conn_result
        
        schema_result = self.validate_schema(route)
        return {
            "healthy": schema_result["valid"],
            "connection": conn_result,
            "schema": schema_result,
        }
    
    # -------------------------------------------------------------------------
    # Factory methods for specific purposes (STRICT - only accept correct purpose)
    # -------------------------------------------------------------------------
    
    def create_vector_store(self, embedding) -> Any:
        """Create vector store - ONLY works for VECTOR_STORE purpose routes."""
        route = self.get_route(DatabasePurpose.VECTOR_STORE)
        if not route:
            raise ConfigurationError(
                f"No VECTOR_STORE database configured for workspace {self.workspace_id}. "
                f"Add a database route with purpose='vector_store' in settings."
            )
        
        # Validate schema hasn't drifted
        self.validate_schema(route)
        
        # Create via plugin registry
        plugin = self._registry.get_plugin(IntegrationType.VECTOR_STORE, route.provider)
        if not plugin:
            raise ConfigurationError(f"No vector store plugin for provider: {route.provider}")
        
        config = self._decrypt_config(route.config, route.config_encrypted)
        config["embedding"] = embedding
        return plugin.create_instance(config)
    
    def create_checkpointer(self) -> Any:
        """Create checkpointer - ONLY works for CHECKPOINTER purpose routes."""
        route = self.get_route(DatabasePurpose.CHECKPOINTER)
        if not route:
            raise ConfigurationError(
                f"No CHECKPOINTER database configured for workspace {self.workspace_id}. "
                f"Add a database route with purpose='checkpointer' (PostgreSQL/SQLite/Redis)."
            )
        
        self.validate_schema(route)
        
        plugin = self._registry.get_plugin(IntegrationType.CHECKPOINTER, route.provider)
        if not plugin:
            raise ConfigurationError(f"No checkpointer plugin for provider: {route.provider}")
        
        config = self._decrypt_config(route.config, route.config_encrypted)
        return plugin.create_instance(config)
    
    def create_store(self) -> Any:
        """Create store - ONLY works for STORE purpose routes."""
        route = self.get_route(DatabasePurpose.STORE)
        if not route:
            raise ConfigurationError(
                f"No STORE database configured for long-term memory. "
                f"Add a database route with purpose='store'."
            )
        
        self.validate_schema(route)
        
        plugin = self._registry.get_plugin(IntegrationType.STORE, route.provider)
        if not plugin:
            raise ConfigurationError(f"No store plugin for provider: {route.provider}")
        
        config = self._decrypt_config(route.config, route.config_encrypted)
        return plugin.create_instance(config)
    
    def create_analytics(self) -> Engine:
        """Create analytics database engine."""
        route = self.get_route(DatabasePurpose.ANALYTICS)
        if not route:
            raise ConfigurationError("No ANALYTICS database configured")
        return self._get_engine(route)
    
    def create_cache(self) -> Any:
        """Create cache connection."""
        route = self.get_route(DatabasePurpose.CACHE)
        if not route:
            raise ConfigurationError("No CACHE database configured")
        
        plugin = self._registry.get_plugin(IntegrationType.CACHE, route.provider)
        if not plugin:
            raise ConfigurationError(f"No cache plugin for provider: {route.provider}")
        
        config = self._decrypt_config(route.config, route.config_encrypted)
        return plugin.create_instance(config)


class ConfigurationError(Exception):
    """Configuration error."""
    pass
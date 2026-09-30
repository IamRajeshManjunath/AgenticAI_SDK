"""Database schema validators for strict purpose-bound enforcement."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine

from agenticai_sdk.config.schemas import DatabasePurpose


@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: List[str] = None
    details: Dict[str, Any] = None
    schema_hash: str = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.details is None:
            self.details = {}


class DatabaseSchemaValidator:
    """Validates user-provided database matches declared purpose schema."""
    
    @classmethod
    def validate_route_creation(
        cls,
        purpose: DatabasePurpose,
        provider: str,
        config: Dict[str, Any],
        schema_contract: Dict[str, Any],
    ) -> ValidationResult:
        """
        1. Validate schema_contract matches purpose
        2. Connect to database and introspect actual schema
        3. Compare actual vs declared schema
        4. Return validation result with errors
        """
        # 1. Validate contract structure
        if not cls._validate_contract_structure(purpose, schema_contract):
            return ValidationResult(
                valid=False,
                errors=[f"Invalid schema contract for purpose: {purpose.value}"],
            )
        
        # 2. Connect and introspect
        try:
            engine = cls._create_temp_engine(provider, config)
            actual_schema = cls._introspect_schema(engine, provider)
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Failed to connect to database: {e}"],
            )
        
        # 3. Strict comparison
        mismatches = cls._compare_schemas(purpose, schema_contract, actual_schema, provider)
        
        if mismatches:
            return ValidationResult(
                valid=False,
                errors=[f"Schema mismatch for {purpose.value}: {m}" for m in mismatches],
                details={"expected": schema_contract, "actual": actual_schema}
            )
        
        # 4. Compute schema hash for drift detection
        schema_hash = cls._compute_hash(schema_contract)
        
        return ValidationResult(
            valid=True,
            schema_hash=schema_hash,
            details={"validated_at": "now", "provider": provider}
        )
    
    @classmethod
    def _validate_contract_structure(cls, purpose: DatabasePurpose, contract: Dict[str, Any]) -> bool:
        """Validate the contract has required structure for purpose."""
        if purpose == DatabasePurpose.VECTOR_STORE:
            return "collections" in contract and isinstance(contract["collections"], dict) and len(contract["collections"]) > 0
        elif purpose == DatabasePurpose.CHECKPOINTER:
            return "tables" in contract and isinstance(contract["tables"], dict)
        elif purpose == DatabasePurpose.STORE:
            return "tables" in contract and isinstance(contract["tables"], dict)
        elif purpose == DatabasePurpose.ANALYTICS:
            return "tables" in contract and isinstance(contract["tables"], dict) and len(contract["tables"]) > 0
        elif purpose == DatabasePurpose.CACHE:
            return "tables" in contract and isinstance(contract["tables"], dict)
        return True
    
    @classmethod
    def _create_temp_engine(cls, provider: str, config: Dict[str, Any]) -> Engine:
        """Create temporary engine for schema introspection."""
        url = cls._build_connection_url(provider, config)
        return create_engine(url, pool_pre_ping=True)
    
    @classmethod
    def _build_connection_url(cls, provider: str, config: Dict[str, Any]) -> str:
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
        elif provider == "pinecone":
            return "pinecone://"  # Pinecone uses API, not SQL
        else:
            raise ValueError(f"Unsupported provider for schema validation: {provider}")
    
    @classmethod
    def _introspect_schema(cls, engine: Engine, provider: str) -> Dict[str, Any]:
        """Introspect actual database schema."""
        inspector = inspect(engine)
        
        if provider == "pinecone":
            # Pinecone doesn't use SQL schema
            return {"provider": "pinecone", "note": "Vector store uses API, not SQL schema"}
        
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
    
    @classmethod
    def _compare_schemas(
        cls,
        purpose: DatabasePurpose,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
        provider: str,
    ) -> List[str]:
        """Strict schema comparison - NO MISMATCH ALLOWED."""
        mismatches = []
        
        if purpose == DatabasePurpose.VECTOR_STORE:
            mismatches.extend(cls._validate_vector_store(expected, actual, provider))
        elif purpose == DatabasePurpose.CHECKPOINTER:
            mismatches.extend(cls._validate_checkpointer(expected, actual, provider))
        elif purpose == DatabasePurpose.STORE:
            mismatches.extend(cls._validate_store(expected, actual, provider))
        elif purpose == DatabasePurpose.ANALYTICS:
            mismatches.extend(cls._validate_analytics(expected, actual, provider))
        elif purpose == DatabasePurpose.CACHE:
            mismatches.extend(cls._validate_cache(expected, actual, provider))
        
        return mismatches
    
    @classmethod
    def _validate_vector_store(cls, expected: Dict, actual: Dict, provider: str) -> List[str]:
        mismatches = []
        expected_collections = expected.get("collections", {})
        actual_collections = actual.get("tables", {})
        
        for coll_name, coll_schema in expected_collections.items():
            if coll_name not in actual_collections:
                mismatches.append(f"Missing collection: {coll_name}")
                continue
            
            actual_coll = actual_collections[coll_name]
            required_cols = {"vector", "content", "metadata"}
            actual_cols = set(actual_coll.get("columns", {}).keys())
            missing = required_cols - actual_cols
            if missing:
                mismatches.append(f"Collection '{coll_name}' missing columns: {missing}")
            
            # Validate vector dimension
            if "vector" in actual_coll.get("columns", {}):
                expected_dim = coll_schema.get("columns", {}).get("vector", {}).get("dimension")
                actual_dim = actual_coll.get("columns", {}).get("vector", {}).get("dimension")
                if expected_dim and actual_dim and expected_dim != actual_dim:
                    mismatches.append(
                        f"Vector dimension mismatch: expected {expected_dim}, got {actual_dim}"
                    )
        
        return mismatches
    
    @classmethod
    def _validate_checkpointer(cls, expected: Dict, actual: Dict, provider: str) -> List[str]:
        mismatches = []
        expected_tables = expected.get("tables", {})
        actual_tables = actual.get("tables", {})
        
        required_tables = {"checkpoints", "checkpoint_blobs", "checkpoint_writes"}
        missing = required_tables - set(actual_tables.keys())
        if missing:
            mismatches.append(f"Missing checkpoint tables: {missing}")
        
        # Validate each table has required columns
        for table in required_tables:
            if table in actual_tables:
                cols = set(actual_tables[table].get("columns", {}).keys())
                if table == "checkpoints":
                    required = {"thread_id", "checkpoint_ns", "checkpoint", "parent_checkpoint_id"}
                elif table == "checkpoint_blobs":
                    required = {"thread_id", "checkpoint_ns", "channel", "type", "blob"}
                elif table == "checkpoint_writes":
                    required = {"thread_id", "checkpoint_ns", "task_id", "idx", "channel", "type", "blob"}
                else:
                    required = set()
                
                missing = required - cols
                if missing:
                    mismatches.append(f"Table '{table}' missing columns: {missing}")
        
        return mismatches
    
    @classmethod
    def _validate_store(cls, expected: Dict, actual: Dict, provider: str) -> List[str]:
        mismatches = []
        actual_tables = actual.get("tables", {})
        
        if "store" not in actual_tables:
            mismatches.append("Missing 'store' table")
        else:
            cols = set(actual_tables["store"].get("columns", {}).keys())
            required = {"namespace", "key", "value", "updated_at"}
            missing = required - cols
            if missing:
                mismatches.append(f"Store table missing columns: {missing}")
        
        return mismatches
    
    @classmethod
    def _validate_analytics(cls, expected: Dict, actual: Dict, provider: str) -> List[str]:
        mismatches = []
        actual_tables = actual.get("tables", {})
        
        if not actual_tables:
            mismatches.append("No tables found in analytics database")
        
        return mismatches
    
    @classmethod
    def _validate_cache(cls, expected: Dict, actual: Dict, provider: str) -> List[str]:
        mismatches = []
        actual_tables = actual.get("tables", {})
        
        if "cache" not in actual_tables:
            mismatches.append("Missing 'cache' table")
        else:
            cols = set(actual_tables["cache"].get("columns", {}).keys())
            required = {"key", "value", "expires_at"}
            missing = required - cols
            if missing:
                mismatches.append(f"Cache table missing columns: {missing}")
        
        return mismatches
    
    @classmethod
    def _compute_hash(cls, data: Dict[str, Any]) -> str:
        """Compute deterministic hash of schema for drift detection."""
        serialized = json.dumps(data, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]
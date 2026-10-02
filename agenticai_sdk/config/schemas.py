"""Configuration schemas for AgenticAI SDK.

All configuration is defined as Pydantic models for validation.
Supports YAML static defaults + JSON runtime overrides.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class IntegrationType(str, Enum):
    """Types of integrations supported by the platform."""
    CHAT_MODEL = "chat_model"
    TOOL = "tool"
    MIDDLEWARE = "middleware"
    SANDBOX = "sandbox"
    CHECKPOINTER = "checkpointer"
    STORE = "store"
    VECTOR_STORE = "vector_store"
    EMBEDDING = "embedding"
    RETRIEVER = "retriever"
    TEXT_SPLITTER = "text_splitter"
    DOCUMENT_LOADER = "document_loader"
    BACKEND = "backend"
    SKILL = "skill"
    # Provider-specific values for backwards compatibility with tests
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    AZURE = "azure"
    AWS = "aws"
    GROQ = "groq"
    COHERE = "cohere"
    MISTRAL = "mistral"
    OLLAMA = "ollama"
    TOGETHER = "together"
    FIREWORKS = "fireworks"
    PERPLEXITY = "perplexity"
    VERTEX_AI = "vertex_ai"
    BEDROCK = "bedrock"


class DatabasePurpose(str, Enum):
    """Strict database purposes - each has required schema."""
    CHECKPOINTER = "checkpointer"
    STORE = "store"
    VECTOR_STORE = "vector_store"
    ANALYTICS = "analytics"
    AUDIT_LOG = "audit_log"
    CACHE = "cache"
    RATE_LIMIT = "rate_limit"


class RemoteSkillSource(BaseModel):
    """Configuration for remote skill sources (git, S3, LangSmith Fleet)."""
    type: Literal["git", "s3", "fleet"]
    url: str = Field(..., description="Repository URL or S3 bucket")
    branch: str = Field(default="main", description="Git branch")
    path: str = Field(default="skills", description="Path within repo/bucket")
    auth: Optional[Dict[str, str]] = Field(default=None, description="Auth config (token, key, etc.)")


class SkillsConfig(BaseModel):
    """Skills system configuration."""
    enabled: bool = Field(default=True, description="Enable skills system")
    skills_dir: str = Field(default="skills", description="Local skills directory (relative to project root)")
    auto_discover: bool = Field(default=True, description="Auto-discover skills on startup")
    watch_for_changes: bool = Field(default=True, description="Watch for file changes and hot reload")
    deep_agent_model: str = Field(default="anthropic:claude-sonnet-4-6", description="Default model for deep agents")
    remote_sources: List[RemoteSkillSource] = Field(default_factory=list, description="Remote skill sources")
    validation_mode: Literal["strict", "permissive"] = Field(
        default="strict",
        description="Validation mode for SKILL.md files",
    )


class FeatureFlags(BaseModel):
    """Feature support flags for integrations."""
    stream: bool = True
    tools: bool = True
    structured_output: bool = True
    multimodal: bool = False


class PluginMetadata(BaseModel):
    """Metadata for a plugin/integration provider."""
    type: IntegrationType
    provider: str
    name: str
    description: str
    package_name: str
    version: str
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    config_schema: str  # Fully qualified class name
    docs_url: str = ""
    downloads_per_month: int = 0
    tags: List[str] = []


# =============================================================================
# Platform Configuration
# =============================================================================

class PlatformConfig(BaseModel):
    """Platform-level configuration (internal, not user-configurable)."""
    name: str = "agenticai"
    environment: str = "development"  # development, staging, production
    version: str = "0.3.0"
    
    # Platform database (internal - users don't configure this)
    database_url: str = Field(
        default="sqlite:///agenticai.db",
        description="Platform database for IAM, workflows, secrets, audit logs"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Auth
    jwt_secret_env: str = "JWT_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    api_key_prefix: str = "akai_"
    bcrypt_rounds: int = 12
    
    # Encryption
    encryption_key_env: str = "ENCRYPTION_KEY"
    
    # Observability
    otel_service_name: str = "agenticai-sdk"
    otel_exporter_endpoint: Optional[str] = None
    prometheus_port: int = 9090
    
    # Feature flags
    enable_billing: bool = False
    enable_marketplace: bool = True
    enable_skills: bool = True
    enable_collaborative_editing: bool = False
    
    # Skills configuration
    skills: SkillsConfig = Field(default_factory=SkillsConfig)

    # Default model references
    default_chat_model: str = "primary"
    default_embedding: str = "openai"

    # Feature toggles
    enable_telemetry: bool = True
    enable_cost_tracking: bool = True

    # Secrets configuration
    secrets: Optional["SecretsConfig"] = Field(default=None, description="Secrets manager configuration")


class SecretsConfig(BaseModel):
    """Secrets manager configuration."""

    backend: str = Field(default="env", description="Backend: azure, aws, vault, env, dotenv, chained")
    # Azure Key Vault
    azure_vault_url: Optional[str] = Field(default=None, description="Azure Key Vault URL")
    # AWS Secrets Manager
    aws_region: str = Field(default="us-east-1", description="AWS region")
    aws_prefix: str = Field(default="", description="AWS secrets prefix")
    # HashiCorp Vault
    vault_url: Optional[str] = Field(default=None, description="Vault URL")
    vault_token: Optional[str] = Field(default=None, description="Vault token")
    vault_mount_point: str = Field(default="secret", description="Vault mount point")
    vault_kv_version: int = Field(default=2, description="Vault KV version")
    # Environment variables
    env_prefix: str = Field(default="", description="Environment variable prefix")
    # DotEnv
    dotenv_path: str = Field(default=".env", description="Path to .env file")
    # Chained
    chained_managers: list[dict[str, Any]] = Field(default_factory=list, description="Chained manager configs")


# =============================================================================
# Integration Configuration
# =============================================================================

class BaseIntegrationConfig(BaseModel):
    """Base configuration for all integrations."""
    id: str = Field(..., description="Unique identifier for this integration instance")
    provider: str = Field(..., description="Provider name (e.g., 'openai', 'tavily', 'qdrant')")
    enabled: bool = True
    priority: int = 0  # For fallback routing (lower = higher priority)
    config: Dict[str, Any] = Field(default_factory=dict)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ChatModelConfig(BaseIntegrationConfig):
    """Chat model integration configuration."""
    id: str = Field(default="primary", description="Unique identifier")
    # Backward compatibility
    type: Optional[IntegrationType] = Field(default=None, description="Legacy type field")
    model: str = Field(..., description="Model identifier (e.g., 'gpt-4o', 'claude-3-5-sonnet')")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    api_key_env: Optional[str] = Field(default=None, description="Environment variable for API key")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = None
    timeout: float = Field(default=60.0, gt=0)
    max_retries: int = Field(default=3, ge=0, le=10)
    
    # Provider-specific fields go in config dict
    # e.g., for Azure: {"azure_endpoint": "...", "azure_deployment": "...", "api_version": "..."}


class ToolConfig(BaseIntegrationConfig):
    """Tool/toolkit integration configuration."""
    tool_type: str = Field(default="toolkit", description="tool, toolkit, mcp, custom")
    apps: List[str] = Field(default_factory=list, description="For integration platforms like Composio")
    mcp_servers: List[Dict[str, Any]] = Field(default_factory=list, description="MCP server configurations")


class MiddlewareConfig(BaseModel):
    """Middleware configuration."""
    type: str = Field(..., description="Middleware type (rate_limiter, pii_masking, etc.)")
    id: str = Field(..., description="Unique identifier")
    enabled: bool = True
    priority: int = 0
    config: Dict[str, Any] = Field(default_factory=dict)


class DatabaseRouteConfig(BaseModel):
    """User-provided database route with strict purpose-bound schema."""
    name: str = Field(default="default", description="Unique name for this route")
    purpose: DatabasePurpose = Field(..., description="Purpose - determines schema requirements")
    provider: str = Field(..., description="Database provider (postgresql, qdrant, redis, clickhouse, etc.)")
    config: Dict[str, Any] = Field(..., description="Connection config (host, port, database, collection, etc.)")
    schema_contract: Dict[str, Any] = Field(..., description="Declared schema contract for validation")
    config_encrypted: Optional[Dict[str, Any]] = Field(default=None, description="Encrypted sensitive config")
    is_active: bool = True
    
    @property
    def enabled(self) -> bool:
        """Alias for is_active for backward compatibility."""
        return self.is_active
    
    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.is_active = value


class PersistenceConfig(BaseModel):
    """Persistence layer configuration - all user-provided."""
    checkpointer: Optional[DatabaseRouteConfig] = Field(default=None, description="LangGraph checkpointer")
    store: Optional[DatabaseRouteConfig] = Field(default=None, description="Long-term memory store")
    vector_store: Optional[DatabaseRouteConfig] = Field(default=None, description="Vector store for RAG")
    analytics: Optional[DatabaseRouteConfig] = Field(default=None, description="Analytics database")
    audit_log: Optional[DatabaseRouteConfig] = Field(default=None, description="Audit log database")
    cache: Optional[DatabaseRouteConfig] = Field(default=None, description="Cache database")
    rate_limit: Optional[DatabaseRouteConfig] = Field(default=None, description="Rate limit database")


class EmbeddingConfig(BaseIntegrationConfig):
    """Embedding model configuration."""
    model: str = Field(..., description="Embedding model identifier")
    dimensions: Optional[int] = None
    batch_size: int = Field(default=100, ge=1, le=2048)


class RetrieverConfig(BaseIntegrationConfig):
    """Retriever configuration."""
    retriever_type: str = Field(default="vector", description="vector, hybrid, bm25, custom")
    search_kwargs: Dict[str, Any] = Field(default_factory=dict)
    reranker: Optional[str] = None
    reranker_config: Dict[str, Any] = Field(default_factory=dict)


class TextSplitterConfig(BaseIntegrationConfig):
    """Text splitter configuration."""
    splitter_type: str = Field(default="recursive", description="recursive, markdown, html, code, semantic")
    chunk_size: int = Field(default=1000, ge=100)
    chunk_overlap: int = Field(default=200, ge=0)
    separators: Optional[List[str]] = None


class DocumentLoaderConfig(BaseIntegrationConfig):
    """Document loader configuration."""
    loader_type: str = Field(..., description="pdf, json, text, html, code, directory, etc.")
    glob_pattern: Optional[str] = None
    recursive: bool = True


class RAGConfig(BaseModel):
    """RAG pipeline configuration."""
    embedding: EmbeddingConfig
    vector_store: str = Field(..., description="Reference to vector_store route name")
    retriever: RetrieverConfig
    text_splitter: TextSplitterConfig
    document_loaders: List[DocumentLoaderConfig] = Field(default_factory=list)


class SandboxConfig(BaseIntegrationConfig):
    """Sandbox configuration."""
    sandbox_type: str = Field(..., description="daytona, modal, e2b, runloop, agentcore, etc.")
    resources: Dict[str, Any] = Field(default_factory=dict, description="cpu, memory, disk, gpu")
    timeout: int = Field(default=300, description="Default execution timeout in seconds")


class ConsensusConfig(BaseModel):
    """Consensus configuration for multi-instance agreement."""
    enabled: bool = Field(default=False, description="Enable consensus")
    strategy: str = Field(default="majority", description="Consensus strategy: majority, weighted, threshold, unanimous, judge")
    instances: int = Field(default=3, ge=2, le=5, description="Number of instances to run")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Agreement threshold for threshold/unanimous strategies")
    temperatures: Optional[List[float]] = Field(default=None, description="Temperature values for each instance (optional)")


class BackendConfig(BaseIntegrationConfig):
    """Deep Agents backend configuration."""
    backend_type: str = Field(..., description="state, filesystem, store, contexthub, sandbox, localshell, composite")
    routes: Dict[str, str] = Field(default_factory=dict, description="For composite backend")


class SkillConfig(BaseIntegrationConfig):
    """Skill configuration."""
    skill_id: str = Field(..., description="Reference to skill in registry")
    max_iterations: int = Field(default=5, ge=1, le=50)
    timeout_seconds: int = Field(default=300, ge=30)
    allowed_integrations: List[str] = Field(default_factory=list)


class IntegrationsConfig(BaseModel):
    """All user-configurable integrations."""
    chat_models: List[ChatModelConfig] = Field(default_factory=list)
    tools: List[ToolConfig] = Field(default_factory=list)
    middleware: List[MiddlewareConfig] = Field(default_factory=list)
    persistence: PersistenceConfig = Field(default_factory=PersistenceConfig)
    rag: Optional[RAGConfig] = None
    sandboxes: List[SandboxConfig] = Field(default_factory=list)
    backends: List[BackendConfig] = Field(default_factory=list)
    skills: List[SkillConfig] = Field(default_factory=list)
    
    # Plugin registry (static registration for custom/private plugins)
    plugins: List[PluginMetadata] = Field(default_factory=list)


# =============================================================================
# Main Configuration
# =============================================================================

class AgenticAIConfig(BaseModel):
    """Root configuration for AgenticAI SDK."""
    platform: PlatformConfig = Field(default_factory=PlatformConfig)
    integrations: IntegrationsConfig = Field(default_factory=IntegrationsConfig)

    # Legacy fields for backward compatibility
    chat_models: Optional[Dict[str, ChatModelConfig]] = Field(default=None, exclude=True)
    database_routes: Optional[Dict[str, DatabaseRouteConfig]] = Field(default=None, exclude=True)

    # Runtime overrides (populated from JSON at request time)
    runtime_overrides: Dict[str, Any] = Field(default_factory=dict, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def _handle_legacy_fields(cls, data: Any) -> Any:
        """Handle legacy chat_models and database_routes dict format."""
        if isinstance(data, dict):
            # Convert legacy chat_models dict to integrations.chat_models list
            if "chat_models" in data and data["chat_models"]:
                chat_models = data.pop("chat_models")
                if isinstance(chat_models, dict):
                    data.setdefault("integrations", {})
                    data["integrations"].setdefault("chat_models", [])
                    for k, v in chat_models.items():
                        if isinstance(v, dict):
                            v.setdefault("id", k)
                        elif hasattr(v, "id") and not v.id:
                            v.id = k
                        data["integrations"]["chat_models"].append(v)

            # Convert legacy database_routes dict to integrations.persistence
            if "database_routes" in data and data["database_routes"]:
                db_routes = data.pop("database_routes")
                if isinstance(db_routes, dict):
                    data.setdefault("integrations", {})
                    data["integrations"].setdefault("persistence", {})
                    # Map legacy keys to persistence fields
                    purpose_map = {
                        "checkpointer": "checkpointer",
                        "checkpointer": "checkpointer",
                        "store": "store",
                        "vector": "vector_store",
                        "vector_store": "vector_store",
                        "analytics": "analytics",
                        "audit_log": "audit_log",
                        "audit": "audit_log",
                        "cache": "cache",
                        "rate_limit": "rate_limit",
                    }
                    for k, v in db_routes.items():
                        if isinstance(v, dict):
                            v.setdefault("name", k)
                        mapped_key = purpose_map.get(k, k)
                        data["integrations"]["persistence"][mapped_key] = v

        return data

    @model_validator(mode="after")
    def validate_integrations(self) -> "AgenticAIConfig":
        """Validate integration configurations."""
        # Ensure at least one chat model
        if not self.integrations.chat_models:
            raise ValueError("At least one chat model must be configured")
        
        # Validate database routes have unique names per purpose
        routes = []
        if self.integrations.persistence.checkpointer:
            routes.append(("checkpointer", self.integrations.persistence.checkpointer))
        if self.integrations.persistence.store:
            routes.append(("store", self.integrations.persistence.store))
        if self.integrations.persistence.vector_store:
            routes.append(("vector_store", self.integrations.persistence.vector_store))
        if self.integrations.persistence.analytics:
            routes.append(("analytics", self.integrations.persistence.analytics))
        if self.integrations.persistence.audit_log:
            routes.append(("audit_log", self.integrations.persistence.audit_log))
        if self.integrations.persistence.cache:
            routes.append(("cache", self.integrations.persistence.cache))
        if self.integrations.persistence.rate_limit:
            routes.append(("rate_limit", self.integrations.persistence.rate_limit))
        
        for purpose, route in routes:
            if route.purpose.value != purpose:
                raise ValueError(
                    f"Database route '{route.name}' has purpose '{route.purpose.value}' "
                    f"but is configured as '{purpose}'"
                )
        
        return self
    
    def get_chat_model(self, model_id: str) -> Optional[ChatModelConfig]:
        """Get chat model config by ID."""
        for m in self.integrations.chat_models:
            if m.id == model_id and m.enabled:
                return m
        return None
    
    def get_primary_chat_model(self) -> Optional[ChatModelConfig]:
        """Get highest priority enabled chat model."""
        enabled = [m for m in self.integrations.chat_models if m.enabled]
        if not enabled:
            return None
        return min(enabled, key=lambda m: m.priority)
    
    def get_tools(self) -> List[ToolConfig]:
        """Get all enabled tool configs."""
        return [t for t in self.integrations.tools if t.enabled]
    
    def get_middleware(self) -> List[MiddlewareConfig]:
        """Get all enabled middleware configs sorted by priority."""
        enabled = [m for m in self.integrations.middleware if m.enabled]
        return sorted(enabled, key=lambda m: m.priority)
    
    def get_database_route(self, purpose: Union[DatabasePurpose, str]) -> Optional[DatabaseRouteConfig]:
        """Get database route by purpose."""
        if isinstance(purpose, str):
            # Convert string to DatabasePurpose enum
            purpose_map = {
                "checkpointer": DatabasePurpose.CHECKPOINTER,
                "store": DatabasePurpose.STORE,
                "vector": DatabasePurpose.VECTOR_STORE,
                "vector_store": DatabasePurpose.VECTOR_STORE,
                "analytics": DatabasePurpose.ANALYTICS,
                "audit_log": DatabasePurpose.AUDIT_LOG,
                "audit": DatabasePurpose.AUDIT_LOG,
                "cache": DatabasePurpose.CACHE,
                "rate_limit": DatabasePurpose.RATE_LIMIT,
            }
            purpose = purpose_map.get(purpose, purpose)
            if isinstance(purpose, str):
                try:
                    purpose = DatabasePurpose(purpose)
                except ValueError:
                    return None
        route_map = {
            DatabasePurpose.CHECKPOINTER: self.integrations.persistence.checkpointer,
            DatabasePurpose.STORE: self.integrations.persistence.store,
            DatabasePurpose.VECTOR_STORE: self.integrations.persistence.vector_store,
            DatabasePurpose.ANALYTICS: self.integrations.persistence.analytics,
            DatabasePurpose.AUDIT_LOG: self.integrations.persistence.audit_log,
            DatabasePurpose.CACHE: self.integrations.persistence.cache,
            DatabasePurpose.RATE_LIMIT: self.integrations.persistence.rate_limit,
        }
        route = route_map.get(purpose)
        if route and route.enabled:
            return route
        return None
    
    def apply_runtime_overrides(self, overrides: Dict[str, Any]) -> "AgenticAIConfig":
        """Apply runtime overrides (from JSON request) and return new config."""
        # Deep merge overrides into config
        import copy
        new_config = copy.deepcopy(self)
        new_config.runtime_overrides = overrides
        
        # Apply to integrations
        if "chat_models" in overrides:
            for override in overrides["chat_models"]:
                model_id = override.get("id")
                if model_id:
                    model = new_config.get_chat_model(model_id)
                    if model:
                        model.config.update(override.get("config", {}))
                        if "model" in override:
                            model.model = override["model"]
                        if "temperature" in override:
                            model.temperature = override["temperature"]
        
        if "tools" in overrides:
            for override in overrides["tools"]:
                tool_id = override.get("id")
                if tool_id:
                    for tool in new_config.integrations.tools:
                        if tool.id == tool_id:
                            tool.config.update(override.get("config", {}))
        
        return new_config
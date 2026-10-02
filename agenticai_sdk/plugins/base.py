"""Base plugin classes and types for AgenticAI SDK."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel, Field


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


class FeatureFlags(BaseModel):
    """Feature support flags for integrations."""
    stream: bool = True
    tools: bool = True
    structured_output: bool = True
    multimodal: bool = False


class HealthStatus(str, Enum):
    """Health check result for a plugin."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class PluginMetadata:
    """Metadata for a plugin/integration provider."""
    type: IntegrationType
    provider: str
    name: str
    description: str
    package_name: str
    version: str
    features: FeatureFlags = field(default_factory=FeatureFlags)
    config_schema: str = ""  # Fully qualified class name
    docs_url: str = ""
    downloads_per_month: int = 0
    tags: List[str] = field(default_factory=list)
    entry_point: Optional[str] = None


class IntegrationPlugin(ABC):
    """Base class for all integration plugins.
    
    Plugins are registered via entry points or explicit registration.
    Each plugin handles a specific provider for a given integration type.
    """
    
    def __init__(self, metadata: PluginMetadata):
        self.metadata = metadata
        self._config_schema: Optional[Type[BaseModel]] = None
    
    @property
    def type(self) -> IntegrationType:
        return self.metadata.type
    
    @property
    def provider(self) -> str:
        return self.metadata.provider
    
    @property
    def config_schema(self) -> Type[BaseModel]:
        """Get the Pydantic config schema for this plugin."""
        if self._config_schema is None and self.metadata.config_schema:
            self._config_schema = self._import_config_schema(self.metadata.config_schema)
        return self._config_schema
    
    def _import_config_schema(self, schema_path: str) -> Type[BaseModel]:
        """Import config schema class from string path."""
        module_path, class_name = schema_path.rsplit(".", 1)
        module = __import__(module_path, fromlist=[class_name])
        return getattr(module, class_name)
    
    @abstractmethod
    def create_instance(self, config: BaseModel) -> Any:
        """Create and return the integration instance.
        
        Args:
            config: Validated configuration for this provider.
            
        Returns:
            The initialized integration instance (e.g., ChatOpenAI, TavilyTool, etc.)
        """
        pass
    
    def validate_config(self, config_dict: Dict[str, Any]) -> BaseModel:
        """Validate configuration against plugin's schema."""
        schema = self.config_schema
        if schema is None:
            raise ValueError(f"No config schema defined for {self.provider}")
        return schema(**config_dict)
    
    def health_check(self, config: BaseModel) -> HealthStatus:
        """Check health of the integration with given config.
        
        Default implementation returns unknown. Override for actual checks.
        """
        return HealthStatus(
            healthy=True,
            message="Health check not implemented",
            details={"provider": self.provider, "type": self.type.value},
        )
    
    def get_features(self) -> FeatureFlags:
        """Get feature flags for this plugin."""
        return self.metadata.features


class ChatModelPlugin(IntegrationPlugin):
    """Plugin for chat model providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.CHAT_MODEL:
            raise ValueError("ChatModelPlugin must have type CHAT_MODEL")


class ToolPlugin(IntegrationPlugin):
    """Plugin for tool/toolkit providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.TOOL:
            raise ValueError("ToolPlugin must have type TOOL")


class MiddlewarePlugin(IntegrationPlugin):
    """Plugin for middleware providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.MIDDLEWARE:
            raise ValueError("MiddlewarePlugin must have type MIDDLEWARE")


class SandboxPlugin(IntegrationPlugin):
    """Plugin for sandbox providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.SANDBOX:
            raise ValueError("SandboxPlugin must have type SANDBOX")


class CheckpointerPlugin(IntegrationPlugin):
    """Plugin for checkpointer providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.CHECKPOINTER:
            raise ValueError("CheckpointerPlugin must have type CHECKPOINTER")


class StorePlugin(IntegrationPlugin):
    """Plugin for store (long-term memory) providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.STORE:
            raise ValueError("StorePlugin must have type STORE")


class VectorStorePlugin(IntegrationPlugin):
    """Plugin for vector store providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.VECTOR_STORE:
            raise ValueError("VectorStorePlugin must have type VECTOR_STORE")


class EmbeddingPlugin(IntegrationPlugin):
    """Plugin for embedding model providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.EMBEDDING:
            raise ValueError("EmbeddingPlugin must have type EMBEDDING")


class RetrieverPlugin(IntegrationPlugin):
    """Plugin for retriever providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.RETRIEVER:
            raise ValueError("RetrieverPlugin must have type RETRIEVER")


class TextSplitterPlugin(IntegrationPlugin):
    """Plugin for text splitter providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.TEXT_SPLITTER:
            raise ValueError("TextSplitterPlugin must have type TEXT_SPLITTER")


class DocumentLoaderPlugin(IntegrationPlugin):
    """Plugin for document loader providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.DOCUMENT_LOADER:
            raise ValueError("DocumentLoaderPlugin must have type DOCUMENT_LOADER")


class BackendPlugin(IntegrationPlugin):
    """Plugin for Deep Agents backend providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.BACKEND:
            raise ValueError("BackendPlugin must have type BACKEND")


class SkillPlugin(IntegrationPlugin):
    """Plugin for skill providers."""
    
    def __init__(self, metadata: PluginMetadata):
        super().__init__(metadata)
        if metadata.type != IntegrationType.SKILL:
            raise ValueError("SkillPlugin must have type SKILL")


# Plugin factory functions
PLUGIN_CLASSES: Dict[IntegrationType, Type[IntegrationPlugin]] = {
    IntegrationType.CHAT_MODEL: ChatModelPlugin,
    IntegrationType.TOOL: ToolPlugin,
    IntegrationType.MIDDLEWARE: MiddlewarePlugin,
    IntegrationType.SANDBOX: SandboxPlugin,
    IntegrationType.CHECKPOINTER: CheckpointerPlugin,
    IntegrationType.STORE: StorePlugin,
    IntegrationType.VECTOR_STORE: VectorStorePlugin,
    IntegrationType.EMBEDDING: EmbeddingPlugin,
    IntegrationType.RETRIEVER: RetrieverPlugin,
    IntegrationType.TEXT_SPLITTER: TextSplitterPlugin,
    IntegrationType.DOCUMENT_LOADER: DocumentLoaderPlugin,
    IntegrationType.BACKEND: BackendPlugin,
    IntegrationType.SKILL: SkillPlugin,
}


def create_plugin(metadata: PluginMetadata) -> IntegrationPlugin:
    """Create plugin instance from metadata."""
    plugin_class = PLUGIN_CLASSES.get(metadata.type)
    if plugin_class is None:
        raise ValueError(f"No plugin class for type: {metadata.type}")
    return plugin_class(metadata)
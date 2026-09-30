"""Plugin registry for AgenticAI SDK.

Central registry for all integration plugins with dynamic discovery.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import logging
from typing import Any, Dict, List, Optional, Set, Type

import structlog

from .base import (
    IntegrationPlugin,
    IntegrationType,
    PluginMetadata,
    FeatureFlags,
    HealthStatus,
    create_plugin,
)
from ..config.schemas import PluginMetadata as ConfigPluginMetadata

logger = structlog.get_logger(__name__)


class IntegrationRegistry:
    """Central registry for all integration plugins.
    
    Supports:
    - Entry point auto-discovery (pip installed packages)
    - Explicit YAML registration (custom/private plugins)
    - Plugin metadata management
    - Instance creation with validated config
    """
    
    def __init__(self):
        self._plugins: Dict[str, IntegrationPlugin] = {}  # key: "{type}:{provider}"
        self._metadata: Dict[str, PluginMetadata] = {}
        self._entry_points_loaded = False
        self._explicit_plugins: List[PluginMetadata] = []
    
    def _make_key(self, type: IntegrationType, provider: str) -> str:
        return f"{type.value}:{provider}"
    
    def register_plugin(self, plugin: IntegrationPlugin) -> None:
        """Register a plugin instance."""
        key = self._make_key(plugin.type, plugin.provider)
        if key in self._plugins:
            logger.warning("plugin_already_registered", key=key, provider=plugin.provider)
        self._plugins[key] = plugin
        self._metadata[key] = plugin.metadata
        logger.info("plugin_registered", key=key, provider=plugin.provider, type=plugin.type.value)
    
    def register_metadata(self, metadata: PluginMetadata) -> None:
        """Register plugin metadata (for later lazy loading)."""
        key = self._make_key(metadata.type, metadata.provider)
        self._metadata[key] = metadata
        logger.debug("plugin_metadata_registered", key=key, provider=metadata.provider)
    
    def get_plugin(self, type: IntegrationType, provider: str) -> Optional[IntegrationPlugin]:
        """Get plugin instance, creating it lazily if needed."""
        key = self._make_key(type, provider)
        
        # Return cached instance
        if key in self._plugins:
            return self._plugins[key]
        
        # Try to create from metadata
        if key in self._metadata:
            metadata = self._metadata[key]
            plugin = create_plugin(metadata)
            self._plugins[key] = plugin
            return plugin
        
        return None
    
    def get_metadata(self, type: IntegrationType, provider: str) -> Optional[PluginMetadata]:
        """Get plugin metadata without creating instance."""
        key = self._make_key(type, provider)
        return self._metadata.get(key)
    
    def list_available(self, type: Optional[IntegrationType] = None) -> List[PluginMetadata]:
        """List all available plugin metadata."""
        results = []
        for key, metadata in self._metadata.items():
            if type is None or metadata.type == type:
                results.append(metadata)
        return results
    
    def create_instance(
        self,
        type: IntegrationType,
        provider: str,
        config: Dict[str, Any],
    ) -> Any:
        """Create integration instance with validated config."""
        plugin = self.get_plugin(type, provider)
        if plugin is None:
            raise ValueError(
                f"Plugin not found: {type.value}:{provider}. "
                f"Available: {[m.provider for m in self.list_available(type)]}"
            )
        
        # Validate config
        validated_config = plugin.validate_config(config)
        
        # Create instance
        return plugin.create_instance(validated_config)
    
    def health_check(
        self,
        type: IntegrationType,
        provider: str,
        config: Dict[str, Any],
    ) -> HealthStatus:
        """Run health check for a plugin."""
        plugin = self.get_plugin(type, provider)
        if plugin is None:
            return HealthStatus(
                healthy=False,
                message=f"Plugin not found: {type.value}:{provider}",
            )
        
        validated_config = plugin.validate_config(config)
        return plugin.health_check(validated_config)
    
    def load_entry_points(self, force: bool = False) -> int:
        """Load plugins from entry points.
        
        Entry point group: "agenticai.plugins"
        """
        if self._entry_points_loaded and not force:
            return 0
        
        count = 0
        try:
            eps = importlib.metadata.entry_points(group="agenticai.plugins")
            for ep in eps:
                try:
                    metadata = ep.load()
                    if isinstance(metadata, PluginMetadata):
                        self.register_metadata(metadata)
                        count += 1
                    else:
                        logger.warning(
                            "invalid_entry_point",
                            entry_point=ep.name,
                            type=type(metadata),
                        )
                except Exception as e:
                    logger.error("entry_point_load_failed", entry_point=ep.name, error=str(e))
        except Exception as e:
            logger.warning("entry_points_load_failed", error=str(e))
        
        self._entry_points_loaded = True
        logger.info("entry_points_loaded", count=count)
        return count
    
    def register_explicit_plugins(self, plugins: List[ConfigPluginMetadata]) -> int:
        """Register plugins from explicit configuration (YAML)."""
        count = 0
        for plugin_meta in plugins:
            try:
                # Convert config schema to plugin metadata
                metadata = PluginMetadata(
                    type=IntegrationType(plugin_meta.type),
                    provider=plugin_meta.provider,
                    name=plugin_meta.name,
                    description=plugin_meta.description,
                    package_name=plugin_meta.package_name,
                    version=plugin_meta.version,
                    features=plugin_meta.features,
                    config_schema=plugin_meta.config_schema,
                    docs_url=plugin_meta.docs_url,
                    downloads_per_month=plugin_meta.downloads_per_month,
                    tags=plugin_meta.tags,
                )
                self.register_metadata(metadata)
                count += 1
            except Exception as e:
                logger.error(
                    "explicit_plugin_register_failed",
                    provider=plugin_meta.provider,
                    error=str(e),
                )
        
        logger.info("explicit_plugins_registered", count=count)
        return count
    
    def discover_installed_packages(self) -> List[PluginMetadata]:
        """Discover LangChain integration packages installed in environment."""
        discovered = []
        
        # Known LangChain integration packages
        known_packages = {
            # Chat models
            "langchain-openai": ("chat_model", "openai"),
            "langchain-anthropic": ("chat_model", "anthropic"),
            "langchain-google-genai": ("chat_model", "google_genai"),
            "langchain-google-vertexai": ("chat_model", "google_vertex"),
            "langchain-aws": ("chat_model", "bedrock"),
            "langchain-groq": ("chat_model", "groq"),
            "langchain-mistralai": ("chat_model", "mistral"),
            "langchain-cohere": ("chat_model", "cohere"),
            "langchain-xai": ("chat_model", "xai"),
            "langchain-deepseek": ("chat_model", "deepseek"),
            "langchain-nvidia-ai-endpoints": ("chat_model", "nvidia"),
            "langchain-together": ("chat_model", "together"),
            "langchain-fireworks": ("chat_model", "fireworks"),
            "langchain-databricks": ("chat_model", "databricks"),
            "langchain-ibm": ("chat_model", "watsonx"),
            "langchain-perplexity": ("chat_model", "perplexity"),
            "langchain-cerebras": ("chat_model", "cerebras"),
            "langchain-huggingface": ("chat_model", "huggingface"),
            "langchain-litellm": ("chat_model", "litellm"),
            "langchain-openrouter": ("chat_model", "openrouter"),
            "langchain-ollama": ("chat_model", "ollama"),
            "langchain-azure-ai": ("chat_model", "azure_ai"),
            
            # Embeddings
            "langchain-openai": ("embedding", "openai"),
            "langchain-google-genai": ("embedding", "google_genai"),
            "langchain-ollama": ("embedding", "ollama"),
            "langchain-cohere": ("embedding", "cohere"),
            "langchain-mistralai": ("embedding", "mistral"),
            "langchain-nomic": ("embedding", "nomic"),
            "langchain-voyageai": ("embedding", "voyage"),
            "langchain-ibm": ("embedding", "watsonx"),
            
            # Vector stores
            "langchain-qdrant": ("vector_store", "qdrant"),
            "langchain-pinecone": ("vector_store", "pinecone"),
            "langchain-chroma": ("vector_store", "chroma"),
            "langchain-weaviate": ("vector_store", "weaviate"),
            "langchain-milvus": ("vector_store", "milvus"),
            "langchain-elasticsearch": ("vector_store", "elasticsearch"),
            "langchain-postgres": ("vector_store", "pgvector"),
            "langchain-astradb": ("vector_store", "astradb"),
            "langchain-redis": ("vector_store", "redis"),
            "langchain-mongodb": ("vector_store", "mongodb"),
            
            # Tools
            "langchain-tavily": ("tool", "tavily"),
            "langchain-composio": ("tool", "composio"),
            "langchain-google-community": ("tool", "google"),
            "langchain-exa": ("tool", "exa"),
            
            # Checkpointers
            "langgraph-checkpoint-postgres": ("checkpointer", "postgres"),
            "langgraph-checkpoint-sqlite": ("checkpointer", "sqlite"),
            "langgraph-checkpoint-redis": ("checkpointer", "redis"),
            "langgraph-checkpoint-mongodb": ("checkpointer", "mongodb"),
        }
        
        for package_name, (itype, provider) in known_packages.items():
            try:
                dist = importlib.metadata.distribution(package_name)
                version = dist.version
                
                # Try to get download count from PyPI (cached)
                downloads = self._get_download_count(package_name)
                
                metadata = PluginMetadata(
                    type=IntegrationType(itype),
                    provider=provider,
                    name=package_name.replace("langchain-", "").replace("langgraph-", "").replace("-", " ").title(),
                    description=f"{provider} integration via {package_name}",
                    package_name=package_name,
                    version=version,
                    features=FeatureFlags(
                        stream=True,
                        tools=True,
                        structured_output=True,
                        multimodal=False,
                    ),
                    config_schema=self._get_config_schema(package_name, itype),
                    downloads_per_month=downloads,
                    tags=["langchain", "official"],
                )
                discovered.append(metadata)
            except importlib.metadata.PackageNotFoundError:
                continue
            except Exception as e:
                logger.debug("package_discover_failed", package=package_name, error=str(e))
        
        return discovered
    
    def _get_download_count(self, package_name: str) -> int:
        """Get download count from PyPI (simplified - would use cached data in production)."""
        # In production, this would query PyPI stats API or use cached data
        return 0
    
    def _get_config_schema(self, package_name: str, itype: str) -> str:
        """Get config schema class path for a package."""
        # Map to actual config schema classes
        schema_map = {
            "langchain-openai": "agenticai_sdk.integrations.openai.OpenAIConfig",
            "langchain-anthropic": "agenticai_sdk.integrations.anthropic.AnthropicConfig",
            "langchain-google-genai": "agenticai_sdk.integrations.google.GoogleGenAIConfig",
            "langchain-google-vertexai": "agenticai_sdk.integrations.google.VertexAIConfig",
            "langchain-aws": "agenticai_sdk.integrations.aws.BedrockConfig",
            "langchain-groq": "agenticai_sdk.integrations.groq.GroqConfig",
            "langchain-mistralai": "agenticai_sdk.integrations.mistral.MistralConfig",
            "langchain-cohere": "agenticai_sdk.integrations.cohere.CohereConfig",
            "langchain-xai": "agenticai_sdk.integrations.xai.XAIConfig",
            "langchain-deepseek": "agenticai_sdk.integrations.deepseek.DeepSeekConfig",
            "langchain-nvidia-ai-endpoints": "agenticai_sdk.integrations.nvidia.NVIDIAConfig",
            "langchain-together": "agenticai_sdk.integrations.together.TogetherConfig",
            "langchain-fireworks": "agenticai_sdk.integrations.fireworks.FireworksConfig",
            "langchain-databricks": "agenticai_sdk.integrations.databricks.DatabricksConfig",
            "langchain-ibm": "agenticai_sdk.integrations.ibm.WatsonXConfig",
            "langchain-perplexity": "agenticai_sdk.integrations.perplexity.PerplexityConfig",
            "langchain-cerebras": "agenticai_sdk.integrations.cerebras.CerebrasConfig",
            "langchain-huggingface": "agenticai_sdk.integrations.huggingface.HuggingFaceConfig",
            "langchain-litellm": "agenticai_sdk.integrations.litellm.LiteLLMConfig",
            "langchain-openrouter": "agenticai_sdk.integrations.openrouter.OpenRouterConfig",
            "langchain-ollama": "agenticai_sdk.integrations.ollama.OllamaConfig",
            "langchain-azure-ai": "agenticai_sdk.integrations.azure.AzureAIConfig",
            
            # Embeddings
            "langchain-qdrant": "agenticai_sdk.integrations.qdrant.QdrantVectorStoreConfig",
            "langchain-pinecone": "agenticai_sdk.integrations.pinecone.PineconeVectorStoreConfig",
            "langchain-chroma": "agenticai_sdk.integrations.chroma.ChromaVectorStoreConfig",
            
            # Tools
            "langchain-tavily": "agenticai_sdk.integrations.tavily.TavilyConfig",
            "langchain-composio": "agenticai_sdk.integrations.composio.ComposioConfig",
        }
        
        return schema_map.get(package_name, "agenticai_sdk.config.schemas.BaseIntegrationConfig")


# Global registry instance
_global_registry: Optional[IntegrationRegistry] = None


def get_global_registry() -> IntegrationRegistry:
    """Get global integration registry instance."""
    global _global_registry
    if _global_registry is None:
        _global_registry = IntegrationRegistry()
        _global_registry.load_entry_points()
        _global_registry.register_metadata_from_packages()
    return _global_registry


def register_metadata_from_packages(self) -> None:
    """Discover and register metadata from installed packages."""
    discovered = self.discover_installed_packages()
    for metadata in discovered:
        self.register_metadata(metadata)


# Monkey-patch the method
IntegrationRegistry.register_metadata_from_packages = register_metadata_from_packages


def reset_global_registry() -> None:
    """Reset global registry (for testing)."""
    global _global_registry
    _global_registry = None
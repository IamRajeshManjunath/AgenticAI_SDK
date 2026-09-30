"""RAG Pipeline Factories for AgenticAI SDK."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agenticai_sdk.plugins import get_global_registry, IntegrationType

import structlog

logger = structlog.get_logger(__name__)


class EmbeddingFactory:
    """Factory for creating embedding model instances."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
    
    def create(self, config: Dict[str, Any]) -> Any:
        """Create embedding model from config."""
        provider = config.get("provider")
        if not provider:
            raise ValueError("Embedding config must include 'provider'")
        
        plugin = self._registry.get_plugin(IntegrationType.EMBEDDING, provider)
        if not plugin:
            raise ValueError(f"No embedding plugin for provider: {provider}")
        
        return plugin.create_instance(config)
    
    def create_from_config(self, embedding_config) -> Any:
        """Create from EmbeddingConfig object."""
        config_dict = embedding_config.model_dump()
        return self.create(config_dict)
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available embedding providers."""
        plugins = self._registry.list_available(IntegrationType.EMBEDDING)
        return [
            {
                "provider": p.provider,
                "name": p.name,
                "description": p.description,
                "package": p.package_name,
                "version": p.version,
                "downloads_per_month": p.downloads_per_month,
            }
            for p in plugins
        ]


class VectorStoreFactory:
    """Factory for creating vector store instances."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
    
    def create(self, config: Dict[str, Any], embedding=None) -> Any:
        """Create vector store from config."""
        provider = config.get("provider")
        if not provider:
            raise ValueError("Vector store config must include 'provider'")
        
        plugin = self._registry.get_plugin(IntegrationType.VECTOR_STORE, provider)
        if not plugin:
            raise ValueError(f"No vector store plugin for provider: {provider}")
        
        config_dict = config.copy()
        if embedding:
            config_dict["embedding"] = embedding
        
        return plugin.create_instance(config_dict)
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available vector store providers."""
        plugins = self._registry.list_available(IntegrationType.VECTOR_STORE)
        return [
            {
                "provider": p.provider,
                "name": p.name,
                "description": p.description,
                "package": p.package_name,
                "version": p.version,
                "features": {
                    "async": True,
                    "filtering": True,
                    "score_search": True,
                },
                "downloads_per_month": p.downloads_per_month,
            }
            for p in plugins
        ]


class RetrieverFactory:
    """Factory for creating retriever instances."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
    
    def create(self, config: Dict[str, Any], vector_store=None) -> Any:
        """Create retriever from config."""
        provider = config.get("provider", "vector")
        
        if provider == "vector":
            # Use vector store as retriever
            if not vector_store:
                raise ValueError("Vector store required for vector retriever")
            return vector_store.as_retriever(
                search_kwargs=config.get("search_kwargs", {})
            )
        
        plugin = self._registry.get_plugin(IntegrationType.RETRIEVER, provider)
        if not plugin:
            raise ValueError(f"No retriever plugin for provider: {provider}")
        
        config_dict = config.copy()
        if vector_store:
            config_dict["vector_store"] = vector_store
        
        return plugin.create_instance(config_dict)
    
    def create_hybrid(self, vector_retriever, bm25_retriever, weights=None) -> Any:
        """Create hybrid retriever combining vector and keyword search."""
        from langchain.retrievers import EnsembleRetriever
        
        retrievers = [vector_retriever]
        if bm25_retriever:
            retrievers.append(bm25_retriever)
        
        if weights is None:
            weights = [0.7, 0.3] if len(retrievers) == 2 else [1.0]
        
        return EnsembleRetriever(retrievers=retrievers, weights=weights)
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available retriever providers."""
        plugins = self._registry.list_available(IntegrationType.RETRIEVER)
        return [
            {
                "provider": p.provider,
                "name": p.name,
                "description": p.description,
                "package": p.package_name,
                "version": p.version,
                "downloads_per_month": p.downloads_per_month,
            }
            for p in plugins
        ]


class TextSplitterFactory:
    """Factory for creating text splitter instances."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
    
    def create(self, config: Dict[str, Any]) -> Any:
        """Create text splitter from config."""
        provider = config.get("provider", "recursive")
        
        if provider == "recursive":
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            return RecursiveCharacterTextSplitter(
                chunk_size=config.get("chunk_size", 1000),
                chunk_overlap=config.get("chunk_overlap", 200),
                separators=config.get("separators"),
            )
        elif provider == "markdown":
            from langchain_text_splitters import MarkdownTextSplitter
            return MarkdownTextSplitter(
                chunk_size=config.get("chunk_size", 1000),
                chunk_overlap=config.get("chunk_overlap", 200),
            )
        elif provider == "html":
            from langchain_text_splitters import HTMLTextSplitter
            return HTMLTextSplitter(
                chunk_size=config.get("chunk_size", 1000),
                chunk_overlap=config.get("chunk_overlap", 200),
            )
        elif provider == "code":
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            return RecursiveCharacterTextSplitter.from_language(
                language=config.get("language", "python"),
                chunk_size=config.get("chunk_size", 1000),
                chunk_overlap=config.get("chunk_overlap", 200),
            )
        elif provider == "semantic":
            from langchain_experimental.text_splitter import SemanticChunker
            # Requires embedding model
            return SemanticChunker(
                embedding_model=config.get("embedding_model"),
                breakpoint_threshold_type=config.get("threshold_type", "percentile"),
                breakpoint_threshold_amount=config.get("threshold_amount", 0.8),
            )
        
        # Try plugin registry
        plugin = self._registry.get_plugin(IntegrationType.TEXT_SPLITTER, provider)
        if plugin:
            return plugin.create_instance(config)
        
        raise ValueError(f"Unknown text splitter provider: {provider}")
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available text splitter providers."""
        return [
            {
                "provider": "recursive",
                "name": "Recursive Character",
                "description": "Recursively splits text by separators",
            },
            {
                "provider": "markdown",
                "name": "Markdown",
                "description": "Splits markdown by headers and structure",
            },
            {
                "provider": "html",
                "name": "HTML",
                "description": "Splits HTML by tags",
            },
            {
                "provider": "code",
                "name": "Code",
                "description": "Splits code by language syntax",
            },
            {
                "provider": "semantic",
                "name": "Semantic",
                "description": "Splits by semantic similarity (requires embedding model)",
            },
        ]


class DocumentLoaderFactory:
    """Factory for creating document loader instances."""
    
    def __init__(self, registry=None):
        self._registry = registry or get_global_registry()
    
    def create(self, config: Dict[str, Any]) -> Any:
        """Create document loader from config."""
        loader_type = config.get("loader_type", "text")
        
        if loader_type == "pdf":
            from langchain_community.document_loaders import PyPDFLoader
            return PyPDFLoader(config.get("file_path"))
        elif loader_type == "text":
            from langchain_community.document_loaders import TextLoader
            return TextLoader(config.get("file_path"), encoding=config.get("encoding", "utf-8"))
        elif loader_type == "json":
            from langchain_community.document_loaders import JSONLoader
            return JSONLoader(
                file_path=config.get("file_path"),
                jq_schema=config.get("jq_schema", "."),
                text_content=config.get("text_content", False),
            )
        elif loader_type == "html":
            from langchain_community.document_loaders import UnstructuredHTMLLoader
            return UnstructuredHTMLLoader(config.get("file_path"))
        elif loader_type == "csv":
            from langchain_community.document_loaders import CSVLoader
            return CSVLoader(config.get("file_path"))
        elif loader_type == "directory":
            from langchain_community.document_loaders import DirectoryLoader
            return DirectoryLoader(
                path=config.get("path"),
                glob=config.get("glob", "**/*"),
                loader_cls=self._get_loader_class(config.get("loader_type", "text")),
            )
        
        raise ValueError(f"Unknown document loader type: {loader_type}")
    
    def _get_loader_class(self, loader_type: str):
        loaders = {
            "text": "langchain_community.document_loaders.TextLoader",
            "pdf": "langchain_community.document_loaders.PyPDFLoader",
            "json": "langchain_community.document_loaders.JSONLoader",
        }
        return loaders.get(loader_type)
    
    def list_available(self) -> List[Dict[str, Any]]:
        """List available document loader types."""
        return [
            {
                "loader_type": "pdf",
                "name": "PDF",
                "description": "Load PDF documents",
            },
            {
                "loader_type": "text",
                "name": "Text",
                "description": "Load plain text files",
            },
            {
                "loader_type": "json",
                "name": "JSON",
                "description": "Load JSON documents",
            },
            {
                "loader_type": "html",
                "name": "HTML",
                "description": "Load HTML documents",
            },
            {
                "loader_type": "csv",
                "name": "CSV",
                "description": "Load CSV files",
            },
            {
                "loader_type": "directory",
                "name": "Directory",
                "description": "Load all files in a directory",
            },
        ]


class RAGPipeline:
    """Complete RAG pipeline orchestrating all components."""
    
    def __init__(self, workspace_id: str, db_session, config):
        from agenticai_sdk.db.factory import DynamicDatabaseFactory
        
        self.workspace_id = workspace_id
        self.db = db_session
        self.config = config
        
        # Initialize factories
        self.embedding_factory = EmbeddingFactory()
        self.vector_store_factory = VectorStoreFactory()
        self.retriever_factory = RetrieverFactory()
        self.text_splitter_factory = TextSplitterFactory()
        self.document_loader_factory = DocumentLoaderFactory()
        
        # Initialize database factory
        self.db_factory = DynamicDatabaseFactory(workspace_id, db_session)
        
        # Create components
        self.embedding = self._create_embedding()
        self.vector_store = self._create_vector_store()
        self.text_splitter = self._create_text_splitter()
        self.retriever = self._create_retriever()
    
    def _create_embedding(self):
        """Create embedding model from config."""
        embedding_config = self.config.rag.embedding
        return self.embedding_factory.create_from_config(embedding_config)
    
    def _create_vector_store(self):
        """Create vector store from config."""
        vector_store_ref = self.config.rag.vector_store
        persistence_config = self.config.integrations.persistence
        
        # Get vector store route from persistence config
        if persistence_config.vector_store:
            route = self.db_factory.get_route("vector_store")  # This needs purpose enum
            # For now, use config directly
            return self.vector_store_factory.create(
                {"provider": persistence_config.vector_store.provider, **persistence_config.vector_store.config},
                embedding=self.embedding
            )
        
        # Fallback to config reference
        return self.vector_store_factory.create(
            {"provider": vector_store_ref, "embedding": self.embedding}
        )
    
    def _create_text_splitter(self):
        """Create text splitter from config."""
        splitter_config = self.config.rag.text_splitter
        return self.text_splitter_factory.create(splitter_config.model_dump())
    
    def _create_retriever(self):
        """Create retriever from config."""
        retriever_config = self.config.rag.retriever
        return self.retriever_factory.create(
            retriever_config.model_dump(),
            vector_store=self.vector_store
        )
    
    def load_documents(self, sources: List[Dict[str, Any]]) -> List[Any]:
        """Load documents from multiple sources."""
        all_docs = []
        for source in sources:
            loader = self.document_loader_factory.create(source)
            docs = loader.load()
            all_docs.extend(docs)
        return all_docs
    
    def split_documents(self, documents: List[Any]) -> List[Any]:
        """Split documents into chunks."""
        return self.text_splitter.split_documents(documents)
    
    def index_documents(self, documents: List[Any]) -> int:
        """Index documents into vector store."""
        # Add to vector store
        self.vector_store.add_documents(documents)
        return len(documents)
    
    def ingest(self, sources: List[Dict[str, Any]]) -> int:
        """Full ingestion pipeline: load -> split -> index."""
        docs = self.load_documents(sources)
        chunks = self.split_documents(docs)
        return self.index_documents(chunks)
    
    def query(self, query: str, k: int = 4) -> List[Any]:
        """Query the RAG pipeline."""
        return self.retriever.invoke(query, k=k)
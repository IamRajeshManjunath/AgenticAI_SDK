"""Deep Agents Integration — wraps the deepagents package for AgenticAI SDK.

Provides a high-level interface to create Deep Agents with AgenticAI configuration,
integrating skills, tools, backends, and observability.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

try:
    from deepagents import create_deep_agent
    from deepagents.backends.protocol import BackendProtocol
    from deepagents.backends.filesystem import FilesystemBackend
    from deepagents.backends.store import StoreBackend
    DEEPAGENTS_AVAILABLE = True
except ImportError:
    create_deep_agent = None
    FilesystemBackend = None
    StoreBackend = None
    BackendProtocol = None
    DEEPAGENTS_AVAILABLE = False

from agenticai_sdk.config.schemas import AgenticAIConfig, SkillsConfig
from agenticai_sdk.plugins.registry import get_global_registry
from agenticai_sdk.runtime.backend_registry import BackendRegistry
from agenticai_sdk.skills.registry import get_skills_registry

logger = structlog.get_logger(__name__)


class DeepAgentIntegrationError(Exception):
    """Raised when Deep Agent integration fails."""
    pass


class DeepAgentsIntegration:
    """Integrates AgenticAI SDK with the deepagents package.
    
    Handles:
    - Skill discovery and loading
    - Tool resolution from plugin registry
    - Backend selection (Filesystem, Store, Composite)
    - Model configuration
    - Deep Agent graph compilation
    """
    
    def __init__(self, config: Optional[AgenticAIConfig] = None, project_root: Optional[Path] = None):
        self.config = config
        self.project_root = project_root or Path.cwd()
        
        # Initialize registries
        self.plugin_registry = get_global_registry()
        
        # Handle skills config
        skills_config = None
        if config and config.platform and config.platform.skills:
            skills_config = config.platform.skills
        self.skills_registry = get_skills_registry(skills_config)
        
        self.backend_registry = BackendRegistry()
        
        # Ensure entry points are loaded
        self.plugin_registry.load_entry_points()
    
    def _check_deepagents_available(self) -> None:
        """Check if deepagents package is available."""
        if not DEEPAGENTS_AVAILABLE:
            raise DeepAgentIntegrationError(
                "deepagents package not installed. Install with: pip install deepagents>=0.7"
            )
    
    def create_backend(self, config: Optional[Dict[str, Any]] = None) -> Optional[BackendProtocol]:
        """Create a deepagents backend based on configuration.
        
        Args:
            config: Backend configuration dict with keys:
                - type: "filesystem", "store", "composite"
                - For filesystem: root_dir, virtual_mode
                - For store: namespace, store (LangGraph store)
                - For composite: backends list
                
        Returns:
            Configured BackendProtocol instance or None if not configured
        """
        self._check_deepagents_available()
        
        backend_config = config or {}
        backend_type = backend_config.get("type", "filesystem")
        
        try:
            if backend_type == "filesystem":
                root_dir = backend_config.get("root_dir", str(self.project_root))
                virtual_mode = backend_config.get("virtual_mode", True)
                return FilesystemBackend(root_dir=root_dir, virtual_mode=virtual_mode)
            
            elif backend_type == "store":
                # StoreBackend requires a LangGraph store
                store = backend_config.get("store")
                namespace = backend_config.get("namespace", "skills")
                if store is None:
                    logger.warning("store_backend_requires_langgraph_store")
                    return None
                return StoreBackend(namespace=namespace, store=store)
            
            elif backend_type == "composite":
                # Composite backend with multiple backends
                from deepagents.backends.composite import CompositeBackend
                backends = []
                for b in backend_config.get("backends", []):
                    b_instance = self.create_backend(b)
                    if b_instance:
                        backends.append(b_instance)
                if backends:
                    return CompositeBackend(backends=backends)
                return None
            
            else:
                logger.warning("unknown_backend_type", type=backend_type)
                return None
                
        except Exception as exc:
            logger.error("backend_creation_failed", type=backend_type, error=str(exc))
            return None
    
    def _resolve_tools(self, tool_ids: List[str], workspace_id: str = "default") -> List[BaseTool]:
        """Resolve tool IDs to LangChain BaseTool instances."""
        tools: List[BaseTool] = []
        
        # Built-in tools from plugin registry
        for tool_id in tool_ids:
            # Skip integration tool IDs that are handled separately
            if tool_id in ("send_slack_message", "send_teams_message", "send_outlook_email", "send_whatsapp_message"):
                continue
            try:
                tool = self.plugin_registry.get_tool(tool_id)
                if tool:
                    tools.append(tool)
            except Exception as exc:
                logger.warning("tool_resolution_failed", tool_id=tool_id, error=str(exc))
        
        # Integration registry tools
        try:
            from agenticai_sdk.runtime.integration_registry import IntegrationRegistry
            registry = IntegrationRegistry(workspace_id=workspace_id)
            integration_tools = registry.get_tools()
            tools.extend(integration_tools)
        except Exception as exc:
            logger.warning("integration_tools_binding_failed", error=str(exc))
        
        return tools
    
    def _resolve_llm(self, llm_config) -> BaseChatModel:
        """Resolve LLM configuration to a LangChain ChatModel."""
        from agenticai_sdk.runtime.llm_factory import LLMClientFactory
        factory = LLMClientFactory()
        return factory.create(llm_config)
    
    def _build_system_prompt(self, agent_config, retrieved_docs: List[Any]) -> str:
        """Build system prompt with RAG context injection."""
        from agenticai_sdk.rag.context_injector import ContextInjector
        
        role_header = f"You are {agent_config.role}.\n\n"
        template_body = agent_config.prompt_template.template_string
        
        if retrieved_docs:
            context_block = ContextInjector.format_documents(retrieved_docs)
            return f"{role_header}{template_body}\n\n{context_block}"
        
        return f"{role_header}{template_body}"
    
    def create_deep_agent(
        self,
        agent_config,
        rag_retriever_map: Optional[Dict[str, Any]] = None,
        schema_config: Optional[Any] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        store: Optional[BaseStore] = None,
    ) -> Callable[[Any], Any]:
        """Create a Deep Agent callable compatible with LangGraph node signatures.
        
        This replaces the custom DeepAgentFactory with the deepagents package.
        
        Args:
            agent_config: AgentNodeConfig with model, tools, prompt, etc.
            rag_retriever_map: Map of RAG source IDs to retriever engines
            schema_config: WorkflowSchema for context
            checkpointer: LangGraph checkpointer for HITL
            store: LangGraph store for long-term memory
            
        Returns:
            Async callable compatible with LangGraph node signature
        """
        self._check_deepagents_available()
        
        # Resolve LLM
        resolved_llm = self._resolve_llm(agent_config.llm)
        
        # Resolve tools
        workspace_id = getattr(schema_config, "workspace_id", "default") if schema_config else "default"
        resolved_tools = self._resolve_tools(agent_config.tools, workspace_id)
        
        # Add sub-agent tools if configured
        if hasattr(agent_config, "sub_agents") and agent_config.sub_agents and schema_config:
            from agenticai_sdk.runtime.orchestrator import SubAgentTool
            agent_map = {a.agent_id: a for a in schema_config.agents} if hasattr(schema_config, "agents") else {}
            for sa_id in agent_config.sub_agents:
                sub_agent_meta = agent_map.get(sa_id)
                role = sub_agent_meta.role if sub_agent_meta else "Specialist"
                delegator = SubAgentTool(
                    sub_agent_id=sa_id,
                    node_registry={},  # Will be populated by orchestrator
                    role=role
                )
                resolved_tools.append(delegator.tool)
        
        # Build system prompt (will be enhanced with RAG at runtime)
        system_prompt = self._build_system_prompt(agent_config, [])
        
        # Get skills from registry
        skill_sources = self.skills_registry.get_deepagents_sources()
        
        # Create deep agent
        try:
            deep_agent = create_deep_agent(
                model=resolved_llm,
                tools=resolved_tools,
                system_prompt=system_prompt,
                skills=skill_sources if skill_sources else None,
                checkpointer=checkpointer,
                store=store,
            )
        except Exception as exc:
            logger.error("deep_agent_creation_failed", error=str(exc))
            raise DeepAgentIntegrationError(f"Failed to create deep agent: {exc}") from exc
        
        # Return wrapped callable for LangGraph
        async def agent_node(state: Dict[str, Any]) -> Dict[str, Any]:
            # Add runtime RAG retrieval if configured
            if rag_retriever_map and agent_config.rag_sources:
                # Runtime RAG would be handled here
                pass
            
            # Invoke deep agent
            result = await deep_agent.ainvoke(state)
            return result
        
        return agent_node


def create_agentic_deep_agent(
    config: AgenticAIConfig,
    project_root: Optional[Path] = None,
    model: str = "anthropic:claude-sonnet-4-6",
    checkpointer: Optional[BaseCheckpointSaver] = None,
    store: Optional[BaseStore] = None,
) -> Any:
    """High-level factory to create a Deep Agent with AgenticAI configuration.
    
    This is the main entry point for creating Deep Agents with full AgenticAI integration.
    
    Args:
        config: AgenticAIConfig with skills, tools, models, etc.
        project_root: Project root directory (defaults to cwd)
        model: Default model string for deepagents
        checkpointer: LangGraph checkpointer
        store: LangGraph store
        
    Returns:
        Compiled Deep Agent graph
    """
    integration = DeepAgentsIntegration(config, project_root)
    
    # Get skill sources
    skills_registry = get_skills_registry(config.platform.skills if config.platform.skills else None, project_root)
    skill_sources = skills_registry.get_deepagents_sources()
    
    # Load plugin registry
    plugin_registry = get_global_registry()
    plugin_registry.load_entry_points()
    
    # Create backend
    backend = None
    if config.integrations.backends:
        backend = integration.create_backend(config.integrations.backends[0].model_dump() if config.integrations.backends else None)
    
    # Get default model
    primary_model = config.get_primary_chat_model()
    model_str = model
    if primary_model:
        model_str = primary_model.model
    
    # Create deep agent
    return create_deep_agent(
        model=model_str,
        tools=[],  # Tools will be bound at runtime
        skills=skill_sources if skill_sources else None,
        checkpointer=checkpointer,
        store=store,
    )
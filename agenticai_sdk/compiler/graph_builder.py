"""Graph Builder - Constructs LangGraph StateGraph from validated workflow schema."""

from __future__ import annotations

import uuid
from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

import structlog
from langgraph.graph import END, StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.store.base import BaseStore

from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.runtime.llm_factory import LLMClientFactory
from agenticai_sdk.runtime.tool_registry import ToolRegistry
from agenticai_sdk.schemas.workflow import WorkflowSchema, AgentNodeConfig, EdgeConfig
from agenticai_sdk.state.workflow_state import WorkflowState
from agenticai_sdk.compiler.semantic_validator import SemanticValidator
from agenticai_sdk.compiler.dependency_resolver import DependencyResolver, CycleDetectedError

logger = structlog.get_logger(__name__)


class GraphBuildError(Exception):
    """Raised when graph construction fails."""
    def __init__(self, errors: List[str]):
        self.errors = errors
        super().__init__(f"Graph build failed: {'; '.join(errors)}")


class GraphBuilder:
    """Builds LangGraph StateGraph from validated WorkflowSchema."""
    
    def __init__(
        self,
        config: AgenticAIConfig,
        workflow: WorkflowSchema,
        llm_factory: Optional[LLMClientFactory] = None,
        tool_registry: Optional[ToolRegistry] = None,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        store: Optional[BaseStore] = None,
    ):
        self.config = config
        self.workflow = workflow
        self.llm_factory = llm_factory or LLMClientFactory()
        self.tool_registry = tool_registry or ToolRegistry()
        self.checkpointer = checkpointer
        self.store = store
        
        self._node_executors: Dict[str, Callable] = {}
        self._compiled_graph: Optional[Any] = None
    
    def build(self) -> StateGraph:
        """Build and return compiled LangGraph StateGraph."""
        # Validate semantic correctness
        self._validate()
        
        # Resolve dependencies
        self.dependency_resolver = DependencyResolver(self.workflow)
        try:
            execution_order = self.dependency_resolver.topological_sort()
        except Exception as e:
            raise GraphBuildError([f"Dependency resolution failed: {e}"])
        
        # Build graph
        graph = StateGraph(WorkflowState)
        
        # Add nodes
        for node_id in execution_order:
            if node_id == "__end__":
                continue
            node_config = self._get_node_config(node_id)
            if node_config:
                executor = self._create_node_executor(node_config)
                graph.add_node(node_id, executor)
        
        # Add edges
        self._add_edges(graph)
        
        # Set entry point
        graph.set_entry_point(self.workflow.entry_point)
        
        # Compile with checkpointer
        self._compiled_graph = graph.compile(
            checkpointer=self.checkpointer,
            store=self.store,
        )
        
        logger.info("graph_compiled", 
                   node_count=len(self._node_executors),
                   entry_point=self.workflow.entry_point)
        
        return self._compiled_graph
    
    def _validate(self) -> None:
        """Run semantic validation."""
        validator = SemanticValidator(self.config)
        errors = validator.validate(self.workflow)
        if errors:
            raise GraphBuildError(errors)
    
    def _get_node_config(self, node_id: str) -> Optional[AgentNodeConfig]:
        """Get node config by ID."""
        for node in self.workflow.agents:
            if node.agent_id == node_id:
                return node
        return None
    
    def _create_node_executor(self, node_config: AgentNodeConfig) -> Callable:
        """Create async executor function for a node."""
        # Resolve LLM
        llm = self.llm_factory.create(node_config.llm)
        
        # Resolve tools
        tools = []
        for tool_id in node_config.tools:
            try:
                tool = self.tool_registry.get_tool(tool_id)
                tools.append(tool)
            except Exception as e:
                logger.warning("tool_resolution_failed", tool_id=tool_id, error=str(e))
        
        # Build system prompt
        system_prompt = self._build_system_prompt(node_config)
        
        async def executor(state: WorkflowState) -> Dict[str, Any]:
            """Execute node with given state."""
            from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
            
            # Build messages for LLM
            messages = state.get("messages", [])
            
            # Add system prompt if not already present
            if not any(isinstance(m, SystemMessage) for m in messages):
                messages = [SystemMessage(content=system_prompt)] + messages
            
            # Invoke LLM with tools
            if tools:
                llm_with_tools = llm.bind_tools(tools)
                response = await llm_with_tools.ainvoke(messages)
            else:
                response = await llm.ainvoke(messages)
            
            # Update state
            new_state = state.copy()
            new_state["messages"] = messages + [response]
            
            # Track token usage
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                new_state["token_usage"] = new_state.get("token_usage", {})
                new_state["token_usage"]["input_tokens"] = new_state["token_usage"].get("input_tokens", 0) + usage.get("input_tokens", 0)
                new_state["token_usage"]["output_tokens"] = new_state["token_usage"].get("output_tokens", 0) + usage.get("output_tokens", 0)
            
            return new_state
        
        return executor
    
    def _build_system_prompt(self, node_config: AgentNodeConfig) -> str:
        """Build system prompt from node configuration."""
        parts = [
            f"Role: {node_config.role}",
            f"Task: {node_config.prompt_template.template_string}",
        ]
        
        # Add tool descriptions
        if node_config.tools:
            tool_descriptions = []
            for tool_id in node_config.tools:
                try:
                    tool = self.tool_registry.get_tool(tool_id)
                    tool_descriptions.append(f"- {tool.name}: {tool.description}")
                except Exception:
                    pass
            if tool_descriptions:
                parts.append("Available tools:\n" + "\n".join(tool_descriptions))
        
        # Add subagent info
        if node_config.sub_agents:
            parts.append(f"Subagents: {', '.join(node_config.sub_agents)}")
        
        return "\n\n".join(parts)
    
    def _add_edges(self, graph: StateGraph) -> None:
        """Add edges to the graph."""
        edge_map: Dict[str, List[EdgeConfig]] = defaultdict(list)
        
        for edge in self.workflow.edges:
            edge_map[edge.source].append(edge)
        
        for source, edges in edge_map.items():
            if source == "__end__":
                continue
            
            if len(edges) == 1:
                edge = edges[0]
                target = edge.target if edge.target != "__end__" else END
                if edge.condition:
                    graph.add_conditional_edges(
                        source,
                        self._create_condition_fn(edge.condition),
                        {edge.target: target, END: END} if edge.target != "__end__" else {END: END}
                    )
                else:
                    graph.add_edge(source, target)
            else:
                # Multiple edges from same source - use conditional routing
                path_map = {}
                for edge in edges:
                    target = edge.target if edge.target != "__end__" else END
                    path_map[edge.target] = target
                
                graph.add_conditional_edges(
                    source,
                    self._create_multi_condition_fn(edges),
                    path_map
                )
    
    def _create_condition_fn(self, condition: str) -> Callable[[WorkflowState], str]:
        """Create condition evaluation function."""
        def condition_fn(state: WorkflowState) -> str:
            # Simple condition evaluation
            try:
                local_vars = {"state": state}
                result = eval(condition, {"__builtins__": {}}, local_vars)
                return "true" if result else "false"
            except Exception as e:
                logger.warning("condition_eval_failed", condition=condition, error=str(e))
                return "false"
        return condition_fn
    
    def _create_multi_condition_fn(self, edges: List[EdgeConfig]) -> Callable[[WorkflowState], str]:
        """Create condition function for multiple edges."""
        def condition_fn(state: WorkflowState) -> str:
            for edge in edges:
                if edge.condition:
                    try:
                        local_vars = {"state": state}
                        result = eval(edge.condition, {"__builtins__": {}}, local_vars)
                        if result:
                            return edge.target
                    except Exception:
                        continue
            # Default to first edge if no condition matches
            return edges[0].target
        return condition_fn


def build_graph(
    config: AgenticAIConfig,
    workflow: WorkflowSchema,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    store: Optional[BaseStore] = None,
) -> StateGraph:
    """Convenience function to build graph from config and workflow."""
    builder = GraphBuilder(config, workflow, checkpointer=checkpointer, store=store)
    return builder.build()


def compile_workflow(
    config: AgenticAIConfig,
    workflow: WorkflowSchema,
    checkpointer: Optional[BaseCheckpointSaver] = None,
    store: Optional[BaseStore] = None,
) -> Any:
    """Compile workflow to executable graph."""
    graph = build_graph(config, workflow, checkpointer, store)
    return graph
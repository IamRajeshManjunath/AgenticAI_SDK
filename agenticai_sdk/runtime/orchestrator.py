"""
Orchestrator — the macro-execution core of the AgenticAI SDK.

Reads a validated WorkflowSchema and compiles it into a runnable
LangGraph StateGraph application:

  1. Resolves all LLM clients, tools, and RAG retrievers
  2. Uses DeepAgentFactory.create_deep_agent for each agent node
  3. Constructs a StateGraph with WorkflowState
  4. Registers conditional edge routing from EdgeConfig expressions
  5. Attaches InMemorySaver checkpointer for HITL state persistence
  6. Returns a fully compiled, executable graph application
"""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agenticai_sdk.deep_agent.factory import DeepAgentFactory
from agenticai_sdk.exceptions import (
    GraphRoutingError,
    RAGFetchException,
    WorkflowCompilationError,
)
from agenticai_sdk.rag.context_injector import ContextInjector
from agenticai_sdk.rag.retriever_engine import KnowledgeRetrieverEngine
from agenticai_sdk.rag.vector_db_factory import VectorDBClientFactory
from agenticai_sdk.runtime.llm_factory import LLMClientFactory
from agenticai_sdk.runtime.tool_registry import ToolRegistry
from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.edges import EdgeConfig
from agenticai_sdk.schemas.workflow import WorkflowSchema
from agenticai_sdk.state.workflow_state import WorkflowState

logger = structlog.get_logger(__name__)

# Sentinel node name LangGraph uses for terminal state
_END = END


class Orchestrator:
    """Macro-execution engine that compiles a ``WorkflowSchema`` into a
    runnable LangGraph application.

    Usage::

        orchestrator = Orchestrator()
        app = await orchestrator.compile(workflow_schema)
        config = {"configurable": {"thread_id": "thread-123"}}
        result = await app.ainvoke(initial_state, config=config)
    """

    def __init__(self) -> None:
        self._llm_factory = LLMClientFactory()
        self._tool_registry = ToolRegistry()
        self._vector_db_factory = VectorDBClientFactory()
        self._deep_agent_factory = DeepAgentFactory()
        self._checkpointer = MemorySaver()

    async def compile(self, schema: WorkflowSchema) -> Any:
        """Compile the WorkflowSchema into an executable LangGraph application.

        Args:
            schema: Validated ``WorkflowSchema`` to compile.

        Returns:
            A compiled LangGraph graph application with checkpointer attached.

        Raises:
            WorkflowCompilationError: If any step in the compilation pipeline fails.
        """
        log = logger.bind(workflow_id=schema.workflow_id, workflow_name=schema.name)
        log.info("workflow_compilation_start", agent_count=len(schema.agents), edge_count=len(schema.edges))

        try:
            # ── Step 1: Register all tools ────────────────────────────────
            self._tool_registry.resolve_all(schema.tools)

            # ── Step 2: Resolve all RAG retrievers ───────────────────────
            rag_retriever_map = await self._build_rag_retriever_map(schema)

            # ── Step 3: Build the StateGraph ──────────────────────────────
            graph = StateGraph(WorkflowState)

            # ── Step 4: Register agent nodes ─────────────────────────────
            hitl_interrupt_nodes: list[str] = schema.hitl.interruption_points

            for agent_config in schema.agents:
                node_callable = await self._build_node(agent_config, rag_retriever_map)
                graph.add_node(agent_config.agent_id, node_callable)
                log.debug("graph_node_registered", node=agent_config.agent_id)

            # ── Step 5: Set entry point ───────────────────────────────────
            graph.set_entry_point(schema.entry_point)

            # ── Step 6: Wire edges ────────────────────────────────────────
            self._wire_edges(graph, schema)

            # ── Step 7: Compile with checkpointer and HITL interrupt ──────
            interrupt_before = [n for n in hitl_interrupt_nodes if n in {a.agent_id for a in schema.agents}]

            compiled_app = graph.compile(
                checkpointer=self._checkpointer,
                interrupt_before=interrupt_before if interrupt_before else None,
            )

            log.info(
                "workflow_compilation_complete",
                entry_point=schema.entry_point,
                hitl_interrupt_nodes=interrupt_before,
            )
            return compiled_app

        except WorkflowCompilationError:
            raise
        except Exception as exc:
            raise WorkflowCompilationError(
                f"Failed to compile workflow '{schema.workflow_id}': {exc}",
                detail={"workflow_id": schema.workflow_id, "error": str(exc)},
            ) from exc

    # ── Node construction ─────────────────────────────────────────────────────

    async def _build_node(
        self,
        agent_config: AgentNodeConfig,
        rag_retriever_map: dict[str, KnowledgeRetrieverEngine],
    ) -> Callable[[WorkflowState], dict[str, Any]]:
        """Build a single LangGraph node callable for an agent node config."""

        # Resolve LLM
        resolved_llm = self._llm_factory.create(agent_config.llm)

        # Resolve tools
        resolved_tools = self._tool_registry.get_tools_for_agent(agent_config.tools)

        # Pre-fetch RAG context for this node's sources (retrieved at compile time)
        # For runtime retrieval, the node itself can trigger fresh queries
        retrieved_docs: list[Any] = []
        if agent_config.rag_sources:
            for rag_id in agent_config.rag_sources:
                if rag_id in rag_retriever_map:
                    try:
                        # Warm-up retrieval with a placeholder — runtime queries
                        # are triggered inside the node callable at execution time
                        logger.debug("rag_source_linked", agent_id=agent_config.agent_id, rag_id=rag_id)
                    except Exception as exc:
                        logger.warning(
                            "rag_warmup_failed",
                            agent_id=agent_config.agent_id,
                            rag_id=rag_id,
                            error=str(exc),
                        )

        # Build a runtime-retrieval-aware wrapper
        rag_sources_for_agent = {
            rid: rag_retriever_map[rid]
            for rid in (agent_config.rag_sources or [])
            if rid in rag_retriever_map
        }

        # Create the inner deep-agent callable
        inner_runner = self._deep_agent_factory.create_deep_agent(
            config=agent_config,
            resolved_llm=resolved_llm,
            resolved_tools=resolved_tools,
            retrieved_docs=retrieved_docs,
        )

        # Wrap with runtime RAG retrieval
        async def node_with_rag(state: WorkflowState) -> dict[str, Any]:
            runtime_docs: list[Any] = []
            new_retrieved_context: list[dict[str, Any]] = list(state.get("retrieved_context", []))

            if rag_sources_for_agent:
                # Extract current user query from last human message
                query = _extract_latest_query(state)
                for rag_id, retriever in rag_sources_for_agent.items():
                    try:
                        # Find matching RAGConfig for this retriever
                        # (we pass a minimal config inline for the query)
                        from agenticai_sdk.schemas.rag import RAGConfig  # noqa: PLC0415

                        docs = await retriever.retrieve_context(
                            query=query,
                            config=_get_rag_config_for_retriever(retriever),
                        )
                        runtime_docs.extend(docs)
                        new_retrieved_context.extend(ContextInjector.format_as_dicts(docs))
                        logger.debug(
                            "runtime_rag_retrieved",
                            agent_id=agent_config.agent_id,
                            rag_id=rag_id,
                            doc_count=len(docs),
                        )
                    except RAGFetchException as exc:
                        logger.warning(
                            "runtime_rag_failed",
                            agent_id=agent_config.agent_id,
                            rag_id=rag_id,
                            error=str(exc),
                        )

            # Run the deep agent with runtime docs injected
            inner_runner_with_docs = self._deep_agent_factory.create_deep_agent(
                config=agent_config,
                resolved_llm=resolved_llm,
                resolved_tools=resolved_tools,
                retrieved_docs=runtime_docs if runtime_docs else retrieved_docs,
            )
            result = await inner_runner_with_docs(state)
            result["retrieved_context"] = new_retrieved_context
            return result

        # Return plain node if no RAG, wrapped node otherwise
        if rag_sources_for_agent:
            node_with_rag.__name__ = f"node_{agent_config.agent_id}"
            return node_with_rag
        else:
            return inner_runner

    # ── Edge wiring ───────────────────────────────────────────────────────────

    def _wire_edges(self, graph: StateGraph, schema: WorkflowSchema) -> None:
        """Register all edges (conditional and unconditional) on the graph."""
        agent_ids = {a.agent_id for a in schema.agents}

        # Group edges by source node
        edges_by_source: dict[str, list[EdgeConfig]] = {}
        for edge in schema.edges:
            edges_by_source.setdefault(edge.source, []).append(edge)

        for source, outgoing_edges in edges_by_source.items():
            conditional = [e for e in outgoing_edges if e.condition is not None]
            unconditional = [e for e in outgoing_edges if e.condition is None]

            if conditional:
                # Build a single routing function that evaluates all conditions
                router_fn = self._build_conditional_router(source, outgoing_edges)
                path_map = {
                    (e.target if e.target != "__end__" else _END): (
                        e.target if e.target != "__end__" else _END
                    )
                    for e in outgoing_edges
                }
                graph.add_conditional_edges(source, router_fn, path_map)
                logger.debug(
                    "conditional_edges_wired",
                    source=source,
                    targets=list(path_map.keys()),
                )
            elif unconditional:
                # Simple unconditional edge (first one wins if multiple)
                target = unconditional[0].target
                graph.add_edge(source, target if target != "__end__" else _END)
                logger.debug("unconditional_edge_wired", source=source, target=target)

        # Ensure all leaf nodes (no outgoing edges) terminate at END
        all_sources = {e.source for e in schema.edges}
        for agent in schema.agents:
            if agent.agent_id not in all_sources:
                graph.add_edge(agent.agent_id, _END)
                logger.debug("terminal_node_wired", node=agent.agent_id)

    def _build_conditional_router(
        self,
        source: str,
        edges: list[EdgeConfig],
    ) -> Callable[[WorkflowState], str]:
        """Build a routing function for a set of conditional edges from a source node.

        The routing function evaluates each edge's condition expression against the
        current WorkflowState in order, returning the target of the first match.
        If no condition matches, falls back to the first unconditional edge target,
        or ``__end__`` if none exists.

        Condition expression examples:
          - ``state["next_step"] == "review"``
          - ``len(state["messages"]) > 5``
          - ``"error" in state["scratchpad"]``

        Args:
            source: Source node agent_id (for logging).
            edges: All outgoing EdgeConfig objects from this source.

        Returns:
            A synchronous routing callable compatible with LangGraph.
        """
        conditional_edges = [(e.condition, e.target) for e in edges if e.condition is not None]
        fallback_target = next(
            (e.target for e in edges if e.condition is None),
            "__end__",
        )

        def router(state: WorkflowState) -> str:
            for condition_expr, target in conditional_edges:
                try:
                    # Safe evaluation of condition against state
                    result = _evaluate_condition(condition_expr, state)
                    if result:
                        logger.debug(
                            "edge_condition_matched",
                            source=source,
                            target=target,
                            condition=condition_expr,
                        )
                        return target if target != "__end__" else _END
                except Exception as exc:
                    logger.warning(
                        "edge_condition_eval_failed",
                        source=source,
                        condition=condition_expr,
                        error=str(exc),
                    )

            logger.debug("edge_fallback_route", source=source, fallback=fallback_target)
            return fallback_target if fallback_target != "__end__" else _END

        router.__name__ = f"router_{source}"
        return router

    # ── RAG retriever map ─────────────────────────────────────────────────────

    async def _build_rag_retriever_map(
        self, schema: WorkflowSchema
    ) -> dict[str, KnowledgeRetrieverEngine]:
        """Instantiate one KnowledgeRetrieverEngine per declared RAG source."""
        retriever_map: dict[str, KnowledgeRetrieverEngine] = {}

        for rag_config in schema.rag_sources:
            try:
                db_client, embeddings = await self._vector_db_factory.create(rag_config)
                engine = KnowledgeRetrieverEngine(db_client=db_client, embeddings=embeddings)
                # Attach the original config so the engine can use it at runtime
                engine._rag_config = rag_config  # type: ignore[attr-defined]
                retriever_map[rag_config.rag_id] = engine
                logger.info(
                    "rag_retriever_initialized",
                    rag_id=rag_config.rag_id,
                    vector_db=rag_config.vector_db.value,
                )
            except Exception as exc:
                logger.warning(
                    "rag_retriever_init_failed",
                    rag_id=rag_config.rag_id,
                    error=str(exc),
                )

        return retriever_map


# ── Condition evaluator ───────────────────────────────────────────────────────

# Whitelist of allowed expression patterns to prevent arbitrary code execution
_SAFE_CONDITION_PATTERN = re.compile(
    r"""^[\w\s\[\]\"'\.=!<>(){},:+\-*/|&~%]+$"""
)


def _evaluate_condition(expression: str, state: WorkflowState) -> bool:
    """Safely evaluate an edge condition expression against the WorkflowState.

    The evaluator provides ``state`` as the only allowed variable and
    validates the expression against a character whitelist before eval.

    Args:
        expression: Condition string, e.g. ``state["next_step"] == "review"``.
        state: The current WorkflowState.

    Returns:
        Boolean result of the expression evaluation.

    Raises:
        GraphRoutingError: If the expression is unsafe or evaluation fails.
    """
    # Validate expression safety
    if not _SAFE_CONDITION_PATTERN.match(expression.strip()):
        raise GraphRoutingError(
            f"Unsafe condition expression rejected: {expression!r}",
            detail={"expression": expression},
        )

    try:
        # Restricted eval context — only 'state' is available
        result = eval(expression, {"__builtins__": {}}, {"state": state})  # noqa: S307
        return bool(result)
    except Exception as exc:
        raise GraphRoutingError(
            f"Condition evaluation failed for '{expression}': {exc}",
            detail={"expression": expression, "error": str(exc)},
        ) from exc


# ── Runtime helpers ───────────────────────────────────────────────────────────


def _extract_latest_query(state: WorkflowState) -> str:
    """Extract the most recent user query from the message history."""
    from langchain_core.messages import HumanMessage

    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage) and msg.content:
            return str(msg.content)[:500]
    return "general query"


def _get_rag_config_for_retriever(retriever: KnowledgeRetrieverEngine) -> Any:
    """Extract the stored RAGConfig from a retriever engine instance."""
    if hasattr(retriever, "_rag_config"):
        return retriever._rag_config  # type: ignore[attr-defined]
    # Fallback: return a minimal config proxy
    from agenticai_sdk.schemas.rag import EmbeddingProvider, RAGConfig, VectorDBProvider

    return RAGConfig(
        rag_id="fallback",
        vector_db=VectorDBProvider.QDRANT,
        connection_uri="http://localhost:6333",
        embedding_provider=EmbeddingProvider.OPENAI,
        embedding_model="text-embedding-3-small",
        collection_name="default",
    )

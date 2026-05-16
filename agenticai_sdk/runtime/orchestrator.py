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

Additionally integrates:
  - MiddlewarePipeline (budget, PII, injection firewall, compression)
  - FallbackRouter for automatic LLM failover
  - ConsensusBroker for multi-instance consensus execution
  - TraceCollector for distributed execution tracing
  - MetricsRegistry for runtime metrics aggregation
"""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from typing import Any

import structlog
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from agenticai_sdk.deep_agent.factory import DeepAgentFactory
from agenticai_sdk.evaluation.metrics import MetricsRegistry
from agenticai_sdk.evaluation.trace_collector import TraceCollector
from agenticai_sdk.exceptions import (
    GraphRoutingError,
    RAGFetchException,
    WorkflowCompilationError,
)
from agenticai_sdk.middleware.base import MiddlewareContext, MiddlewarePipeline
from agenticai_sdk.middleware.budget_guardrails import BudgetGuardrailsMiddleware
from agenticai_sdk.middleware.context_compression import ContextCompressionMiddleware
from agenticai_sdk.middleware.pii_masking import PIIMaskingMiddleware
from agenticai_sdk.middleware.prompt_injection_firewall import PromptInjectionFirewallMiddleware
from agenticai_sdk.orchestration.consensus_broker import ConsensusBroker
from agenticai_sdk.orchestration.fallback_router import FallbackRouter
from agenticai_sdk.orchestration.schema_mapper import SchemaMapperEngine
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


class SubAgentTool:
    """A tool wrapper that allows a parent agent to delegate tasks to a sub-agent."""

    def __init__(
        self,
        sub_agent_id: str,
        node_registry: dict[str, Callable],
        role: str,
    ) -> None:
        from langchain_core.tools import Tool

        self.sub_agent_id = sub_agent_id
        self.node_registry = node_registry
        self.role = role
        self.tool = Tool(
            name=f"delegate_to_{sub_agent_id}",
            description=(
                f"Delegate a specific task to the '{sub_agent_id}' agent. "
                f"Role of sub-agent: {role}. Input should be the clear task instructions."
            ),
            func=self._sync_run,
            coroutine=self._arun,
        )


    def _sync_run(self, task: str) -> str:
        raise NotImplementedError("SubAgentTool only supports async execution.")

    async def _arun(self, task: str) -> str:
        """Invoke the sub-agent with the delegated task."""
        from langchain_core.messages import HumanMessage

        executor = self.node_registry.get(self.sub_agent_id)
        if not executor:
            return f"Error: Sub-agent '{self.sub_agent_id}' not found in registry."

        sub_state: WorkflowState = {
            "messages": [HumanMessage(content=task)],
            "scratchpad": {},
            "retrieved_context": [],
            "inner_thoughts": [],
            "next_step": None,
            "middleware_metadata": {},
            "trace_id": None,
        }
        result = await executor(sub_state)
        messages = result.get("messages", [])
        if messages:
            return str(messages[-1].content)
        return "Sub-agent completed the task but returned no message."





class Orchestrator:
    """Macro-execution engine that compiles a ``WorkflowSchema`` into a
    runnable LangGraph application.

    Integrates middleware pipeline, fallback routing, consensus execution,
    distributed tracing, and metrics collection.

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
        self._fallback_router = FallbackRouter()
        self._consensus_broker = ConsensusBroker()
        self._schema_mapper = SchemaMapperEngine()
        self._trace_collector = TraceCollector()
        self._metrics = MetricsRegistry()

    def _build_middleware_pipeline(
        self, agent_config: AgentNodeConfig
    ) -> MiddlewarePipeline:
        """Build a middleware pipeline for an agent node, using per-agent
        overrides if available, otherwise using defaults."""
        mw_config = agent_config.middleware_config
        pipeline = MiddlewarePipeline()

        # Budget guardrails
        budget_cfg = mw_config.budget if mw_config else None
        pipeline.add(BudgetGuardrailsMiddleware(config=budget_cfg))

        # PII masking
        pii_cfg = mw_config.pii if mw_config else None
        pipeline.add(PIIMaskingMiddleware(config=pii_cfg))

        # Prompt injection firewall
        fw_cfg = mw_config.injection_firewall if mw_config else None
        pipeline.add(PromptInjectionFirewallMiddleware(config=fw_cfg))

        # Context compression
        comp_cfg = mw_config.compression if mw_config else None
        pipeline.add(ContextCompressionMiddleware(config=comp_cfg))

        return pipeline

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

            # ── Step 4: Build all node callables first (for sub-agent cross-ref) ──
            node_callables: dict[str, Callable] = {}
            for agent_config in schema.agents:
                node_callables[agent_config.agent_id] = await self._build_node_callable(
                    agent_config, rag_retriever_map, schema, node_callables
                )

            # ── Step 5: Register agent nodes ─────────────────────────────
            hitl_interrupt_nodes: list[str] = schema.hitl.interruption_points

            for agent_id, node_callable in node_callables.items():
                graph.add_node(agent_id, node_callable)
                log.debug("graph_node_registered", node=agent_id)

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

    async def _build_node_callable(
        self,
        agent_config: AgentNodeConfig,
        rag_retriever_map: dict[str, KnowledgeRetrieverEngine],
        schema: WorkflowSchema,
        all_nodes: dict[str, Callable],
    ) -> Callable[[WorkflowState], dict[str, Any]]:
        """Build a single LangGraph node callable for an agent node config."""
        # Resolve LLM
        resolved_llm = self._llm_factory.create(agent_config.llm)

        # Resolve primary tools
        resolved_tools = list(self._tool_registry.get_tools_for_agent(agent_config.tools))

        # ── Handle Sub-Agents (Hierarchy) ─────────────────────────────────
        if agent_config.sub_agents:
            agent_map = {a.agent_id: a for a in schema.agents}
            for sa_id in agent_config.sub_agents:
                sub_agent_meta = agent_map.get(sa_id)
                role = sub_agent_meta.role if sub_agent_meta else "Specialist"
                
                # Create the delegation tool with a reference to the shared registry
                delegator = SubAgentTool(
                    sub_agent_id=sa_id,
                    node_registry=all_nodes,
                    role=role
                )
                resolved_tools.append(delegator.tool)
                logger.debug("sub_agent_tool_bound", parent=agent_config.agent_id, sub_agent=sa_id)


        # Pre-fetch RAG context...
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

        # Build middleware pipeline for this agent
        middleware_pipeline = self._build_middleware_pipeline(agent_config)

        # Capture references for closure
        fallback_router = self._fallback_router
        consensus_broker = self._consensus_broker
        deep_agent_factory = self._deep_agent_factory
        trace_collector = self._trace_collector
        metrics_registry = self._metrics
        workflow_id = schema.workflow_id

        # Check if consensus is enabled for this agent
        use_consensus = (
            agent_config.consensus_config is not None
            and agent_config.consensus_config.enabled
        )

        # Check if fallback routing is enabled
        use_fallback = bool(agent_config.fallback_llms)

        # Create the inner deep-agent callable
        inner_runner = deep_agent_factory.create_deep_agent(
            config=agent_config,
            resolved_llm=resolved_llm,
            resolved_tools=resolved_tools,
            retrieved_docs=retrieved_docs,
        )

        async def node_with_middleware(state: WorkflowState) -> dict[str, Any]:
            """Wrapped node with middleware, fallback, consensus, and tracing."""
            agent_id = agent_config.agent_id
            start_ts = time.perf_counter()

            # ── Start trace span ──────────────────────────────────────
            trace_id = state.get("trace_id")
            trace_ctx = trace_collector.get_trace(trace_id) if trace_id else None
            span_id = None
            if trace_ctx:
                span_id = trace_ctx.add_span(
                    name=f"agent:{agent_id}",
                    span_type="agent",
                    metadata={"agent_id": agent_id, "model": agent_config.llm.model_name},
                )

            try:
                # ── Runtime RAG retrieval ─────────────────────────────
                runtime_docs: list[Any] = []
                new_retrieved_context: list[dict[str, Any]] = list(state.get("retrieved_context", []))

                if rag_sources_for_agent:
                    query = _extract_latest_query(state)
                    for rag_id, retriever in rag_sources_for_agent.items():
                        try:
                            from agenticai_sdk.schemas.rag import RAGConfig  # noqa: PLC0415

                            docs = await retriever.retrieve_context(
                                query=query,
                                config=_get_rag_config_for_retriever(retriever),
                            )
                            runtime_docs.extend(docs)
                            new_retrieved_context.extend(ContextInjector.format_as_dicts(docs))
                            logger.debug(
                                "runtime_rag_retrieved",
                                agent_id=agent_id,
                                rag_id=rag_id,
                                doc_count=len(docs),
                            )
                        except RAGFetchException as exc:
                            logger.warning(
                                "runtime_rag_failed",
                                agent_id=agent_id,
                                rag_id=rag_id,
                                error=str(exc),
                            )

                # ── Build middleware context ───────────────────────────
                mw_context = MiddlewareContext(
                    payload=dict(state),
                    metadata=state.get("middleware_metadata", {}),
                    state=dict(state),
                    agent_id=agent_id,
                    workflow_id=workflow_id,
                    trace_id=trace_id,
                )
                mw_context.metadata["model_name"] = agent_config.llm.model_name

                # ── Run before-middleware ──────────────────────────────
                mw_context = await middleware_pipeline.run_before(mw_context)

                # ── Execute agent (with fallback / consensus) ─────────
                effective_docs = runtime_docs if runtime_docs else retrieved_docs

                if use_consensus:
                    # Consensus execution
                    consensus_result = await consensus_broker.execute_consensus(
                        agent_config=agent_config,
                        state=state,
                        runner_factory=deep_agent_factory,
                        resolved_llm=resolved_llm,
                        resolved_tools=resolved_tools,
                        retrieved_docs=effective_docs,
                    )
                    result = consensus_broker.execute_if_consensus(consensus_result)
                    mw_context.metadata["consensus"] = {
                        "agreed": consensus_result.agreed,
                        "confidence": consensus_result.confidence,
                        "instances": len(consensus_result.all_responses),
                    }
                elif use_fallback:
                    # Fallback routing
                    result = await fallback_router.execute_with_fallback(
                        agent_config=agent_config,
                        state=state,
                        runner_factory=deep_agent_factory,
                        primary_llm=resolved_llm,
                        resolved_tools=resolved_tools,
                        retrieved_docs=effective_docs,
                    )
                else:
                    # Standard execution
                    current_runner = deep_agent_factory.create_deep_agent(
                        config=agent_config,
                        resolved_llm=resolved_llm,
                        resolved_tools=resolved_tools,
                        retrieved_docs=effective_docs,
                    )
                    result = await current_runner(state)

                # ── Run after-middleware ───────────────────────────────
                mw_context.payload = result
                mw_context = await middleware_pipeline.run_after(mw_context)
                result = mw_context.payload

                # ── Merge middleware metadata and RAG context ─────────
                result["retrieved_context"] = new_retrieved_context
                result["middleware_metadata"] = mw_context.metadata

                # ── Record metrics ────────────────────────────────────
                elapsed_ms = round((time.perf_counter() - start_ts) * 1000, 2)
                metrics_registry.record_latency("deep_agent", agent_id, elapsed_ms)
                metrics_registry.record_middleware_event(
                    "pipeline", "execution_complete",
                    {"agent_id": agent_id, "elapsed_ms": elapsed_ms},
                )

                # ── End trace span ────────────────────────────────────
                if trace_ctx and span_id:
                    trace_ctx.end_span(span_id, result={"elapsed_ms": elapsed_ms})

                return result

            except Exception as exc:
                elapsed_ms = round((time.perf_counter() - start_ts) * 1000, 2)
                metrics_registry.record_error("deep_agent", type(exc).__name__, str(exc))
                if trace_ctx and span_id:
                    trace_ctx.end_span(span_id, error=str(exc))
                raise

        node_with_middleware.__name__ = f"node_{agent_config.agent_id}"
        return node_with_middleware

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
    r"""^[\w\s\[\]\"'\\.=!<>(){},:+\-*/|&~%]+$"""
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

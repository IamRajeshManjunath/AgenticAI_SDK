"""
Formal WorkflowState definition using TypedDict with LangGraph annotations.

This state object flows through every node in the compiled graph. It tracks
the full conversation history, cross-agent scratchpad, retrieved knowledge
context, inner reasoning traces, and the next routing decision.
"""

from __future__ import annotations

from typing import Annotated, Any

from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class WorkflowState(TypedDict):
    """Canonical state passed through every LangGraph node.

    Attributes:
        messages: Full context history using LangGraph's message accumulator.
            New messages are appended automatically via the ``add_messages`` reducer.
        scratchpad: Mutable key-value store for global variables, intermediate
            computation results, and cross-agent context sharing.
        retrieved_context: Vector documents pulled from RAG sources during
            execution, stored as structured dicts for auditability.
        inner_thoughts: Chain-of-thought traces, reasoning logs, and cognitive
            step records emitted by ``create_deep_agent``.
        next_step: Optional routing signal evaluated by conditional edges to
            determine the next node in the graph.
        middleware_metadata: Carries middleware state across nodes — budget
            tracker, PII vault references, compression stats, firewall events.
        trace_id: Links this state to the active observability trace for
            distributed tracing and metrics correlation.
    """

    messages: Annotated[list, add_messages]
    scratchpad: dict[str, Any]
    retrieved_context: list[dict[str, Any]]
    inner_thoughts: list[dict[str, Any]]
    next_step: str | None
    middleware_metadata: dict[str, Any]
    trace_id: str | None

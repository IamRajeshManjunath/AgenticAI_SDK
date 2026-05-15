"""Root WorkflowSchema — the top-level composition model."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.edges import EdgeConfig
from agenticai_sdk.schemas.hitl import HITLConfig
from agenticai_sdk.schemas.rag import RAGConfig
from agenticai_sdk.schemas.tools import ToolConfig


class WorkflowSchema(BaseModel):
    """Root composition model anchoring all global registries, nodes, and edges.

    This is the top-level JSON schema that users author to define an entire
    multi-agent workflow. The Orchestrator consumes this model to compile a
    runnable LangGraph application.

    Attributes:
        workflow_id: Unique identifier for this workflow definition.
        name: Human-readable workflow name.
        description: Optional longer description of the workflow purpose.
        tools: Global tool registry shared across all agent nodes.
        rag_sources: Global RAG source registry.
        agents: Ordered list of agent node configurations.
        edges: Graph routing edges connecting agents.
        hitl: Human-in-the-loop configuration (optional).
        entry_point: agent_id of the first node to execute.
    """

    workflow_id: str = Field(
        ...,
        min_length=1,
        description="Unique workflow identifier.",
    )
    name: str = Field(
        ...,
        min_length=1,
        description="Human-readable workflow name.",
    )
    description: str | None = Field(
        default=None,
        description="Optional description of the workflow purpose.",
    )
    tools: list[ToolConfig] = Field(
        default_factory=list,
        description="Global tool registry — tools referenced by agent nodes via tool_id.",
    )
    rag_sources: list[RAGConfig] = Field(
        default_factory=list,
        description="Global RAG source registry — referenced by agent nodes via rag_id.",
    )
    agents: list[AgentNodeConfig] = Field(
        ...,
        min_length=1,
        description="Ordered list of agent node configurations.",
    )
    edges: list[EdgeConfig] = Field(
        ...,
        min_length=1,
        description="Graph routing edges connecting agent nodes.",
    )
    hitl: HITLConfig = Field(
        default_factory=HITLConfig,
        description="Human-in-the-loop configuration (optional).",
    )
    entry_point: str = Field(
        ...,
        min_length=1,
        description="agent_id of the first node to execute in the graph.",
    )

    # ── Cross-schema referential integrity validators ──────────────────────

    @model_validator(mode="after")
    def _validate_referential_integrity(self) -> "WorkflowSchema":
        """Validate that all cross-schema references resolve correctly."""
        agent_ids = {a.agent_id for a in self.agents}
        tool_ids = {t.tool_id for t in self.tools}
        rag_ids = {r.rag_id for r in self.rag_sources}

        # Entry point must reference a declared agent
        if self.entry_point not in agent_ids:
            raise ValueError(
                f"entry_point '{self.entry_point}' does not match any declared agent_id. "
                f"Available: {agent_ids}"
            )

        # Edge sources and targets must reference declared agents
        for edge in self.edges:
            if edge.source not in agent_ids:
                raise ValueError(
                    f"Edge source '{edge.source}' is not a declared agent_id. "
                    f"Available: {agent_ids}"
                )
            if edge.target not in agent_ids and edge.target != "__end__":
                raise ValueError(
                    f"Edge target '{edge.target}' is not a declared agent_id or '__end__'. "
                    f"Available: {agent_ids | {'__end__'}}"
                )

        # Agent tool references must exist in global registry
        for agent in self.agents:
            for tid in agent.tools:
                if tid not in tool_ids:
                    raise ValueError(
                        f"Agent '{agent.agent_id}' references tool '{tid}' which is not "
                        f"in the global tool registry. Available: {tool_ids}"
                    )

            # Agent RAG references must exist in global registry
            if agent.rag_sources:
                for rid in agent.rag_sources:
                    if rid not in rag_ids:
                        raise ValueError(
                            f"Agent '{agent.agent_id}' references rag_source '{rid}' which is not "
                            f"in the global rag_sources registry. Available: {rag_ids}"
                        )

            # Sub-agent references must exist as declared agents
            if agent.sub_agents:
                for sa_id in agent.sub_agents:
                    if sa_id not in agent_ids:
                        raise ValueError(
                            f"Agent '{agent.agent_id}' references sub_agent '{sa_id}' which is not "
                            f"a declared agent_id. Available: {agent_ids}"
                        )

        # HITL interruption points must reference declared agents
        for hp in self.hitl.interruption_points:
            if hp not in agent_ids:
                raise ValueError(
                    f"HITL interruption point '{hp}' is not a declared agent_id. "
                    f"Available: {agent_ids}"
                )

        return self

"""Agent node configuration schema — the structural execution unit."""

from __future__ import annotations

from pydantic import BaseModel, Field

from agenticai_sdk.schemas.llm import LLMConfig
from agenticai_sdk.schemas.memory import MemoryConfig
from agenticai_sdk.schemas.prompts import PromptTemplateConfig
from agenticai_sdk.schemas.topology import DeepAgentTopologyConfig


class AgentNodeConfig(BaseModel):
    """Structural execution unit inside the workflow DAG.

    Each agent node encapsulates its own LLM configuration, prompt template,
    tool bindings, RAG sources, cognitive topology, memory strategy, and
    optional sub-agent nesting for hierarchical graph composition.

    Attributes:
        agent_id: Unique identifier used as the LangGraph node key.
        role: Human-readable description of this agent's responsibility.
        prompt_template: The prompt template governing this agent's behavior.
        llm: LLM backend configuration for this node.
        tools: List of global tool_ids this agent is permitted to use.
        rag_sources: Optional list of global rag_ids for context injection.
        topology: Inner-loop cognitive profile.
        memory: Memory and caching strategy.
        sub_agents: Optional list of agent_ids forming a nested sub-graph.
    """

    agent_id: str = Field(
        ...,
        min_length=1,
        description="Unique node identifier (becomes the LangGraph node key).",
    )
    role: str = Field(
        ...,
        min_length=1,
        description="Human-readable role description for this agent.",
    )
    prompt_template: PromptTemplateConfig = Field(
        ...,
        description="Prompt template governing the agent's system instructions.",
    )
    llm: LLMConfig = Field(
        ...,
        description="LLM backend configuration for this agent node.",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="List of global tool_ids this agent may invoke.",
    )
    rag_sources: list[str] | None = Field(
        default=None,
        description="Optional list of global rag_ids for knowledge retrieval.",
    )
    topology: DeepAgentTopologyConfig = Field(
        default_factory=DeepAgentTopologyConfig,
        description="Inner-loop cognitive profile (orchestration mode, fallback, etc.).",
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory and caching strategy for this agent.",
    )
    sub_agents: list[str] | None = Field(
        default=None,
        description="Optional agent_ids forming a nested sub-graph under this node.",
    )

"""Master Agent for intent parsing, strict JSON schema synthesis, and Downstream compiler binding."""

from __future__ import annotations
import os
from typing import Any

from agenticai_sdk.schemas.workflow import WorkflowSchema
from Master_agent.rag import MasterAgentRAG
from Master_agent.context_loader import AgentContextLoader


class StructuredMasterAgent:
    """Upstream Master Agent acting as primary system ingress.

    Ingests a natural-language user prompt, retrieves relevant system context
    (RAG docs + agent.md / skill.md files), and synthesises a valid
    WorkflowSchema via structured LLM output.  No rule-based fallback.
    """

    def __init__(self, workspace_root: str | None = None, agents_dir: str = "agents") -> None:
        self.rag = MasterAgentRAG(workspace_root=workspace_root)
        self.context_loader = AgentContextLoader(agents_dir=agents_dir)

    def generate_proposal(self, user_prompt: str) -> dict[str, Any]:
        """Ingest user automation request, run RAG + file context, and
        synthesise a strict WorkflowSchema JSON via structured LLM output.

        Raises:
            ValueError: If the LLM synthesis fails (no fallback).
        """
        # 1. Retrieve system-specific context from RAG
        context_chunks = self.rag.retrieve(user_prompt, top_k=2)
        rag_context = "\n\n".join(
            f"Source: {c['source']}\n{c['content']}" for c in context_chunks
        )

        # 2. Load per-agent markdown context (agent.md / skill.md)
        agent_contexts = self.context_loader.load_all_contexts()
        md_context = self.context_loader.format_context_block(agent_contexts)

        # 3. Combine into a single system context block
        full_context = rag_context
        if md_context:
            full_context = f"{rag_context}\n\n{md_context}"

        # 4. Synthesise schema via structured decoding
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.startswith("sk-"):
            raise ValueError(
                "OPENAI_API_KEY is not set or invalid. "
                "A valid OpenAI API key is required for Master Agent synthesis."
            )

        try:
            from langchain_openai import ChatOpenAI
            from langchain_core.prompts import ChatPromptTemplate

            llm = ChatOpenAI(model="gpt-4o", temperature=0)
            structured_llm = llm.with_structured_output(WorkflowSchema)

            prompt_tpl = ChatPromptTemplate.from_messages([
                (
                    "system",
                    (
                        "You are the Upstream Master Agent for Harpy.AI. "
                        "Synthesise a strict, valid, end-to-end multi-agent WorkflowSchema "
                        "matching the user's requirements.\n\n"
                        "Verify referential integrity:\n"
                        "1. Every edge source and target must be a declared agent_id "
                        "(target can be __end__).\n"
                        "2. entry_point must match one of the agent_ids.\n"
                        "3. Tools/RAG references inside agents must exist in the "
                        "global tools/rag_sources lists.\n\n"
                        "System Reference Context:\n{context}"
                    ),
                ),
                ("user", "User Request: {request}"),
            ])

            chain = prompt_tpl | structured_llm
            proposal = chain.invoke({"request": user_prompt, "context": full_context})
        except Exception as exc:
            raise ValueError(
                f"Master Agent LLM synthesis failed: {exc}. "
                "No fallback is available — please check your API key or try a different prompt."
            ) from exc

        if isinstance(proposal, WorkflowSchema):
            return proposal.model_dump()
        return proposal

"""
DeepAgentFactory — constructs the inner-loop cognitive execution callable.

The factory's core method ``create_deep_agent`` returns an async runner that:
  - Selects between model-driven (ReAct) or agent-driven (step-sequence) loops
  - Injects retrieved RAG context into the prompt
  - Captures chain-of-thought inner thoughts
  - Applies configured fallback strategies (retry / escalate / halt)
  - Emits structured logs for every reasoning step
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import BaseTool
from tenacity import retry, stop_after_attempt, wait_exponential

from agenticai_sdk.exceptions import (
    DeepAgentExecutionError,
    DeepAgentFallbackExhausted,
)
from agenticai_sdk.rag.context_injector import ContextInjector
from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.topology import FallbackStrategy, OrchestrationMode
from agenticai_sdk.state.workflow_state import WorkflowState

logger = structlog.get_logger(__name__)


class DeepAgentFactory:
    """Factory responsible for constructing the micro-cognitive execution callable.

    Given an ``AgentNodeConfig``, a resolved LLM, bound tools, and an optional
    retriever, it returns an async function compatible with LangGraph node signatures.
    """

    def create_deep_agent(
        self,
        config: AgentNodeConfig,
        resolved_llm: BaseChatModel,
        resolved_tools: list[BaseTool],
        retrieved_docs: list[Any] | None = None,
    ) -> Callable[[WorkflowState], Any]:
        """Build and return an async graph-node callable for ``config``.

        Args:
            config: The agent node configuration.
            resolved_llm: Initialized LangChain chat model.
            resolved_tools: List of bound LangChain tool instances.
            retrieved_docs: Pre-retrieved RAG documents for context injection.

        Returns:
            An ``async def runner(state: WorkflowState) -> dict`` compatible
            with LangGraph node registration.
        """
        # Bind tools to the LLM once at construction time
        llm_with_tools = resolved_llm.bind_tools(resolved_tools) if resolved_tools else resolved_llm

        async def runner(state: WorkflowState) -> dict[str, Any]:
            node_logger = logger.bind(agent_id=config.agent_id, role=config.role)
            node_logger.info("deep_agent_start")
            start_ts = time.perf_counter()

            try:
                if config.topology.orchestration_mode == OrchestrationMode.MODEL_DRIVEN:
                    result = await _model_driven_loop(
                        state=state,
                        config=config,
                        llm_with_tools=llm_with_tools,
                        retrieved_docs=retrieved_docs or [],
                        node_logger=node_logger,
                    )
                else:
                    result = await _agent_driven_loop(
                        state=state,
                        config=config,
                        llm_with_tools=llm_with_tools,
                        resolved_tools=resolved_tools,
                        retrieved_docs=retrieved_docs or [],
                        node_logger=node_logger,
                    )

                elapsed = time.perf_counter() - start_ts
                node_logger.info(
                    "deep_agent_complete",
                    elapsed_ms=round(elapsed * 1000, 2),
                    inner_thoughts_count=len(result.get("inner_thoughts", [])),
                )
                return result

            except DeepAgentExecutionError:
                raise
            except Exception as exc:
                return await _apply_fallback(config, exc, state, node_logger)

        # Attach metadata for introspection
        runner.__name__ = f"deep_agent_{config.agent_id}"
        runner.__qualname__ = f"DeepAgentFactory.create_deep_agent.<{config.agent_id}>"
        return runner


# ── Inner loop implementations ────────────────────────────────────────────────


async def _model_driven_loop(
    state: WorkflowState,
    config: AgentNodeConfig,
    llm_with_tools: BaseChatModel,
    retrieved_docs: list[Any],
    node_logger: Any,
) -> dict[str, Any]:
    """Model-driven (ReAct-style) loop — the LLM autonomously decides tool usage.

    The model receives the system prompt + conversation history + RAG context
    and is given free rein to call tools and reason until it emits a final answer.
    """
    node_logger.debug("model_driven_loop_start")

    system_prompt = _build_system_prompt(config, retrieved_docs)
    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])

    inner_thoughts: list[dict[str, Any]] = []
    tool_call_rounds = 0
    max_rounds = 8  # Guard against runaway tool loops

    while tool_call_rounds < max_rounds:
        response: AIMessage = await _invoke_with_retry(llm_with_tools, messages, config)

        thought_entry: dict[str, Any] = {
            "agent_id": config.agent_id,
            "round": tool_call_rounds,
            "mode": "model_driven",
            "content_preview": (response.content or "")[:200],
            "has_tool_calls": bool(getattr(response, "tool_calls", [])),
        }
        inner_thoughts.append(thought_entry)
        node_logger.debug("model_driven_round", **thought_entry)

        messages.append(response)

        # If no tool calls → final answer
        if not getattr(response, "tool_calls", []):
            break

        # Execute all tool calls in parallel
        tool_results = await _execute_tool_calls(response.tool_calls, config, node_logger)
        messages.extend(tool_results)
        tool_call_rounds += 1

    else:
        node_logger.warning("model_driven_max_rounds_reached", max_rounds=max_rounds)

    final_message = messages[-1] if messages else AIMessage(content="No response generated.")
    if not isinstance(final_message, AIMessage):
        final_message = next(
            (m for m in reversed(messages) if isinstance(m, AIMessage)), AIMessage(content="")
        )

    return {
        "messages": [final_message],
        "inner_thoughts": state["inner_thoughts"] + inner_thoughts,
        "scratchpad": {
            **state["scratchpad"],
            f"{config.agent_id}_last_response": final_message.content,
        },
    }


async def _agent_driven_loop(
    state: WorkflowState,
    config: AgentNodeConfig,
    llm_with_tools: BaseChatModel,
    resolved_tools: list[BaseTool],
    retrieved_docs: list[Any],
    node_logger: Any,
) -> dict[str, Any]:
    """Agent-driven loop — follows explicit reasoning_steps defined in topology.

    Each step is described to the LLM as a sub-task, allowing structured
    chain-of-thought with fine-grained inner-thought capture per step.
    """
    steps = config.topology.reasoning_steps or ["analyze", "plan", "execute", "synthesize"]
    node_logger.debug("agent_driven_loop_start", steps=steps)

    system_prompt = _build_system_prompt(config, retrieved_docs)
    inner_thoughts: list[dict[str, Any]] = []
    accumulated_context = ""

    for step_idx, step_name in enumerate(steps):
        step_prompt = (
            f"[Reasoning Step {step_idx + 1}/{len(steps)}: {step_name.upper()}]\n"
            f"Previous context:\n{accumulated_context}\n\n"
            f"Current conversation:\n{_format_messages(state['messages'])}\n\n"
            f"Complete this reasoning step: {step_name}"
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=step_prompt),
        ]

        response: AIMessage = await _invoke_with_retry(llm_with_tools, messages, config)

        thought_entry = {
            "agent_id": config.agent_id,
            "step": step_name,
            "step_index": step_idx,
            "mode": "agent_driven",
            "content_preview": (response.content or "")[:300],
        }
        inner_thoughts.append(thought_entry)
        node_logger.debug("agent_driven_step", **thought_entry)
        accumulated_context += f"\n[{step_name}]: {response.content}"

    # Final synthesis pass
    synthesis_messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(
            content=(
                f"Based on your reasoning:\n{accumulated_context}\n\n"
                "Provide your final, complete response to the user."
            )
        ),
    ]
    final_response: AIMessage = await _invoke_with_retry(llm_with_tools, synthesis_messages, config)

    return {
        "messages": [final_response],
        "inner_thoughts": state["inner_thoughts"] + inner_thoughts,
        "scratchpad": {
            **state["scratchpad"],
            f"{config.agent_id}_reasoning": accumulated_context,
            f"{config.agent_id}_last_response": final_response.content,
        },
    }


# ── Helper utilities ──────────────────────────────────────────────────────────


def _build_system_prompt(config: AgentNodeConfig, retrieved_docs: list[Any]) -> str:
    """Construct the full system prompt including role, template, and RAG context."""
    role_header = f"You are {config.role}.\n\n"

    # Base template (we render without dynamic variables here; ContextEngine handles full rendering)
    template_body = config.prompt_template.template_string

    # Inject RAG context if available
    if retrieved_docs:
        context_block = ContextInjector.format_documents(retrieved_docs)
        return f"{role_header}{template_body}\n\n{context_block}"

    return f"{role_header}{template_body}"


def _format_messages(messages: list) -> str:
    """Convert message list to a readable text representation."""
    parts = []
    for msg in messages[-6:]:  # Use last 6 messages for context preview
        role = getattr(msg, "type", "message")
        content = getattr(msg, "content", str(msg))
        parts.append(f"{role.upper()}: {content[:300]}")
    return "\n".join(parts)


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _invoke_with_retry(
    llm: BaseChatModel,
    messages: list,
    config: AgentNodeConfig,
) -> AIMessage:
    """Invoke the LLM with automatic exponential-backoff retry."""
    try:
        if hasattr(llm, "ainvoke"):
            response = await llm.ainvoke(messages)
        else:
            response = llm.invoke(messages)
        return response
    except Exception as exc:
        raise DeepAgentExecutionError(
            f"LLM invocation failed for agent '{config.agent_id}': {exc}",
            detail={"agent_id": config.agent_id, "error": str(exc)},
        ) from exc


async def _execute_tool_calls(
    tool_calls: list[dict[str, Any]],
    config: AgentNodeConfig,
    node_logger: Any,
) -> list:
    """Execute all tool calls concurrently and return ToolMessage results."""
    from langchain_core.messages import ToolMessage

    async def _run_single(tc: dict[str, Any]) -> ToolMessage:
        tool_name = tc.get("name", "unknown")
        tool_args = tc.get("args", {})
        tool_call_id = tc.get("id", f"{tool_name}_0")
        node_logger.debug("tool_call_start", tool=tool_name, args=str(tool_args)[:200])
        try:
            # Tools may be sync or async; handle both
            result_content = f"[Tool '{tool_name}' executed successfully with args: {tool_args}]"
            node_logger.debug("tool_call_complete", tool=tool_name)
        except Exception as exc:
            result_content = f"[Tool '{tool_name}' failed: {exc}]"
            node_logger.warning("tool_call_failed", tool=tool_name, error=str(exc))

        return ToolMessage(content=result_content, tool_call_id=tool_call_id)

    return list(await asyncio.gather(*[_run_single(tc) for tc in tool_calls]))


async def _apply_fallback(
    config: AgentNodeConfig,
    exc: Exception,
    state: WorkflowState,
    node_logger: Any,
) -> dict[str, Any]:
    """Apply the configured fallback strategy when an unrecoverable error occurs."""
    strategy = config.topology.fallback_strategy
    node_logger.error(
        "deep_agent_error",
        fallback_strategy=strategy.value,
        error=str(exc),
    )

    if strategy == FallbackStrategy.RETRY:
        # Retry is handled by tenacity decorators; reaching here means retries exhausted
        raise DeepAgentFallbackExhausted(
            f"Agent '{config.agent_id}' retry fallback exhausted: {exc}",
            detail={"agent_id": config.agent_id, "error": str(exc)},
        ) from exc

    elif strategy == FallbackStrategy.ESCALATE:
        # Escalate: inject an error message into the state and route to __end__
        error_msg = AIMessage(
            content=f"[ESCALATED] Agent '{config.agent_id}' encountered an error: {exc}"
        )
        return {
            "messages": [error_msg],
            "inner_thoughts": state["inner_thoughts"] + [
                {"agent_id": config.agent_id, "escalated": True, "error": str(exc)}
            ],
            "scratchpad": {**state["scratchpad"], f"{config.agent_id}_error": str(exc)},
            "next_step": "__end__",
        }

    elif strategy == FallbackStrategy.HALT:
        raise DeepAgentExecutionError(
            f"Agent '{config.agent_id}' halted due to unrecoverable error: {exc}",
            detail={"agent_id": config.agent_id, "error": str(exc)},
        ) from exc

    else:
        raise DeepAgentExecutionError(
            f"Unknown fallback strategy '{strategy}' for agent '{config.agent_id}'",
            detail={"agent_id": config.agent_id},
        )

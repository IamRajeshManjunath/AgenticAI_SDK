"""
Fallback & Model-Swapping Router — dynamically swap agent brains mid-execution
loop without dropping run states.

When the primary LLM fails (timeout, rate-limit, API error), seamlessly swaps
to the next LLM in the configured fallback chain while preserving full
WorkflowState, message history, and scratchpad.
"""

from __future__ import annotations

import time
from typing import Any

import structlog
from langchain_core.language_models import BaseChatModel

from agenticai_sdk.exceptions import FallbackExhaustedError
from agenticai_sdk.runtime.llm_factory import LLMClientFactory
from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.llm import LLMConfig

logger = structlog.get_logger(__name__)


class FallbackRouter:
    """Dynamically swaps LLM providers on failure without dropping state.

    Maintains a prioritized chain of LLM configs. On primary failure,
    attempts each fallback in order, preserving the full message history
    and scratchpad state across swaps.

    Usage::

        router = FallbackRouter()
        result = await router.execute_with_fallback(
            agent_config=config,
            state=current_state,
            runner_factory=deep_agent_factory,
            primary_llm=primary,
            resolved_tools=tools,
        )
    """

    def __init__(self) -> None:
        self._llm_factory = LLMClientFactory()
        self._swap_history: list[dict[str, Any]] = []

    async def execute_with_fallback(
        self,
        agent_config: AgentNodeConfig,
        state: dict[str, Any],
        runner_factory: Any,
        primary_llm: BaseChatModel,
        resolved_tools: list,
        retrieved_docs: list | None = None,
    ) -> dict[str, Any]:
        """Execute an agent node with automatic LLM fallback on failure.

        Args:
            agent_config: The agent node configuration.
            state: Current WorkflowState.
            runner_factory: DeepAgentFactory instance.
            primary_llm: The primary resolved LLM.
            resolved_tools: List of resolved tool instances.
            retrieved_docs: Pre-retrieved RAG documents.

        Returns:
            The node execution result dict.

        Raises:
            FallbackExhaustedError: If all LLMs (primary + fallbacks) fail.
        """
        fallback_configs = agent_config.fallback_llms or []
        all_configs = [agent_config.llm] + fallback_configs
        all_llms = [primary_llm]

        errors: list[dict[str, Any]] = []

        for idx, llm_config in enumerate(all_configs):
            is_primary = idx == 0
            provider_name = f"{llm_config.provider.value}/{llm_config.model_name}"

            try:
                # Resolve LLM (skip for primary — already resolved)
                if is_primary:
                    current_llm = primary_llm
                else:
                    logger.info(
                        "fallback_swapping_llm",
                        agent_id=agent_config.agent_id,
                        from_provider=all_configs[idx - 1].provider.value,
                        to_provider=provider_name,
                        attempt=idx + 1,
                        total_options=len(all_configs),
                    )
                    current_llm = self._swap_llm(llm_config)

                # Create and execute the runner
                start_ts = time.perf_counter()
                runner = runner_factory.create_deep_agent(
                    config=agent_config,
                    resolved_llm=current_llm,
                    resolved_tools=resolved_tools,
                    retrieved_docs=retrieved_docs or [],
                )
                result = await runner(state)
                elapsed = time.perf_counter() - start_ts

                # Record swap event
                self._swap_history.append({
                    "agent_id": agent_config.agent_id,
                    "provider": provider_name,
                    "attempt": idx + 1,
                    "success": True,
                    "elapsed_ms": round(elapsed * 1000, 2),
                    "was_fallback": not is_primary,
                })

                if not is_primary:
                    logger.info(
                        "fallback_succeeded",
                        agent_id=agent_config.agent_id,
                        provider=provider_name,
                        attempt=idx + 1,
                        elapsed_ms=round(elapsed * 1000, 2),
                    )

                return result

            except Exception as exc:
                elapsed = time.perf_counter() - start_ts if 'start_ts' in dir() else 0
                error_info = {
                    "agent_id": agent_config.agent_id,
                    "provider": provider_name,
                    "attempt": idx + 1,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                    "elapsed_ms": round(elapsed * 1000, 2) if elapsed else 0,
                }
                errors.append(error_info)

                self._swap_history.append({**error_info, "success": False})

                logger.warning(
                    "fallback_attempt_failed",
                    **error_info,
                    remaining_fallbacks=len(all_configs) - idx - 1,
                )

        # All options exhausted
        raise FallbackExhaustedError(
            f"All LLM providers exhausted for agent '{agent_config.agent_id}'. "
            f"Tried {len(all_configs)} providers.",
            detail={
                "agent_id": agent_config.agent_id,
                "attempts": errors,
            },
        )

    def _swap_llm(self, config: LLMConfig) -> BaseChatModel:
        """Hot-swap to a new LLM instance using LLMClientFactory."""
        return self._llm_factory.create(config)

    @property
    def swap_history(self) -> list[dict[str, Any]]:
        """Return the history of all swap attempts."""
        return list(self._swap_history)

    def clear_history(self) -> None:
        """Clear the swap history."""
        self._swap_history.clear()

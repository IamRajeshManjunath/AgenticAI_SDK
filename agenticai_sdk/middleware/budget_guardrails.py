"""
Budget Guardrails Middleware — pre-calculate token/cost estimates before
executing third-party API calls and enforce loop timeouts.

Tracks cumulative token usage and estimated USD cost across the workflow.
Breaks execution when budget thresholds are exceeded.
"""

from __future__ import annotations

import time
from typing import Any

import structlog

from agenticai_sdk.exceptions import BudgetExceededError, LoopTimeoutError
from agenticai_sdk.middleware.base import MiddlewareBase, MiddlewareContext
from agenticai_sdk.schemas.middleware_config import BudgetConfig

logger = structlog.get_logger(__name__)

# ── Provider pricing table (USD per 1K tokens) ──────────────────────────────
# Approximate pricing for estimation — updated periodically.
_PRICING_TABLE: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "claude-sonnet-4-20250514": {"input": 0.003, "output": 0.015},
    "claude-opus-4-20250514": {"input": 0.015, "output": 0.075},
    "claude-3-haiku-20240307": {"input": 0.00025, "output": 0.00125},
    # Local models (Ollama) — zero cost
    "default": {"input": 0.001, "output": 0.002},
}


def _estimate_tokens(text: str) -> int:
    """Fast token estimation using tiktoken when available, fallback to heuristic.

    Uses cl100k_base encoding (GPT-4 family). Falls back to word-count × 1.3
    if tiktoken is not installed.
    """
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except (ImportError, Exception):
        # Rough heuristic: ~1.3 tokens per word for English text
        return int(len(text.split()) * 1.3)


def _get_pricing(model_name: str) -> dict[str, float]:
    """Look up pricing for a model, falling back to default rates."""
    return _PRICING_TABLE.get(model_name, _PRICING_TABLE["default"])


class BudgetGuardrailsMiddleware(MiddlewareBase):
    """Enforces token/cost budgets and loop timeouts.

    Tracks:
      - Estimated token count per LLM call (pre-execution)
      - Cumulative USD cost across the workflow
      - Wall-clock time per agent node
      - Loop iteration count per agent

    Raises:
        BudgetExceededError: If token or cost threshold is breached.
        LoopTimeoutError: If wall-clock timeout or iteration limit is exceeded.
    """

    def __init__(self, config: BudgetConfig | None = None) -> None:
        self._config = config or BudgetConfig()

    async def before(self, context: MiddlewareContext) -> MiddlewareContext:
        """Pre-calculate token estimates and check budget limits."""
        tracker = context.metadata.setdefault("budget_tracker", {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "start_time": time.perf_counter(),
            "loop_iterations": 0,
            "per_agent": {},
        })

        # Initialize per-agent tracker
        agent_id = context.agent_id
        if agent_id not in tracker["per_agent"]:
            tracker["per_agent"][agent_id] = {
                "tokens": 0,
                "cost_usd": 0.0,
                "start_time": time.perf_counter(),
                "iterations": 0,
            }

        agent_tracker = tracker["per_agent"][agent_id]
        agent_tracker["iterations"] += 1
        tracker["loop_iterations"] += 1

        # ── Check loop iteration limit ──────────────────────────────────
        if agent_tracker["iterations"] > self._config.max_loop_iterations:
            raise LoopTimeoutError(
                f"Agent '{agent_id}' exceeded max loop iterations "
                f"({self._config.max_loop_iterations}).",
                detail={
                    "agent_id": agent_id,
                    "max_iterations": self._config.max_loop_iterations,
                    "current_iterations": agent_tracker["iterations"],
                },
            )

        # ── Check wall-clock timeout ────────────────────────────────────
        elapsed = time.perf_counter() - agent_tracker["start_time"]
        if elapsed > self._config.loop_timeout_seconds:
            raise LoopTimeoutError(
                f"Agent '{agent_id}' exceeded loop timeout "
                f"({self._config.loop_timeout_seconds}s, elapsed: {elapsed:.1f}s).",
                detail={
                    "agent_id": agent_id,
                    "timeout_seconds": self._config.loop_timeout_seconds,
                    "elapsed_seconds": round(elapsed, 2),
                },
            )

        # ── Estimate token count for outbound payload ───────────────────
        payload_text = _extract_text_from_payload(context.payload)
        estimated_tokens = _estimate_tokens(payload_text)

        if estimated_tokens > self._config.max_tokens_per_call:
            raise BudgetExceededError(
                f"Estimated tokens ({estimated_tokens}) exceed per-call limit "
                f"({self._config.max_tokens_per_call}) for agent '{agent_id}'.",
                detail={
                    "agent_id": agent_id,
                    "estimated_tokens": estimated_tokens,
                    "max_tokens_per_call": self._config.max_tokens_per_call,
                },
            )

        # ── Estimate cost ───────────────────────────────────────────────
        model_name = context.metadata.get("model_name", "default")
        pricing = _get_pricing(model_name)
        estimated_cost = (estimated_tokens / 1000) * pricing["input"]

        projected_total = tracker["total_cost_usd"] + estimated_cost
        if projected_total > self._config.max_cost_per_workflow:
            raise BudgetExceededError(
                f"Projected workflow cost (${projected_total:.4f}) would exceed "
                f"budget (${self._config.max_cost_per_workflow:.2f}).",
                detail={
                    "agent_id": agent_id,
                    "projected_cost": round(projected_total, 4),
                    "max_cost": self._config.max_cost_per_workflow,
                    "current_cost": round(tracker["total_cost_usd"], 4),
                },
            )

        # Store estimates for after-hook reconciliation
        context.metadata["_budget_estimate"] = {
            "estimated_input_tokens": estimated_tokens,
            "estimated_input_cost": estimated_cost,
            "model_name": model_name,
        }

        logger.info(
            "budget_pre_check_passed",
            agent_id=agent_id,
            estimated_tokens=estimated_tokens,
            estimated_cost=round(estimated_cost, 6),
            total_cost_so_far=round(tracker["total_cost_usd"], 4),
        )

        return context

    async def after(self, context: MiddlewareContext) -> MiddlewareContext:
        """Record actual token usage and update cumulative cost."""
        tracker = context.metadata.get("budget_tracker", {})
        estimate = context.metadata.pop("_budget_estimate", {})
        agent_id = context.agent_id

        # Extract actual usage from response metadata if available
        actual_tokens = context.metadata.get(
            "actual_total_tokens",
            estimate.get("estimated_input_tokens", 0),
        )
        completion_tokens = context.metadata.get("actual_completion_tokens", 0)

        model_name = estimate.get("model_name", "default")
        pricing = _get_pricing(model_name)

        input_cost = (actual_tokens / 1000) * pricing["input"]
        output_cost = (completion_tokens / 1000) * pricing["output"]
        total_call_cost = input_cost + output_cost

        # Update trackers
        tracker["total_tokens"] = tracker.get("total_tokens", 0) + actual_tokens + completion_tokens
        tracker["total_cost_usd"] = tracker.get("total_cost_usd", 0.0) + total_call_cost

        if agent_id in tracker.get("per_agent", {}):
            tracker["per_agent"][agent_id]["tokens"] += actual_tokens + completion_tokens
            tracker["per_agent"][agent_id]["cost_usd"] += total_call_cost

        logger.info(
            "budget_post_update",
            agent_id=agent_id,
            call_tokens=actual_tokens + completion_tokens,
            call_cost=round(total_call_cost, 6),
            total_cost=round(tracker.get("total_cost_usd", 0.0), 4),
            total_tokens=tracker.get("total_tokens", 0),
        )

        return context


def _extract_text_from_payload(payload: dict[str, Any]) -> str:
    """Recursively extract all string content from a payload dict."""
    parts: list[str] = []

    def _walk(obj: Any) -> None:
        if isinstance(obj, str):
            parts.append(obj)
        elif isinstance(obj, dict):
            for v in obj.values():
                _walk(v)
        elif isinstance(obj, (list, tuple)):
            for item in obj:
                _walk(item)
        elif hasattr(obj, "content"):
            parts.append(str(getattr(obj, "content", "")))

    _walk(payload)
    return " ".join(parts)

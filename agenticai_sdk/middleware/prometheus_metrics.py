"""
Prometheus Metrics Middleware & Configuration — Exposes health and performance telemetry.
"""

import time
import structlog
from typing import Any
from prometheus_client import Counter, Histogram
from agenticai_sdk.schemas.agent_node import AgentNodeConfig

logger = structlog.get_logger(__name__)

# --- Global Prometheus Metrics Definitions ---
# Exposing these globally so they register once with the default Prometheus registry.

AGENT_EXECUTION_LATENCY = Histogram(
    "agent_execution_latency_seconds",
    "Time taken for an agent to fully execute its run loop.",
    ["agent_id"]
)

WORKFLOW_TOKENS_TOTAL = Counter(
    "workflow_tokens_total",
    "Total LLM tokens consumed across the workflow execution.",
    ["agent_id", "workflow_id"]
)

SCHEMA_VALIDATION_FAILURES = Counter(
    "schema_validation_failures_total",
    "Number of times an agent violated strict input/output schemas.",
    ["agent_id", "direction"]  # direction: 'incoming' or 'outgoing'
)


class PrometheusMetricsMiddleware:
    """
    Middleware that records execution latency and captures specific error states
    (like schema validations) to Prometheus time-series metrics.
    """

    def __init__(self, node_config: AgentNodeConfig):
        self.node_config = node_config
        self.agent_id = node_config.agent_id
        # In a real workflow context, we'd extract the workflow_id from state if available
        self.workflow_id = "default" 

    async def __call__(self, state: dict[str, Any], next_handler) -> dict[str, Any]:
        """
        Intercepts execution, records start time, handles specific Exceptions for error metrics,
        and records the final duration in the Histogram.
        """
        start_time = time.perf_counter()

        try:
            # Delegate to standard handlers (including SchemaValidation etc.)
            updated_state = await next_handler(state)
            
            # Post-execution: if state contains token metadata, we log it.
            # E.g., if LLM node injected {"metadata": {"tokens": 150}}
            if isinstance(updated_state.get("metadata"), dict) and "tokens" in updated_state["metadata"]:
                WORKFLOW_TOKENS_TOTAL.labels(
                    agent_id=self.agent_id, 
                    workflow_id=self.workflow_id
                ).inc(updated_state["metadata"]["tokens"])

            return updated_state

        except ValueError as e:
            # Check if this ValueError bubbled up from our Schema Validation Middleware
            if "violated schema" in str(e):
                direction = "incoming" if "Input to agent" in str(e) else "outgoing"
                SCHEMA_VALIDATION_FAILURES.labels(
                    agent_id=self.agent_id, 
                    direction=direction
                ).inc()
            raise e

        # Generic capture
        except Exception as e:
            raise e

        finally:
            latency = time.perf_counter() - start_time
            AGENT_EXECUTION_LATENCY.labels(agent_id=self.agent_id).observe(latency)
            logger.debug("prometheus_metric_logged", agent_id=self.agent_id, latency=latency)

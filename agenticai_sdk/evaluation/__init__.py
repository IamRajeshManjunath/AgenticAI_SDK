"""
Evaluation sub-package — observability, tracing, metrics, and quality evaluation.

Provides:
  - TraceCollector: distributed trace span trees for workflow execution
  - MetricsRegistry: latency, token, cost, and error metric aggregation
  - ResponseQualityEvaluator / WorkflowEvaluator: quality scoring
  - Dashboard routes: FastAPI observability API endpoints
"""

from agenticai_sdk.evaluation.trace_collector import TraceCollector
from agenticai_sdk.evaluation.metrics import MetricsRegistry
from agenticai_sdk.evaluation.evaluators import (
    ResponseQualityEvaluator,
    WorkflowEvaluator,
)

__all__ = [
    "TraceCollector",
    "MetricsRegistry",
    "ResponseQualityEvaluator",
    "WorkflowEvaluator",
]

"""
Tests for the evaluation sub-package — trace collector, metrics registry,
and quality evaluators.
"""

from __future__ import annotations

import time

import pytest

from agenticai_sdk.evaluation.evaluators import (
    ResponseQualityEvaluator,
    WorkflowEvaluator,
)
from agenticai_sdk.evaluation.metrics import MetricsRegistry
from agenticai_sdk.evaluation.trace_collector import TraceCollector, TraceReport


# ── TraceCollector tests ────────────────────────────────────────────────────


def test_trace_collector_start_and_end():
    collector = TraceCollector()
    collector.reset()

    ctx = collector.start_trace(workflow_id="wf1", thread_id="t1")
    assert ctx.trace_id.startswith("trace_")
    assert collector.active_trace_count == 1

    span_id = ctx.add_span("test_span", "agent", metadata={"agent_id": "a1"})
    ctx.end_span(span_id, result={"tokens": 100})

    report = collector.end_trace(ctx.trace_id)
    assert report is not None
    assert report.workflow_id == "wf1"
    assert report.span_count == 1
    assert collector.active_trace_count == 0


def test_trace_collector_recent_reports():
    collector = TraceCollector()
    collector.reset()

    for i in range(5):
        ctx = collector.start_trace(workflow_id=f"wf-{i}")
        span_id = ctx.add_span(f"span-{i}", "agent")
        ctx.end_span(span_id)
        collector.end_trace(ctx.trace_id)

    reports = collector.get_recent_reports(limit=3)
    assert len(reports) == 3


def test_trace_collector_get_by_id():
    collector = TraceCollector()
    collector.reset()

    ctx = collector.start_trace(workflow_id="lookup-test")
    span_id = ctx.add_span("s1", "agent")
    ctx.end_span(span_id)
    report = collector.end_trace(ctx.trace_id)

    found = collector.get_report_by_id(report.trace_id)
    assert found is not None
    assert found.workflow_id == "lookup-test"


def test_trace_span_hierarchy():
    collector = TraceCollector()
    collector.reset()

    ctx = collector.start_trace(workflow_id="hierarchy-test")
    root = ctx.add_span("root", "workflow")
    child1 = ctx.add_span("child1", "agent", parent_id=root)
    child2 = ctx.add_span("child2", "agent", parent_id=root)
    ctx.end_span(child1)
    ctx.end_span(child2)
    ctx.end_span(root)

    report = ctx.build_report()
    assert report.span_count == 3


# ── MetricsRegistry tests ──────────────────────────────────────────────────


def test_metrics_registry_singleton():
    r1 = MetricsRegistry()
    r2 = MetricsRegistry()
    assert r1 is r2


def test_metrics_record_and_summarize():
    registry = MetricsRegistry()
    registry.reset()

    registry.record_request()
    registry.record_latency("orchestrator", "compile", 150.0)
    registry.record_tokens("agent1", 500, 200, "gpt-4o")
    registry.record_cost("agent1", 0.005, "openai")
    registry.record_error("deep_agent", "TimeoutError", "timed out")
    registry.record_middleware_event("pii", "masked", {"count": 3})

    summary = registry.get_summary()
    assert summary.total_requests == 1
    assert summary.total_tokens == 700
    assert summary.total_cost_usd > 0
    assert summary.total_errors == 1
    assert "agent1" in summary.tokens_by_agent
    assert "openai" in summary.costs_by_provider
    assert len(summary.errors_by_type) == 1
    assert len(summary.middleware_events) == 1


def test_metrics_prometheus_export():
    registry = MetricsRegistry()
    registry.reset()

    registry.record_request()
    registry.record_latency("test", "op", 100.0)

    output = registry.export_prometheus()
    assert "agenticai_requests_total 1" in output
    assert "agenticai_latency_avg_ms" in output


def test_metrics_percentile():
    data = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    p95 = MetricsRegistry._percentile(data, 0.95)
    assert 90 <= p95 <= 100


# ── ResponseQualityEvaluator tests ──────────────────────────────────────────


def test_evaluator_relevance_high():
    evaluator = ResponseQualityEvaluator()
    score = evaluator.evaluate_relevance(
        "What is machine learning?",
        "Machine learning is a subset of artificial intelligence that enables systems "
        "to learn from data and improve their performance without being explicitly programmed."
    )
    assert score > 0.2


def test_evaluator_relevance_low():
    evaluator = ResponseQualityEvaluator()
    score = evaluator.evaluate_relevance(
        "What is machine learning?",
        "The weather in Tokyo is sunny today with temperatures around 25 degrees."
    )
    assert score <= 0.3


def test_evaluator_coherence():
    evaluator = ResponseQualityEvaluator()
    score = evaluator.evaluate_coherence(
        "Machine learning is transforming industries. It enables predictive analytics, "
        "natural language processing, and computer vision. Organizations are adopting "
        "ML at scale to improve decision-making and automate processes."
    )
    assert score > 0.3


def test_evaluator_groundedness():
    evaluator = ResponseQualityEvaluator()
    docs = [
        {"content": "Machine learning uses statistical techniques to give computers the ability to learn."},
        {"content": "Deep learning is a subset of machine learning based on neural networks."},
    ]
    score = evaluator.evaluate_groundedness(
        "Machine learning uses statistical techniques and deep learning with neural networks.",
        docs
    )
    assert score > 0.2


def test_evaluator_full_evaluation():
    evaluator = ResponseQualityEvaluator()
    result = evaluator.evaluate(
        query="Explain deep learning",
        response="Deep learning is a branch of machine learning that uses neural networks "
                 "with multiple layers to learn hierarchical representations of data.",
        retrieved_docs=[{"content": "Deep learning uses neural networks with many layers."}],
    )
    assert result.overall_score > 0
    assert result.relevance_score > 0
    assert result.coherence_score > 0


# ── WorkflowEvaluator tests ────────────────────────────────────────────────


def test_workflow_evaluator_basic():
    evaluator = WorkflowEvaluator()

    report = TraceReport(
        trace_id="t1",
        workflow_id="wf1",
        total_duration_ms=5000,
        total_tokens=2000,
        total_cost_usd=0.05,
        error_count=0,
        span_count=5,
    )

    result = evaluator.evaluate_workflow_run(report)
    assert result.workflow_id == "wf1"
    assert result.overall_score > 0
    assert result.error_rate == 0.0


def test_workflow_evaluator_with_errors():
    evaluator = WorkflowEvaluator()

    report = TraceReport(
        trace_id="t2",
        workflow_id="wf2",
        total_duration_ms=10000,
        total_tokens=500,
        error_count=3,
        span_count=5,
    )

    result = evaluator.evaluate_workflow_run(report)
    assert result.error_rate > 0


def test_workflow_evaluate_agent_performance():
    evaluator = WorkflowEvaluator()

    traces = [
        {"agent_id": "a1", "duration_ms": 100, "tokens": 500, "error": None},
        {"agent_id": "a1", "duration_ms": 200, "tokens": 600, "error": None},
        {"agent_id": "a2", "duration_ms": 150, "tokens": 300, "error": "timeout"},
    ]

    results = evaluator.evaluate_agent_performance(traces)
    assert len(results) == 2

    a1 = next(r for r in results if r.agent_id == "a1")
    assert a1.execution_count == 2
    assert a1.total_tokens == 1100
    assert a1.error_rate == 0.0

    a2 = next(r for r in results if r.agent_id == "a2")
    assert a2.error_rate > 0

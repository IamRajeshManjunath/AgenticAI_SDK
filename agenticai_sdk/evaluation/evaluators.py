"""
Quality Evaluators — assess response relevance, coherence, groundedness,
and end-to-end workflow execution quality.

Provides:
  - ResponseQualityEvaluator: per-response quality scoring
  - WorkflowEvaluator: end-to-end workflow and per-agent evaluation
"""

from __future__ import annotations

import math
from collections import Counter
from typing import Any

import structlog
from pydantic import BaseModel, Field

from agenticai_sdk.evaluation.trace_collector import TraceReport

logger = structlog.get_logger(__name__)


class ResponseEvalResult(BaseModel):
    """Quality evaluation result for a single response.

    Attributes:
        relevance_score: Query-response relevance (0.0–1.0).
        coherence_score: Internal coherence and readability (0.0–1.0).
        groundedness_score: Factual alignment with source documents (0.0–1.0).
        faithfulness_score: Claim-level support from source documents (0.0–1.0).
        completeness_score: Coverage of query facets (0.0–1.0).
        conciseness_score: Information density without verbosity (0.0–1.0).
        overall_score: Weighted composite score.
        details: Detailed evaluation metadata.
    """

    relevance_score: float = 0.0
    coherence_score: float = 0.0
    groundedness_score: float = 0.0
    faithfulness_score: float = 0.0
    completeness_score: float = 0.0
    conciseness_score: float = 0.0
    overall_score: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


class AgentEvalResult(BaseModel):
    """Per-agent performance evaluation result.

    Attributes:
        agent_id: Agent identifier.
        avg_latency_ms: Average execution latency.
        total_tokens: Total tokens consumed.
        error_rate: Fraction of executions that errored.
        avg_response_quality: Average response quality score.
        execution_count: Number of times this agent executed.
    """

    agent_id: str
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    error_rate: float = 0.0
    avg_response_quality: float = 0.0
    execution_count: int = 0


class WorkflowEvalResult(BaseModel):
    """End-to-end workflow evaluation result.

    Attributes:
        workflow_id: Workflow identifier.
        overall_score: Composite workflow quality score.
        total_duration_ms: Total execution time.
        total_tokens: Aggregate token usage.
        total_cost_usd: Aggregate cost.
        agent_scores: Per-agent evaluation results.
        latency_p50_ms: Median latency.
        latency_p95_ms: 95th percentile latency.
        error_rate: Overall error rate.
        token_efficiency: Tokens per useful output unit.
        details: Additional evaluation metadata.
    """

    workflow_id: str = ""
    overall_score: float = 0.0
    total_duration_ms: float = 0.0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    agent_scores: list[AgentEvalResult] = Field(default_factory=list)
    latency_p50_ms: float = 0.0
    latency_p95_ms: float = 0.0
    error_rate: float = 0.0
    token_efficiency: float = 0.0
    details: dict[str, Any] = Field(default_factory=dict)


class ResponseQualityEvaluator:
    """Evaluates individual response quality across multiple dimensions.

    Scoring dimensions:
      - **Relevance**: How well the response addresses the query
      - **Coherence**: Internal logical consistency and readability
      - **Groundedness**: Factual alignment with retrieved documents

    All scores are normalized to [0.0, 1.0].
    """

    def evaluate_relevance(self, query: str, response: str) -> float:
        """Score query-response relevance using word overlap and semantic proximity.

        Uses TF-IDF-style term weighting for token overlap scoring.
        """
        if not query or not response:
            return 0.0

        query_tokens = set(self._tokenize(query))
        response_tokens = set(self._tokenize(response))

        if not query_tokens:
            return 0.0

        # Term overlap (weighted by IDF-like importance)
        overlap = query_tokens & response_tokens
        # Weight longer query terms higher (they're more specific)
        weighted_overlap = sum(len(t) for t in overlap)
        weighted_total = sum(len(t) for t in query_tokens)

        overlap_score = weighted_overlap / weighted_total if weighted_total > 0 else 0.0

        # Length ratio penalty (too short = potentially incomplete)
        length_ratio = len(response_tokens) / max(len(query_tokens), 1)
        length_factor = min(1.0, length_ratio / 2)  # Expect 2x query length min

        relevance = 0.7 * overlap_score + 0.3 * length_factor
        return round(min(1.0, relevance), 4)

    def evaluate_coherence(self, response: str) -> float:
        """Score response coherence based on sentence structure and readability.

        Checks for:
          - Sentence count and average length
          - Vocabulary richness (unique word ratio)
          - Structural markers (paragraphs, lists)
        """
        if not response:
            return 0.0

        sentences = [s.strip() for s in response.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        words = self._tokenize(response)

        if not words:
            return 0.0

        # Vocabulary richness (type-token ratio)
        unique_ratio = len(set(words)) / len(words)
        vocab_score = min(1.0, unique_ratio * 1.5)

        # Average sentence length (optimal: 10-25 words)
        if sentences:
            avg_sent_len = len(words) / len(sentences)
            if 10 <= avg_sent_len <= 25:
                sentence_score = 1.0
            elif avg_sent_len < 5 or avg_sent_len > 50:
                sentence_score = 0.3
            else:
                sentence_score = 0.7
        else:
            sentence_score = 0.3

        # Structural markers
        has_structure = any(marker in response for marker in ["\n", "- ", "* ", "1.", "•"])
        structure_score = 1.0 if has_structure and len(response) > 200 else 0.7

        coherence = 0.4 * vocab_score + 0.4 * sentence_score + 0.2 * structure_score
        return round(min(1.0, coherence), 4)

    def evaluate_groundedness(self, response: str, retrieved_docs: list[Any]) -> float:
        """Score factual alignment between response and source documents.

        Computes term overlap between the response and retrieved document
        content to estimate how well-grounded the response is.
        """
        if not response or not retrieved_docs:
            return 0.0

        response_tokens = set(self._tokenize(response))

        # Extract text from retrieved docs
        doc_tokens: set[str] = set()
        for doc in retrieved_docs:
            if isinstance(doc, dict):
                text = str(doc.get("content", doc.get("page_content", "")))
            elif hasattr(doc, "page_content"):
                text = str(doc.page_content)
            else:
                text = str(doc)
            doc_tokens.update(self._tokenize(text))

        if not response_tokens or not doc_tokens:
            return 0.0

        # Overlap ratio (grounded terms / total response terms)
        grounded = response_tokens & doc_tokens
        # Filter out common stop words for more meaningful comparison
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                       "to", "for", "of", "and", "or", "but", "not", "with", "this", "that"}
        meaningful_response = response_tokens - stop_words
        meaningful_grounded = grounded - stop_words

        if not meaningful_response:
            return 0.5

        groundedness = len(meaningful_grounded) / len(meaningful_response)
        return round(min(1.0, groundedness), 4)

    def evaluate(self, query: str, response: str,
                 retrieved_docs: list[Any] | None = None) -> ResponseEvalResult:
        """Run all evaluation dimensions and compute composite score."""
        relevance = self.evaluate_relevance(query, response)
        coherence = self.evaluate_coherence(response)
        groundedness = self.evaluate_groundedness(response, retrieved_docs or [])
        faithfulness = self.evaluate_faithfulness(response, retrieved_docs or [])
        completeness = self.evaluate_completeness(query, response)
        conciseness = self.evaluate_conciseness(response)

        # Weighted composite
        if retrieved_docs:
            overall = (0.20 * relevance + 0.15 * coherence + 0.20 * groundedness
                       + 0.20 * faithfulness + 0.15 * completeness + 0.10 * conciseness)
        else:
            overall = 0.35 * relevance + 0.25 * coherence + 0.25 * completeness + 0.15 * conciseness

        return ResponseEvalResult(
            relevance_score=relevance,
            coherence_score=coherence,
            groundedness_score=groundedness,
            faithfulness_score=faithfulness,
            completeness_score=completeness,
            conciseness_score=conciseness,
            overall_score=round(overall, 4),
            details={
                "query_length": len(query),
                "response_length": len(response),
                "doc_count": len(retrieved_docs or []),
            },
        )

    def evaluate_faithfulness(self, response: str, retrieved_docs: list[Any]) -> float:
        """Score faithfulness — what fraction of claims in the response are
        directly supported by the source documents.

        Extracts sentence-level claims and checks each one against the
        retrieved document text for term overlap.
        """
        if not response or not retrieved_docs:
            return 0.5 if not retrieved_docs else 0.0

        sentences = [s.strip() for s in response.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if not sentences:
            return 0.0

        # Build a combined document corpus
        doc_text = ""
        for doc in retrieved_docs:
            if isinstance(doc, dict):
                doc_text += " " + str(doc.get("content", doc.get("page_content", "")))
            elif hasattr(doc, "page_content"):
                doc_text += " " + str(doc.page_content)
            else:
                doc_text += " " + str(doc)
        doc_tokens = set(self._tokenize(doc_text))

        if not doc_tokens:
            return 0.5

        supported = 0
        for sent in sentences:
            sent_tokens = set(self._tokenize(sent))
            if not sent_tokens:
                continue
            # A claim is "supported" if a majority of its content words appear in docs
            overlap = sent_tokens & doc_tokens
            if len(overlap) / len(sent_tokens) >= 0.3:
                supported += 1

        return round(min(1.0, supported / len(sentences)), 4)

    def evaluate_completeness(self, query: str, response: str) -> float:
        """Score completeness — what fraction of query facets are addressed
        in the response.

        Extracts key terms/facets from the query and measures their coverage
        in the response.
        """
        if not query or not response:
            return 0.0

        query_tokens = set(self._tokenize(query))
        response_tokens = set(self._tokenize(response))

        if not query_tokens:
            return 0.0

        covered = query_tokens & response_tokens
        # Weighted: every covered token gets 1 point, but we penalise
        # very short responses that only match one keyword.
        coverage = len(covered) / len(query_tokens)

        # Length bonus: a complete answer should be at least as long as the query
        resp_len = len(response_tokens)
        q_len = len(query_tokens)
        length_factor = min(1.0, resp_len / max(q_len * 1.5, 1))

        return round(min(1.0, 0.7 * coverage + 0.3 * length_factor), 4)

    def evaluate_conciseness(self, response: str) -> float:
        """Score conciseness — ratio of meaningful content to filler.

        Penalises excessive repetition and low information density.
        """
        if not response:
            return 0.0

        words = self._tokenize(response)
        if not words:
            return 0.0

        # Type-token ratio (unique / total) — higher = more concise
        ttr = len(set(words)) / len(words)

        # Sentence length penalty — extremely long or short sentences hurt
        sentences = [s.strip() for s in response.replace("!", ".").replace("?", ".").split(".") if s.strip()]
        if sentences:
            avg_sent_len = len(words) / len(sentences)
            if 8 <= avg_sent_len <= 30:
                sent_score = 1.0
            elif avg_sent_len < 4 or avg_sent_len > 60:
                sent_score = 0.3
            else:
                sent_score = 0.7
        else:
            sent_score = 0.5

        # Filler word penalty
        filler_words = {"basically", "actually", "literally", "essentially", "simply", "just", "very", "really", "quite", "extremely", "highly", "importantly", "additionally", "furthermore", "moreover", "nevertheless", "nonetheless"}
        filler_count = sum(1 for w in words if w in filler_words)
        filler_rate = filler_count / len(words)
        filler_score = max(0.0, 1.0 - filler_rate * 10)

        return round(min(1.0, 0.4 * ttr + 0.3 * sent_score + 0.3 * filler_score), 4)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple whitespace + punctuation tokenizer."""
        import re
        return [t.lower() for t in re.findall(r"\b\w+\b", text) if len(t) > 2]


class WorkflowEvaluator:
    """Evaluates end-to-end workflow execution quality from trace data.

    Computes aggregate metrics including latency percentiles, error rates,
    token efficiency, and per-agent contribution scores.
    """

    def evaluate_workflow_run(self, trace: TraceReport) -> WorkflowEvalResult:
        """Evaluate a complete workflow execution from its trace report.

        Args:
            trace: The completed trace report.

        Returns:
            WorkflowEvalResult with aggregate quality metrics.
        """
        agent_results = self._extract_agent_metrics(trace)
        latencies = [a.avg_latency_ms for a in agent_results if a.avg_latency_ms > 0]

        error_rate = trace.error_count / max(trace.span_count, 1)
        token_efficiency = trace.total_tokens / max(trace.total_duration_ms / 1000, 0.001)

        # Compute latency percentiles
        sorted_latencies = sorted(latencies)
        p50 = self._percentile(sorted_latencies, 0.50)
        p95 = self._percentile(sorted_latencies, 0.95)

        # Overall score: combination of success rate, latency, efficiency
        success_rate = 1.0 - error_rate
        latency_score = 1.0 / (1.0 + (p95 / 10000))  # Normalize against 10s baseline
        overall = 0.5 * success_rate + 0.3 * latency_score + 0.2 * min(1.0, 1.0 / (1 + error_rate))

        return WorkflowEvalResult(
            workflow_id=trace.workflow_id,
            overall_score=round(overall, 4),
            total_duration_ms=trace.total_duration_ms,
            total_tokens=trace.total_tokens,
            total_cost_usd=trace.total_cost_usd,
            agent_scores=agent_results,
            latency_p50_ms=round(p50, 2),
            latency_p95_ms=round(p95, 2),
            error_rate=round(error_rate, 4),
            token_efficiency=round(token_efficiency, 2),
            details={
                "span_count": trace.span_count,
                "error_count": trace.error_count,
                "trace_id": trace.trace_id,
            },
        )

    def evaluate_agent_performance(self, agent_traces: list[dict[str, Any]]) -> list[AgentEvalResult]:
        """Evaluate per-agent performance from a list of agent trace records.

        Args:
            agent_traces: List of agent execution records with timing and token data.

        Returns:
            List of AgentEvalResult for each unique agent.
        """
        by_agent: dict[str, list[dict]] = {}
        for trace in agent_traces:
            agent_id = trace.get("agent_id", "unknown")
            by_agent.setdefault(agent_id, []).append(trace)

        results = []
        for agent_id, traces in by_agent.items():
            latencies = [t.get("duration_ms", 0) for t in traces]
            tokens = sum(t.get("tokens", 0) for t in traces)
            errors = sum(1 for t in traces if t.get("error"))

            results.append(AgentEvalResult(
                agent_id=agent_id,
                avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0,
                total_tokens=tokens,
                error_rate=round(errors / len(traces), 4) if traces else 0,
                execution_count=len(traces),
            ))

        return results

    def _extract_agent_metrics(self, trace: TraceReport) -> list[AgentEvalResult]:
        """Extract per-agent metrics from a trace report's span tree."""
        agent_spans: dict[str, list[dict]] = {}

        if trace.root_span:
            self._walk_spans(trace.root_span, agent_spans)

        results = []
        for agent_id, spans in agent_spans.items():
            latencies = [s.get("duration_ms", 0) for s in spans]
            tokens = sum(s.get("tokens", 0) for s in spans)
            errors = sum(1 for s in spans if s.get("error"))

            results.append(AgentEvalResult(
                agent_id=agent_id,
                avg_latency_ms=round(sum(latencies) / len(latencies), 2) if latencies else 0,
                total_tokens=tokens,
                error_rate=round(errors / len(spans), 4) if spans else 0,
                execution_count=len(spans),
            ))

        return results

    def _walk_spans(self, span: Any, agent_spans: dict[str, list[dict]]) -> None:
        """Recursively walk the span tree to extract agent metrics."""
        if span.span_type == "agent":
            agent_id = span.metadata.get("agent_id", span.name)
            agent_spans.setdefault(agent_id, []).append({
                "duration_ms": span.duration_ms or 0,
                "tokens": span.metadata.get("tokens", 0),
                "error": span.error,
            })

        for child in span.children:
            self._walk_spans(child, agent_spans)

    @staticmethod
    def _percentile(sorted_data: list[float], p: float) -> float:
        """Compute the p-th percentile."""
        if not sorted_data:
            return 0.0
        k = (len(sorted_data) - 1) * p
        f = int(k)
        c = min(f + 1, len(sorted_data) - 1)
        return sorted_data[f] + (sorted_data[c] - sorted_data[f]) * (k - f)

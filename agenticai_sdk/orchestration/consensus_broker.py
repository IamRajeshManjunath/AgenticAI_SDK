"""
Agent-to-Agent Consensus Broker — spin up parallel agent instances with varied
system prompts and execute downstream changes only upon majority consensus.

Uses asyncio.gather for concurrent execution and text similarity for agreement
scoring across parallel instance responses.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import time
from typing import Any

import structlog
from pydantic import BaseModel, Field

from agenticai_sdk.exceptions import ConsensusNotReachedError
from agenticai_sdk.schemas.agent_node import AgentNodeConfig
from agenticai_sdk.schemas.middleware_config import ConsensusConfig

logger = structlog.get_logger(__name__)


class ConsensusResult(BaseModel):
    """Result of a consensus execution across parallel agent instances.

    Attributes:
        agreed: Whether majority consensus was reached.
        confidence: Agreement confidence score (0.0–1.0).
        majority_response: The response selected by majority vote.
        all_responses: List of all parallel instance responses.
        dissenting_indices: Indices of instances that dissented.
        execution_time_ms: Total wall-clock time for parallel execution.
    """

    agreed: bool
    confidence: float
    majority_response: dict[str, Any]
    all_responses: list[dict[str, Any]]
    dissenting_indices: list[int] = Field(default_factory=list)
    execution_time_ms: float = 0.0


class ConsensusBroker:
    """Executes parallel agent instances and evaluates majority consensus.

    For high-stakes decisions, spins up N parallel instances with varied
    system prompts (temperature variations, rephrased instructions).
    Proceeds with downstream execution only upon majority agreement.

    Usage::

        broker = ConsensusBroker()
        result = await broker.execute_consensus(
            agent_config=config,
            state=current_state,
            runner_factory=deep_agent_factory,
            resolved_llm=llm,
            resolved_tools=tools,
        )
        if result.agreed:
            final = result.majority_response
    """

    async def execute_consensus(
        self,
        agent_config: AgentNodeConfig,
        state: dict[str, Any],
        runner_factory: Any,
        resolved_llm: Any,
        resolved_tools: list,
        retrieved_docs: list | None = None,
        config: ConsensusConfig | None = None,
    ) -> ConsensusResult:
        """Spin up parallel agent instances and evaluate consensus.

        Args:
            agent_config: The agent node configuration.
            state: Current WorkflowState.
            runner_factory: DeepAgentFactory instance.
            resolved_llm: The resolved LLM client.
            resolved_tools: List of resolved tool instances.
            retrieved_docs: Pre-retrieved RAG documents.
            config: Consensus configuration (defaults from agent_config).

        Returns:
            ConsensusResult with agreement score and majority response.
        """
        consensus_config = config or agent_config.consensus_config or ConsensusConfig()
        num_instances = consensus_config.instances
        temp_range = consensus_config.varied_temperature_range

        logger.info(
            "consensus_execution_start",
            agent_id=agent_config.agent_id,
            instances=num_instances,
            threshold=consensus_config.threshold,
        )

        start_ts = time.perf_counter()

        # Generate varied temperature values
        temperatures = self._generate_temperatures(
            num_instances, temp_range[0], temp_range[1]
        )

        # Create parallel runners with varied configs
        tasks = []
        for i in range(num_instances):
            varied_config = self._create_varied_config(agent_config, temperatures[i], i)

            # Create a fresh LLM instance for varied temperature
            from agenticai_sdk.runtime.llm_factory import LLMClientFactory
            factory = LLMClientFactory()
            varied_llm = factory.create(varied_config.llm)

            runner = runner_factory.create_deep_agent(
                config=varied_config,
                resolved_llm=varied_llm,
                resolved_tools=resolved_tools,
                retrieved_docs=retrieved_docs or [],
            )

            # Deep copy state for each instance
            instance_state = copy.deepcopy(state)
            tasks.append(self._run_instance(runner, instance_state, i))

        # Execute all instances concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        elapsed_ms = round((time.perf_counter() - start_ts) * 1000, 2)

        # Filter successful results
        successful_results: list[tuple[int, dict[str, Any]]] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(
                    "consensus_instance_failed",
                    instance=i,
                    error=str(result),
                )
            else:
                successful_results.append((i, result))

        if not successful_results:
            raise ConsensusNotReachedError(
                f"All {num_instances} consensus instances failed for agent "
                f"'{agent_config.agent_id}'.",
                detail={"agent_id": agent_config.agent_id},
            )

        # Evaluate consensus
        consensus_result = self._evaluate_consensus(
            successful_results,
            consensus_config.threshold,
            elapsed_ms,
        )

        logger.info(
            "consensus_execution_complete",
            agent_id=agent_config.agent_id,
            agreed=consensus_result.agreed,
            confidence=consensus_result.confidence,
            elapsed_ms=elapsed_ms,
            successful_instances=len(successful_results),
            total_instances=num_instances,
        )

        return consensus_result

    def execute_if_consensus(
        self,
        consensus_result: ConsensusResult,
        threshold: float = 0.66,
    ) -> dict[str, Any]:
        """Return majority response only if consensus threshold is met.

        Args:
            consensus_result: Result from execute_consensus().
            threshold: Minimum confidence required.

        Returns:
            The majority response dict.

        Raises:
            ConsensusNotReachedError: If confidence < threshold.
        """
        if consensus_result.confidence < threshold:
            raise ConsensusNotReachedError(
                f"Consensus confidence ({consensus_result.confidence:.2f}) "
                f"below threshold ({threshold:.2f}).",
                detail={
                    "confidence": consensus_result.confidence,
                    "threshold": threshold,
                    "dissenting": consensus_result.dissenting_indices,
                },
            )
        return consensus_result.majority_response

    async def _run_instance(
        self,
        runner: Any,
        state: dict[str, Any],
        instance_idx: int,
    ) -> dict[str, Any]:
        """Execute a single agent instance."""
        try:
            result = await runner(state)
            return result
        except Exception as exc:
            logger.warning(
                "consensus_instance_error",
                instance=instance_idx,
                error=str(exc),
            )
            raise

    def _evaluate_consensus(
        self,
        results: list[tuple[int, dict[str, Any]]],
        threshold: float,
        elapsed_ms: float,
    ) -> ConsensusResult:
        """Evaluate agreement across parallel instance responses.

        Uses text similarity on the final AI message content to determine
        agreement. Groups responses by similarity clusters.
        """
        if len(results) == 1:
            return ConsensusResult(
                agreed=True,
                confidence=1.0,
                majority_response=results[0][1],
                all_responses=[r[1] for r in results],
                dissenting_indices=[],
                execution_time_ms=elapsed_ms,
            )

        # Extract response texts for comparison
        response_texts: list[str] = []
        for _, result in results:
            messages = result.get("messages", [])
            if messages:
                last_msg = messages[-1]
                content = getattr(last_msg, "content", "") if hasattr(last_msg, "content") else str(last_msg)
                response_texts.append(str(content))
            else:
                response_texts.append("")

        # Compute pairwise similarity using content hashing + text overlap
        similarity_matrix = self._compute_similarity_matrix(response_texts)

        # Find the response with highest average similarity (majority)
        avg_similarities = []
        for i in range(len(response_texts)):
            avg_sim = sum(similarity_matrix[i]) / len(similarity_matrix[i])
            avg_similarities.append(avg_sim)

        majority_idx = avg_similarities.index(max(avg_similarities))
        confidence = avg_similarities[majority_idx]

        # Identify dissenting instances
        dissenting = []
        for i in range(len(results)):
            if i != majority_idx and similarity_matrix[majority_idx][i] < threshold:
                dissenting.append(results[i][0])

        agreed = confidence >= threshold

        return ConsensusResult(
            agreed=agreed,
            confidence=round(confidence, 4),
            majority_response=results[majority_idx][1],
            all_responses=[r[1] for r in results],
            dissenting_indices=dissenting,
            execution_time_ms=elapsed_ms,
        )

    @staticmethod
    def _compute_similarity_matrix(texts: list[str]) -> list[list[float]]:
        """Compute pairwise similarity between response texts.

        Uses a combination of word-level Jaccard similarity and
        character n-gram overlap for robust comparison.
        """
        n = len(texts)
        matrix = [[1.0] * n for _ in range(n)]

        for i in range(n):
            for j in range(i + 1, n):
                sim = _text_similarity(texts[i], texts[j])
                matrix[i][j] = sim
                matrix[j][i] = sim

        return matrix

    @staticmethod
    def _generate_temperatures(
        count: int, low: float, high: float
    ) -> list[float]:
        """Generate evenly-spaced temperature values."""
        if count == 1:
            return [(low + high) / 2]
        step = (high - low) / (count - 1)
        return [round(low + i * step, 2) for i in range(count)]

    @staticmethod
    def _create_varied_config(
        base_config: AgentNodeConfig,
        temperature: float,
        instance_idx: int,
    ) -> AgentNodeConfig:
        """Create a varied config with modified temperature."""
        config_dict = base_config.model_dump()
        config_dict["llm"]["temperature"] = temperature
        return AgentNodeConfig(**config_dict)


def _text_similarity(text_a: str, text_b: str) -> float:
    """Compute similarity between two texts using word-level Jaccard + n-gram overlap."""
    if not text_a and not text_b:
        return 1.0
    if not text_a or not text_b:
        return 0.0

    # Word-level Jaccard similarity
    words_a = set(text_a.lower().split())
    words_b = set(text_b.lower().split())
    if not words_a and not words_b:
        return 1.0
    jaccard = len(words_a & words_b) / len(words_a | words_b) if words_a | words_b else 0.0

    # Character 3-gram overlap
    ngrams_a = set(_char_ngrams(text_a.lower(), 3))
    ngrams_b = set(_char_ngrams(text_b.lower(), 3))
    ngram_sim = len(ngrams_a & ngrams_b) / len(ngrams_a | ngrams_b) if ngrams_a | ngrams_b else 0.0

    # Weighted average
    return 0.5 * jaccard + 0.5 * ngram_sim


def _char_ngrams(text: str, n: int) -> list[str]:
    """Generate character n-grams from text."""
    return [text[i:i + n] for i in range(len(text) - n + 1)]

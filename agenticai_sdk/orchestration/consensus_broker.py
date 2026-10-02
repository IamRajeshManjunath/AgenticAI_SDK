"""Consensus Broker - Multi-instance agreement with similarity scoring.

Supports multiple consensus strategies:
- Majority Vote: Simple majority of instances
- Weighted Majority: Weighted by instance confidence
- Threshold: Require minimum agreement score
- Unanimous: All instances must agree
- Judge: Use a judge model to evaluate and select best
"""

from __future__ import annotations

import asyncio
import json
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Type

import structlog
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agenticai_sdk.config.schemas import AgenticAIConfig, ConsensusConfig
from agenticai_sdk.runtime.model_registry import ModelRegistry

logger = structlog.get_logger(__name__)


@dataclass
class ConsensusInstance:
    """Result from a single consensus instance."""
    instance_id: str
    model_id: str
    response: Any
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class ConsensusResult:
    """Result of consensus execution."""
    agreed: bool
    consensus_value: Any
    confidence: float
    instances: List[ConsensusInstance]
    strategy: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConsensusStrategy(ABC):
    """Abstract base class for consensus strategies."""
    
    @abstractmethod
    async def execute(
        self,
        instances: List[ConsensusInstance],
        config: ConsensusConfig,
    ) -> ConsensusResult:
        """Execute consensus strategy on instance responses."""
        pass
    
    def _calculate_similarity(self, a: str, b: str) -> float:
        """Calculate text similarity between two responses."""
        # Simple Jaccard similarity on word tokens
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        
        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union)


def _text_similarity(a: str, b: str) -> float:
    """Calculate text similarity between two strings (Jaccard similarity)."""
    words_a = set(a.lower().split())
    words_b = set(b.lower().split())
    
    if not words_a and not words_b:
        return 1.0
    if not words_a or not words_b:
        return 0.0
    
    intersection = words_a & words_b
    union = words_a | words_b
    
    return len(intersection) / len(union)


class ConsensusBroker:
    """Orchestrates consensus execution across multiple model instances."""
    
    @staticmethod
    def _generate_temperatures(num_instances: int, min_temp: float, max_temp: float) -> List[float]:
        """Generate temperature values spread around base temperature."""
        if num_instances == 1:
            return [(min_temp + max_temp) / 2]
        
        return [
            min_temp + (max_temp - min_temp) * i / (num_instances - 1)
            for i in range(num_instances)
        ]
    
    # ... existing ConsensusStrategy class and other code ...


class MajorityVoteStrategy:
    """Simple majority vote consensus."""
    
    async def execute(
        self,
        instances: List[ConsensusInstance],
        config: ConsensusConfig,
    ) -> ConsensusResult:
        # Group by response content
        response_groups: Dict[str, List[ConsensusInstance]] = {}
        
        for inst in instances:
            if inst.error:
                continue
            # Serialize response for grouping
            response_key = json.dumps(inst.response, sort_keys=True, default=str)
            if response_key not in response_groups:
                response_groups[response_key] = []
            response_groups[response_key].append(inst)
        
        if not response_groups:
            return ConsensusResult(
                agreed=False,
                consensus_value=None,
                confidence=0.0,
                instances=instances,
                strategy="majority_vote",
                metadata={"error": "All instances failed"},
            )
        
        # Find majority
        total = len([i for i in instances if not i.error])
        best_group = max(response_groups.values(), key=len)
        agreed = len(best_group) >= (total / 2 + 0.5)  # Strict majority
        
        # Calculate confidence
        confidence = len(best_group) / total if total > 0 else 0
        
        return ConsensusResult(
            agreed=agreed,
            consensus_value=best_group[0].response if agreed else None,
            confidence=confidence,
            instances=instances,
            strategy="majority_vote",
            metadata={
                "group_sizes": {k: len(v) for k, v in response_groups.items()},
                "total_valid": total,
            },
        )


class WeightedMajorityStrategy:
    """Weighted majority vote based on instance confidence."""
    
    async def execute(
        self,
        instances: List[ConsensusInstance],
        config: ConsensusConfig,
    ) -> ConsensusResult:
        response_weights: Dict[str, float] = {}
        response_instances: Dict[str, List[ConsensusInstance]] = {}
        
        for inst in instances:
            if inst.error:
                continue
            response_key = json.dumps(inst.response, sort_keys=True, default=str)
            if response_key not in response_weights:
                response_weights[response_key] = 0.0
                response_instances[response_key] = []
            response_weights[response_key] += inst.confidence
            response_instances[response_key].append(inst)
        
        if not response_weights:
            return ConsensusResult(
                agreed=False,
                consensus_value=None,
                confidence=0.0,
                instances=instances,
                strategy="weighted_majority",
                metadata={"error": "All instances failed"},
            )
        
        # Find highest weighted response
        best_response = max(response_weights, key=response_weights.get)
        total_weight = sum(response_weights.values())
        best_weight = response_weights[best_response]
        
        agreed = best_weight / total_weight >= config.threshold if total_weight > 0 else False
        confidence = best_weight / total_weight if total_weight > 0 else 0
        
        return ConsensusResult(
            agreed=agreed,
            consensus_value=response_instances[best_response][0].response if agreed else None,
            confidence=confidence,
            instances=instances,
            strategy="weighted_majority",
            metadata={
                "weights": response_weights,
                "threshold": config.threshold,
            },
        )


class ThresholdStrategy:
    """Threshold-based consensus requiring minimum similarity."""
    
    async def execute(
        self,
        instances: List[ConsensusInstance],
        config: ConsensusConfig,
    ) -> ConsensusResult:
        valid_instances = [i for i in instances if not i.error]
        
        if not valid_instances:
            return ConsensusResult(
                agreed=False,
                consensus_value=None,
                confidence=0.0,
                instances=instances,
                strategy="threshold",
                metadata={"error": "All instances failed"},
            )
        
        if len(valid_instances) == 1:
            return ConsensusResult(
                agreed=True,
                consensus_value=valid_instances[0].response,
                confidence=valid_instances[0].confidence,
                instances=instances,
                strategy="threshold",
            )
        
        # Compare all pairs for similarity
        responses = [json.dumps(i.response, sort_keys=True, default=str) for i in valid_instances]
        
        # Find the most similar pair
        max_similarity = 0.0
        best_pair = None
        
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                sim = self._calculate_similarity(responses[i], responses[j])
                if sim > max_similarity:
                    max_similarity = sim
                    best_pair = (i, j)
        
        agreed = max_similarity >= config.threshold
        
        return ConsensusResult(
            agreed=agreed,
            consensus_value=valid_instances[best_pair[0]].response if agreed and best_pair else None,
            confidence=max_similarity,
            instances=instances,
            strategy="threshold",
            metadata={
                "max_similarity": max_similarity,
                "threshold": config.threshold,
            },
        )
    
    def _calculate_similarity(self, a: str, b: str) -> float:
        """Calculate text similarity between two responses."""
        # Simple Jaccard similarity on word tokens
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        
        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union)


class UnanimousStrategy:
    """Unanimous consensus - all instances must agree exactly."""
    
    async def execute(
        self,
        instances: List[ConsensusInstance],
        config: ConsensusConfig,
    ) -> ConsensusResult:
        valid_instances = [i for i in instances if not i.error]
        
        if not valid_instances:
            return ConsensusResult(
                agreed=False,
                consensus_value=None,
                confidence=0.0,
                instances=instances,
                strategy="unanimous",
                metadata={"error": "All instances failed"},
            )
        
        # Check if all responses are identical
        first_response = json.dumps(valid_instances[0].response, sort_keys=True, default=str)
        all_agree = all(
            json.dumps(i.response, sort_keys=True, default=str) == first_response
            for i in valid_instances
        )
        
        confidence = 1.0 if all_agree else 0.0
        
        return ConsensusResult(
            agreed=all_agree,
            consensus_value=valid_instances[0].response if all_agree else None,
            confidence=confidence,
            instances=instances,
            strategy="unanimous",
            metadata={"valid_count": len(valid_instances)},
        )


class JudgeStrategy:
    """Use a judge model to evaluate and select best response."""
    
    def __init__(self, judge_model: Optional[BaseChatModel] = None):
        self.judge_model = judge_model
    
    async def execute(
        self,
        instances: List[ConsensusInstance],
        config: ConsensusConfig,
    ) -> ConsensusResult:
        valid_instances = [i for i in instances if not i.error]
        
        if not valid_instances:
            return ConsensusResult(
                agreed=False,
                consensus_value=None,
                confidence=0.0,
                instances=instances,
                strategy="judge",
                metadata={"error": "All instances failed"},
            )
        
        if len(valid_instances) == 1:
            return ConsensusResult(
                agreed=True,
                consensus_value=valid_instances[0].response,
                confidence=valid_instances[0].confidence,
                instances=instances,
                strategy="judge",
            )
        
        if not self.judge_model:
            # Fallback to threshold strategy
            threshold_strategy = ThresholdStrategy()
            return await threshold_strategy.execute(instances, config)
        
        # Build evaluation prompt
        responses_text = "\n\n".join([
            f"Response {i+1}:\n{json.dumps(inst.response, indent=2, default=str)}"
            for i, inst in enumerate(valid_instances)
        ])
        
        judge_prompt = f"""You are an expert evaluator. Review the following responses and select the best one based on:
1. Accuracy and correctness
2. Completeness
3. Clarity and structure
4. Relevance to the task

Responses:
{responses_text}

Output your decision as JSON:
{{
    "selected_index": <0-based index of best response>,
    "confidence": <0.0-1.0>,
    "reasoning": "<brief explanation>"
}}"""
        
        try:
            messages = [
                SystemMessage(content="You are an expert evaluator."),
                HumanMessage(content=judge_prompt),
            ]
            
            response = await self.judge_model.ainvoke(messages)
            result = json.loads(response.content)
            
            selected_idx = result.get("selected_index", 0)
            confidence = result.get("confidence", 0.5)
            
            if 0 <= selected_idx < len(valid_instances):
                selected = valid_instances[selected_idx]
                return ConsensusResult(
                    agreed=True,
                    consensus_value=selected.response,
                    confidence=confidence,
                    instances=instances,
                    strategy="judge",
                    metadata={
                        "reasoning": result.get("reasoning"),
                        "all_scores": result.get("all_scores", []),
                    },
                )
        except Exception as e:
            logger.warning("judge_evaluation_failed", error=str(e))
        
        # Fallback
        threshold_strategy = ThresholdStrategy()
        return await threshold_strategy.execute(instances, config)


class CustomStrategy:
    """Custom strategy using a user-provided function."""
    
    def __init__(self, custom_fn: Callable[[List[ConsensusInstance], ConsensusConfig], ConsensusResult]):
        self.custom_fn = custom_fn
    
    async def execute(
        self,
        instances: List[ConsensusInstance],
        config: ConsensusConfig,
    ) -> ConsensusResult:
        return self.custom_fn(instances, config)


class ConsensusBroker:
    """Orchestrates consensus execution across multiple model instances."""
    
    STRATEGIES: Dict[str, Type] = {
        "majority": MajorityVoteStrategy,
        "weighted": WeightedMajorityStrategy,
        "threshold": ThresholdStrategy,
        "unanimous": UnanimousStrategy,
        "judge": JudgeStrategy,
    }
    
    def __init__(
        self,
        registry: ModelRegistry,
        judge_model: Optional[BaseChatModel] = None,
    ):
        self.registry = registry
        self.judge_model = judge_model
        self._strategy_cache: Dict[str, Type] = {}
    
    @staticmethod
    def _generate_temperatures(num_instances: int, min_temp: float, max_temp: float) -> List[float]:
        """Generate temperature values spread around base temperature."""
        if num_instances == 1:
            return [(min_temp + max_temp) / 2]
        
        return [
            min_temp + (max_temp - min_temp) * i / (num_instances - 1)
            for i in range(num_instances)
        ]
    
    def _get_strategy(self, strategy_name: str) -> Type:
        """Get or create strategy instance."""
        if strategy_name not in self._strategy_cache:
            strategy_class = self.STRATEGIES.get(strategy_name)
            if not strategy_class:
                raise ValueError(f"Unknown consensus strategy: {strategy_name}")
            
            if strategy_class == JudgeStrategy:
                self._strategy_cache[strategy_name] = JudgeStrategy(self.judge_model)
            else:
                self._strategy_cache[strategy_name] = strategy_class()
        
        return self._strategy_cache[strategy_name]
    
    async def execute_consensus(
        self,
        agent_config: Any,
        state: Dict[str, Any],
        runner_factory: Any,
        resolved_llm: Any,
        resolved_tools: List[Any],
        retrieved_docs: List[Any],
    ) -> ConsensusResult:
        """Execute consensus across multiple model instances."""
        consensus_config = agent_config.consensus_config
        
        if not consensus_config or not consensus_config.enabled:
            raise ValueError("Consensus not enabled for this agent")
        
        strategy_name = consensus_config.strategy if hasattr(consensus_config, 'strategy') else "majority"
        strategy = self._get_strategy(strategy_name)
        
        # Generate multiple instances
        instances = await self._generate_instances(
            agent_config=agent_config,
            state=state,
            runner_factory=runner_factory,
            resolved_llm=resolved_llm,
            resolved_tools=resolved_tools,
            retrieved_docs=retrieved_docs,
            num_instances=consensus_config.instances,
            temperatures=consensus_config.temperatures if hasattr(consensus_config, 'temperatures') else None,
        )
        
        # Execute consensus strategy
        consensus_config_obj = ConsensusConfig(
            enabled=True,
            instances=consensus_config.instances,
            threshold=consensus_config.threshold,
        )
        
        result = await strategy.execute(instances, consensus_config_obj)
        
        logger.info("consensus_completed",
                   strategy=strategy_name,
                   agreed=result.agreed,
                   confidence=result.confidence,
                   instance_count=len(instances))
        
        return result
    
    async def _generate_instances(
        self,
        agent_config: Any,
        state: Dict[str, Any],
        runner_factory: Any,
        resolved_llm: Any,
        resolved_tools: List[Any],
        retrieved_docs: List[Any],
        num_instances: int,
        temperatures: Optional[List[float]] = None,
    ) -> List[ConsensusInstance]:
        """Generate multiple instances for consensus."""
        instances = []
        
        # Use provided temperatures or generate varied ones
        if temperatures is None:
            # Generate temperatures spread around base temperature
            base_temp = 0.7
            temperatures = [
                max(0.0, min(1.0, base_temp + (i - num_instances // 2) * 0.2))
                for i in range(num_instances)
            ]
        
        for i in range(num_instances):
            temp = temperatures[i] if i < len(temperatures) else 0.7
            
            instance_id = str(uuid.uuid4())[:8]
            
            try:
                # Execute instance
                runner = runner_factory(
                    config=agent_config,
                    resolved_llm=resolved_llm,
                    resolved_tools=resolved_tools,
                    retrieved_docs=retrieved_docs,
                )
                
                result = await runner(state)
                
                instances.append(ConsensusInstance(
                    instance_id=instance_id,
                    model_id=f"{agent_config.llm.provider}:{agent_config.llm.model}",
                    response=result,
                    confidence=0.8,  # Base confidence
                ))
                
            except Exception as e:
                logger.warning("consensus_instance_failed", 
                              instance_id=instance_id, error=str(e))
                instances.append(ConsensusInstance(
                    instance_id=instance_id,
                    model_id=f"{agent_config.llm.provider}:{agent_config.llm.model}",
                    response=None,
                    error=str(e),
                ))
        
        return instances
    
    async def execute_if_consensus(self, consensus_result: ConsensusResult) -> Any:
        """Extract the consensus value if agreed, otherwise raise."""
        if not consensus_result.agreed:
            raise ConsensusNotReachedError(
                f"Consensus not reached: confidence={consensus_result.confidence}"
            )
        return consensus_result.consensus_value


class ConsensusNotReachedError(Exception):
    """Raised when consensus is not reached."""
    pass


def create_consensus_broker(
    registry: ModelRegistry,
    judge_model: Optional[BaseChatModel] = None,
) -> ConsensusBroker:
    """Factory function to create ConsensusBroker."""
    return ConsensusBroker(registry, judge_model)
"""Model Registry - Central registry for LLM models with fallback routing."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type

import structlog
from langchain_core.language_models import BaseChatModel

from agenticai_sdk.config.schemas import AgenticAIConfig, ChatModelConfig
from agenticai_sdk.runtime.llm_factory import LLMClientFactory

logger = structlog.get_logger(__name__)


@dataclass
class ModelAttempt:
    """Record of a model invocation attempt."""
    model_id: str
    provider: str
    timestamp: float
    success: bool
    error: Optional[str] = None
    latency_ms: float = 0
    tokens_used: int = 0


@dataclass
class ModelHealth:
    """Health status of a model."""
    model_id: str
    healthy: bool = True
    consecutive_failures: int = 0
    last_success: Optional[float] = None
    last_failure: Optional[float] = None
    total_requests: int = 0
    total_failures: int = 0
    avg_latency_ms: float = 0
    
    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.total_failures / self.total_requests


class ModelRegistry:
    """Registry for LLM models with health tracking and provider management."""
    
    def __init__(self, config: AgenticAIConfig):
        self.config = config
        self.llm_factory = LLMClientFactory()
        self._models: Dict[str, BaseChatModel] = {}
        self._model_configs: Dict[str, ChatModelConfig] = {}
        self._health: Dict[str, ModelHealth] = {}
        self._attempts: List[ModelAttempt] = []
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize all configured models."""
        for model_config in self.config.integrations.chat_models:
            if model_config.enabled:
                self._register_model(model_config)
        self._initialized = True
        logger.info("model_registry_initialized", model_count=len(self._models))
    
    def _register_model(self, config: ChatModelConfig) -> None:
        """Register a model configuration."""
        self._model_configs[config.id] = config
        self._health[config.id] = ModelHealth(model_id=config.id)
        
        # Lazy instantiate - create on first use
        logger.debug("model_registered", model_id=config.id, provider=config.provider, model=config.model)
    
    def get_model(self, model_id: str) -> BaseChatModel:
        """Get or create a model instance."""
        if model_id not in self._model_configs:
            raise ValueError(f"Model not found: {model_id}")
        
        if model_id not in self._models:
            config = self._model_configs[model_id]
            try:
                self._models[model_id] = self.llm_factory.create(config)
                logger.info("model_instantiated", model_id=model_id)
            except Exception as e:
                logger.error("model_instantiation_failed", model_id=model_id, error=str(e))
                raise
        
        return self._models[model_id]
    
    def get_config(self, model_id: str) -> Optional[ChatModelConfig]:
        """Get model configuration."""
        return self._model_configs.get(model_id)
    
    def get_primary_model(self) -> BaseChatModel:
        """Get the primary (highest priority) enabled model."""
        enabled = [m for m in self.config.integrations.chat_models if m.enabled]
        if not enabled:
            raise ValueError("No enabled chat models configured")
        
        primary = min(enabled, key=lambda m: m.priority)
        return self.get_model(primary.id)
    
    def get_fallback_models(self, primary_id: str) -> List[BaseChatModel]:
        """Get fallback models for a primary model."""
        primary_config = self.get_config(primary_id)
        if not primary_config:
            return []
        
        # Get all other enabled models as fallbacks, sorted by priority
        fallbacks = [
            m for m in self.config.integrations.chat_models
            if m.enabled and m.id != primary_id
        ]
        fallbacks.sort(key=lambda m: m.priority)
        
        return [self.get_model(m.id) for m in fallbacks]
    
    def list_models(self) -> List[Dict[str, Any]]:
        """List all registered models with their status."""
        result = []
        for model_id, config in self._model_configs.items():
            health = self._health.get(model_id)
            result.append({
                "id": config.id,
                "provider": config.provider,
                "model": config.model,
                "priority": config.priority,
                "enabled": config.enabled,
                "healthy": health.healthy if health else True,
                "failure_rate": health.failure_rate if health else 0,
                "avg_latency_ms": health.avg_latency_ms if health else 0,
            })
        return result
    
    def record_attempt(self, attempt: ModelAttempt) -> None:
        """Record a model invocation attempt for health tracking."""
        self._attempts.append(attempt)
        
        # Keep only recent attempts (last 1000)
        if len(self._attempts) > 1000:
            self._attempts = self._attempts[-1000:]
        
        # Update health
        health = self._health.get(attempt.model_id)
        if health:
            health.total_requests += 1
            if attempt.success:
                health.consecutive_failures = 0
                health.last_success = attempt.timestamp
                # Update rolling average latency
                health.avg_latency_ms = (
                    (health.avg_latency_ms * (health.total_requests - 1) + attempt.latency_ms)
                    / health.total_requests
                )
            else:
                health.consecutive_failures += 1
                health.total_failures += 1
                health.last_failure = attempt.timestamp
                # Mark unhealthy after 3 consecutive failures
                if health.consecutive_failures >= 3:
                    health.healthy = False
                    logger.warning("model_marked_unhealthy", model_id=attempt.model_id)
    
    def get_health(self, model_id: str) -> Optional[ModelHealth]:
        """Get health status for a model."""
        return self._health.get(model_id)
    
    def is_healthy(self, model_id: str) -> bool:
        """Check if model is healthy."""
        health = self._health.get(model_id)
        return health is None or health.healthy
    
    def reset_health(self, model_id: str) -> bool:
        """Reset health status for a model (e.g., after manual recovery)."""
        if model_id in self._health:
            self._health[model_id] = ModelHealth(model_id=model_id)
            logger.info("model_health_reset", model_id=model_id)
            return True
        return False


@dataclass
class FallbackPolicy:
    """Policy for model fallback behavior."""
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    exponential_backoff: bool = True
    max_backoff_seconds: float = 60.0
    retryable_errors: List[str] = field(default_factory=lambda: [
        "rate_limit",
        "timeout",
        "connection_error",
        "server_error",
        "unavailable",
    ])
    non_retryable_errors: List[str] = field(default_factory=lambda: [
        "invalid_request",
        "authentication_error",
        "permission_denied",
        "content_filter",
    ])


class FallbackRouter:
    """Routes requests through models with automatic fallback on failure."""
    
    def __init__(
        self,
        registry: ModelRegistry,
        policy: Optional[FallbackPolicy] = None,
    ):
        self.registry = registry
        self.policy = policy or FallbackPolicy()
        self._attempt_history: Dict[str, List[ModelAttempt]] = {}
    
    async def invoke_with_fallback(
        self,
        primary_model_id: str,
        invoke_fn: Callable[[BaseChatModel], Any],
        *args,
        **kwargs,
    ) -> Any:
        """Invoke function with automatic fallback on failure.
        
        Args:
            primary_model_id: Primary model to try first
            invoke_fn: Async function that takes a model and returns result
            *args, **kwargs: Additional arguments passed to invoke_fn
        
        Returns:
            Result from successful model invocation
        
        Raises:
            Last exception if all fallbacks exhausted
        """
        if not self.registry.is_healthy(primary_model_id):
            logger.warning("primary_model_unhealthy_trying_fallback", model_id=primary_model_id)
        
        # Build model chain: primary + fallbacks
        model_chain = [primary_model_id]
        fallbacks = self.registry.get_fallback_models(primary_model_id)
        model_chain.extend(fallbacks)
        
        last_exception = None
        
        for i, model_id in enumerate(model_chain):
            if not self.registry.is_healthy(model_id):
                logger.warning("skipping_unhealthy_model", model_id=model_id)
                continue
            
            model = self.registry.get_model(model_id)
            attempt_start = time.time()
            
            try:
                logger.info("model_invocation_attempt", 
                           model_id=model_id, attempt=i+1, total=len(model_chain))
                
                result = await invoke_fn(model, *args, **kwargs)
                
                # Record success
                latency = (time.time() - attempt_start) * 1000
                self.registry.record_attempt(ModelAttempt(
                    model_id=model_id,
                    provider=self.registry.get_config(model_id).provider if self.registry.get_config(model_id) else "unknown",
                    timestamp=time.time(),
                    success=True,
                    latency_ms=latency,
                ))
                
                logger.info("model_invocation_success", 
                           model_id=model_id, latency_ms=latency)
                
                return result
                
            except Exception as e:
                latency = (time.time() - attempt_start) * 1000
                error_type = self._classify_error(e)
                
                # Record failure
                self.registry.record_attempt(ModelAttempt(
                    model_id=model_id,
                    provider=self.registry.get_config(model_id).provider if self.registry.get_config(model_id) else "unknown",
                    timestamp=time.time(),
                    success=False,
                    error=str(e),
                    latency_ms=latency,
                ))
                
                last_exception = e
                logger.warning("model_invocation_failed",
                              model_id=model_id, error=str(e), error_type=error_type)
                
                # Check if we should retry
                if self._should_retry(error_type, i, len(model_chain)):
                    delay = self._calculate_delay(i)
                    logger.info("retrying_after_delay", delay_seconds=delay)
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error("fallback_exhausted_or_non_retryable",
                                model_id=model_id, error_type=error_type)
                    break
        
        # All attempts failed
        if last_exception:
            raise last_exception
        raise RuntimeError("All model fallbacks exhausted")
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type for retry logic."""
        error_str = str(error).lower()
        
        # Check non-retryable first
        for pattern in self.policy.non_retryable_errors:
            if pattern in error_str:
                return "non_retryable"
        
        # Check retryable
        for pattern in self.policy.retryable_errors:
            if pattern in error_str:
                return "retryable"
        
        # Default to retryable for unknown errors
        return "unknown"
    
    def _should_retry(self, error_type: str, attempt_index: int, total_models: int) -> bool:
        """Determine if we should retry with next model."""
        if error_type == "non_retryable":
            return False
        if attempt_index >= total_models - 1:
            return False  # Last model
        if attempt_index >= self.policy.max_retries:
            return False
        return True
    
    def _calculate_delay(self, attempt_index: int) -> float:
        """Calculate delay before retry."""
        if self.policy.exponential_backoff:
            delay = self.policy.retry_delay_seconds * (2 ** attempt_index)
        else:
            delay = self.policy.retry_delay_seconds
        return min(delay, self.policy.max_backoff_seconds)
    
    def get_attempt_history(self, model_id: Optional[str] = None) -> List[ModelAttempt]:
        """Get attempt history for a model or all models."""
        if model_id:
            return [a for a in self.registry._attempts if a.model_id == model_id]
        return self.registry._attempts.copy()


def create_model_registry(config: AgenticAIConfig) -> ModelRegistry:
    """Factory function to create and initialize ModelRegistry."""
    registry = ModelRegistry(config)
    registry.initialize()
    return registry


def create_fallback_router(
    registry: ModelRegistry,
    policy: Optional[FallbackPolicy] = None,
) -> FallbackRouter:
    """Factory function to create FallbackRouter."""
    return FallbackRouter(registry, policy)
"""Middleware Injector - Injects lifecycle-aware middleware into node execution.

Middleware chain (per spec §11):
Input → Authorization → PII Detection/Tokenization → Injection Detection → 
Budget Pre-check → Context Management → Node Execution → Output Validation → 
Cost Accounting → Authorized PII Restoration → Telemetry
"""

from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional, Type, Union

import structlog

from agenticai_sdk.config.schemas import AgenticAIConfig
from agenticai_sdk.middleware.base import MiddlewareBase, MiddlewareContext, MiddlewarePipeline, Direction

logger = structlog.get_logger(__name__)


class MiddlewareInjector:
    """Injects middleware into node execution pipeline."""
    
    def __init__(self, config: AgenticAIConfig):
        self.config = config
        self._middleware_cache: Dict[str, MiddlewarePipeline] = {}
    
    def get_pipeline_for_node(self, node_config: Any) -> MiddlewarePipeline:
        """Get or create middleware pipeline for a specific node."""
        cache_key = node_config.agent_id
        
        if cache_key in self._middleware_cache:
            return self._middleware_cache[cache_key]
        
        pipeline = self._build_pipeline(node_config)
        self._middleware_cache[cache_key] = pipeline
        return pipeline
    
    def _build_pipeline(self, node_config: Any) -> MiddlewarePipeline:
        """Build lifecycle-aware middleware pipeline for a node."""
        pipeline = MiddlewarePipeline()
        
        # Phase 1: Input validation & preprocessing
        pipeline.add(AuthorizationMiddleware())
        pipeline.add(PIIDetectionMiddleware(config=node_config.middleware_config.pii if node_config.middleware_config else None))
        pipeline.add(InjectionDetectionMiddleware(config=node_config.middleware_config.injection_firewall if node_config.middleware_config else None))
        pipeline.add(BudgetPrecheckMiddleware(config=node_config.middleware_config.budget if node_config.middleware_config else None))
        pipeline.add(ContextManagementMiddleware())
        
        # Phase 2: Node execution (handled by graph executor)
        
        # Phase 3: Output processing
        pipeline.add(OutputValidationMiddleware())
        pipeline.add(CostAccountingMiddleware())
        pipeline.add(PIIRestorationMiddleware())
        pipeline.add(TelemetryMiddleware())
        
        return pipeline
    
    def wrap_node_executor(
        self, 
        node_config: Any, 
        base_executor: Callable
    ) -> Callable:
        """Wrap node executor with middleware pipeline."""
        pipeline = self.get_pipeline_for_node(node_config)
        
        async def wrapped_executor(state: Dict[str, Any]) -> Dict[str, Any]:
            # Create middleware context
            context = MiddlewareContext(
                payload=state,
                metadata={},
                state=state,
                agent_id=node_config.agent_id,
                direction=Direction.INBOUND,
                workflow_id=state.get("workflow_id", ""),
                trace_id=state.get("trace_id"),
                workspace_id=state.get("workspace_id", ""),
            )
            
            # Run input middleware
            context = await pipeline.run_before(context)
            state = context.payload
            
            # Execute base node
            try:
                start_time = time.perf_counter()
                state = await base_executor(state)
                execution_time = time.perf_counter() - start_time
                state["execution_time_ms"] = execution_time * 1000
            except Exception as e:
                state["error"] = str(e)
                state["execution_failed"] = True
                raise
            
            # Run output middleware
            context.payload = state
            context.direction = Direction.OUTBOUND
            context = await pipeline.run_after(context)
            
            return context.payload
        
        return wrapped_executor


# --- Middleware Implementations ---

class AuthorizationMiddleware:
    """Authorization middleware - validates permissions."""
    
    @property
    def name(self) -> str:
        return "authorization"
    
    async def before(self, context) -> Any:
        # Authorization is handled at API gateway level
        # This is a no-op at node level
        return context
    
    async def after(self, context) -> Any:
        return context


class PIIDetectionMiddleware:
    """PII Detection + Tokenization middleware."""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self.enabled = getattr(config, "enabled", True) if config else True
        self.action = getattr(config, "action", "tokenize") if config else "tokenize"
    
    @property
    def name(self) -> str:
        return "pii_detection"
    
    async def before(self, context) -> Any:
        if not self.enabled:
            return context
        
        payload = context.payload
        if "messages" in payload:
            for msg in payload["messages"]:
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    # Detect and tokenize PII
                    tokenized, vault = self._detect_and_tokenize(msg.content)
                    if tokenized != msg.content:
                        msg.content = tokenized
                        context.metadata["pii_vault"] = vault
        
        return context
    
    async def after(self, context) -> Any:
        # PII restoration happens in PIIRestorationMiddleware
        return context
    
    def _detect_and_tokenize(self, text: str) -> tuple:
        """Detect PII and replace with tokens. Returns (tokenized_text, vault_map)."""
        import re
        
        vault = {}
        tokenized = text
        
        # Email pattern
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            token = f"<EMAIL_{len(vault)}>"
            vault[token] = match.group()
            tokenized = tokenized.replace(match.group(), token)
        
        # SSN pattern
        ssn_pattern = r'\b\d{3}-\d{2}-\d{4}\b'
        for match in re.finditer(ssn_pattern, text):
            token = f"<SSN_{len(vault)}>"
            vault[token] = match.group()
            tokenized = tokenized.replace(match.group(), token)
        
        return tokenized, vault


class InjectionDetectionMiddleware:
    """Prompt Injection Detection middleware."""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self.enabled = getattr(config, "enabled", True) if config else True
        self.mode = getattr(config, "mode", "block") if config else "block"
    
    @property
    def name(self) -> str:
        return "injection_detection"
    
    async def before(self, context) -> Any:
        if not self.enabled:
            return context
        
        payload = context.payload
        if "messages" in payload:
            for msg in payload["messages"]:
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    if self._detect_injection(msg.content):
                        if self.mode == "block":
                            raise InjectionDetectedError("Prompt injection detected")
                        elif self.mode == "sanitize":
                            msg.content = self._sanitize(msg.content)
                        elif self.mode == "hitl":
                            context.metadata["hitl_required"] = True
                            context.metadata["hitl_reason"] = "injection_detected"
        
        return context
    
    async def after(self, context) -> Any:
        return context
    
    def _detect_injection(self, text: str) -> bool:
        """Detect potential prompt injection."""
        injection_patterns = [
            r"ignore\s+previous\s+instructions",
            r"system\s*:\s*you\s+are",
            r"forget\s+everything",
            r"pretend\s+to\s+be",
            r"act\s+as\s+if",
            r"override\s+instructions",
            r"disregard\s+previous",
            r"new\s+instructions",
            r"forget\s+your\s+role",
        ]
        
        import re
        text_lower = text.lower()
        for pattern in injection_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                logger.warning("injection_detected", pattern=pattern)
                return True
        return False
    
    def _sanitize(self, text: str) -> str:
        """Sanitize potentially malicious input."""
        import re
        text = re.sub(r"ignore\s+previous\s+instructions", "[REDACTED]", text, flags=re.IGNORECASE)
        text = re.sub(r"system\s*:\s*you\s+are", "[REDACTED]", text, flags=re.IGNORECASE)
        return text


class BudgetPrecheckMiddleware:
    """Budget pre-check middleware - validates budget before execution."""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self.enabled = getattr(config, "enabled", True) if config else True
    
    @property
    def name(self) -> str:
        return "budget_precheck"
    
    async def before(self, context) -> Any:
        if not self.enabled:
            return context
        
        # Check if budget limits are already exceeded
        budget = context.metadata.get("budget", {})
        if budget.get("exceeded", False):
            raise BudgetExceededError("Budget exceeded before node execution")
        
        return context
    
    async def after(self, context) -> Any:
        return context


class ContextManagementMiddleware:
    """Context management - truncation, compression."""
    
    @property
    def name(self) -> str:
        return "context_management"
    
    async def before(self, context) -> Any:
        # Manage context window before node execution
        return context
    
    async def after(self, context) -> Any:
        return context


class OutputValidationMiddleware:
    """Validate node output against schema."""
    
    @property
    def name(self) -> str:
        return "output_validation"
    
    async def before(self, context) -> Any:
        return context
    
    async def after(self, context) -> Any:
        # Validate output against node's output_schema if defined
        return context


class CostAccountingMiddleware:
    """Track token usage and cost per node."""
    
    @property
    def name(self) -> str:
        return "cost_accounting"
    
    async def before(self, context) -> Any:
        context.metadata["node_start_time"] = time.perf_counter()
        return context
    
    async def after(self, context) -> Any:
        # Calculate cost from token usage
        token_usage = context.payload.get("token_usage", {})
        if token_usage:
            input_tokens = token_usage.get("input_tokens", 0)
            output_tokens = token_usage.get("output_tokens", 0)
            # Rough cost estimation (would use actual pricing in production)
            estimated_cost = (input_tokens * 0.00001) + (output_tokens * 0.00003)
            context.metadata["estimated_cost_usd"] = estimated_cost
            context.metadata["token_usage"] = token_usage
        
        execution_time = context.payload.get("execution_time_ms", 0)
        context.metadata["execution_time_ms"] = execution_time
        
        return context


class PIIRestorationMiddleware:
    """Restore PII at authorized boundaries."""
    
    def __init__(self, config: Optional[Any] = None):
        self.config = config
        self.enabled = getattr(config, "enabled", True) if config else True
        self.restore_at_boundaries = getattr(config, "restoreAtBoundaries", True) if config else True
    
    @property
    def name(self) -> str:
        return "pii_restoration"
    
    async def before(self, context) -> Any:
        return context
    
    async def after(self, context) -> Any:
        if not self.enabled or not self.restore_at_boundaries:
            return context
        
        vault = context.metadata.get("pii_vault")
        if vault and "messages" in context.payload:
            for msg in context.payload["messages"]:
                if hasattr(msg, "content") and isinstance(msg.content, str):
                    for token, original in vault.items():
                        msg.content = msg.content.replace(token, original)
        
        return context


class TelemetryMiddleware:
    """Emit telemetry events."""
    
    @property
    def name(self) -> str:
        return "telemetry"
    
    async def before(self, context) -> Any:
        return context
    
    async def after(self, context) -> Any:
        # Emit telemetry event
        event = {
            "event_type": "node_execution",
            "agent_id": context.agent_id,
            "workflow_id": context.workflow_id,
            "trace_id": context.trace_id,
            "execution_time_ms": context.payload.get("execution_time_ms", 0),
            "token_usage": context.payload.get("token_usage", {}),
            "estimated_cost_usd": context.metadata.get("estimated_cost_usd", 0),
            "status": "error" if context.payload.get("execution_failed") else "success",
        }
        
        # Emit to telemetry system (OpenTelemetry, etc.)
        logger.info("telemetry_event", **event)
        
        return context


# Custom exceptions
class InjectionDetectedError(Exception):
    pass


class BudgetExceededError(Exception):
    pass
"""
Domain-specific exceptions for the AgenticAI SDK.

Every exception inherits from AgenticSDKError to allow blanket catching
at the gateway boundary while preserving granular handling inside the engine.
"""

from __future__ import annotations


class AgenticSDKError(Exception):
    """Base exception for all AgenticAI SDK errors."""

    def __init__(self, message: str, *, detail: dict | None = None) -> None:
        self.detail = detail or {}
        super().__init__(message)


# ── Schema & Validation ──────────────────────────────────────────────────────

class SchemaValidationError(AgenticSDKError):
    """Raised when a Pydantic model fails structural or semantic validation."""


class PromptTemplateError(AgenticSDKError):
    """Raised when prompt template variables do not match declared input_variables."""


# ── Workflow Compilation ──────────────────────────────────────────────────────

class WorkflowCompilationError(AgenticSDKError):
    """Raised when the Orchestrator fails to compile a WorkflowSchema into a runnable graph."""


class GraphRoutingError(AgenticSDKError):
    """Raised when conditional edge evaluation fails during routing."""


# ── Tool Resolution ──────────────────────────────────────────────────────────

class ToolResolutionError(AgenticSDKError):
    """Raised when a referenced tool_id cannot be resolved from the global registry."""


class ToolExecutionError(AgenticSDKError):
    """Raised when a tool invocation fails at runtime."""


# ── LLM ──────────────────────────────────────────────────────────────────────

class LLMProviderError(AgenticSDKError):
    """Raised when an LLM provider cannot be instantiated or returns an error."""


# ── RAG / Knowledge Base ────────────────────────────────────────────────────

class RAGFetchException(AgenticSDKError):
    """Raised when a vector DB query or document retrieval operation fails."""


class VectorDBConnectionError(AgenticSDKError):
    """Raised when the vector database client cannot establish a connection."""


class EmbeddingError(AgenticSDKError):
    """Raised when the embedding provider fails to encode a query or document."""


# ── DeepAgent ────────────────────────────────────────────────────────────────

class DeepAgentExecutionError(AgenticSDKError):
    """Raised when the inner cognitive loop (create_deep_agent) encounters a fatal error."""


class DeepAgentFallbackExhausted(AgenticSDKError):
    """Raised when all fallback strategies (retry, escalate, halt) have been exhausted."""


# ── HITL ─────────────────────────────────────────────────────────────────────

class HITLTimeoutError(AgenticSDKError):
    """Raised when a human-in-the-loop approval exceeds the configured timeout."""


class HITLRejectError(AgenticSDKError):
    """Raised when a human reviewer explicitly rejects a workflow step."""


class HITLDispatchError(AgenticSDKError):
    """Raised when a HITL webhook notification dispatch fails."""


# ── Middleware ───────────────────────────────────────────────────────────────

class BudgetExceededError(AgenticSDKError):
    """Raised when a budget guardrail threshold (token or cost) is breached."""


class LoopTimeoutError(AgenticSDKError):
    """Raised when an agent loop exceeds the configured wall-clock time limit."""


class PIIMaskingError(AgenticSDKError):
    """Raised when PII vault encryption, decryption, or masking operation fails."""


class PromptInjectionDetectedError(AgenticSDKError):
    """Raised when adversarial prompt injection is detected in a payload."""


class ContextCompressionError(AgenticSDKError):
    """Raised when a context truncation or compression operation fails."""


# ── Orchestration ────────────────────────────────────────────────────────────

class SchemaMapperError(AgenticSDKError):
    """Raised when dynamic JSON schema normalization or mapping fails."""


class ConsensusNotReachedError(AgenticSDKError):
    """Raised when agent consensus threshold is not met across parallel instances."""


class FallbackExhaustedError(AgenticSDKError):
    """Raised when all fallback LLM providers have been exhausted."""


# ── Evaluation ───────────────────────────────────────────────────────────────

class EvaluationError(AgenticSDKError):
    """Raised when a quality evaluation or metrics computation fails."""

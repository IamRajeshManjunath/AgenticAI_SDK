"""
Middleware configuration schemas — per-agent and workflow-level middleware overrides.

Provides Pydantic V2 models for:
  - Budget guardrails (token/cost limits, loop timeouts)
  - PII masking (masking level, safe writeback agents)
  - Prompt injection firewall (threat threshold, allowlists)
  - Context compression (strategy, token limits)
  - Consensus (parallel instances, agreement threshold)
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class MaskingLevel(str, Enum):
    """PII masking intensity level."""

    FULL = "full"          # Complete redaction: [PII:type:uuid]
    PARTIAL = "partial"    # Last-4 visible: ****-****-****-1234
    HASH = "hash"          # SHA-256 hash replacement


class CompressionStrategy(str, Enum):
    """Strategy for context window compression."""

    TRUNCATE = "truncate"          # Sliding-window drop of oldest messages
    SUMMARIZE = "summarize"        # LLM-based summarization of middle section
    DROP_SCHEMAS = "drop_schemas"  # Remove redundant tool schema descriptions


class BudgetConfig(BaseModel):
    """Token and cost budget guardrail configuration.

    Attributes:
        max_tokens_per_call: Maximum tokens allowed per single LLM invocation.
        max_cost_per_workflow: Maximum cumulative USD cost for the entire workflow run.
        loop_timeout_seconds: Wall-clock timeout for a single agent node execution.
        max_loop_iterations: Maximum reasoning loop iterations per agent.
    """

    max_tokens_per_call: int = Field(
        default=8192,
        ge=64,
        le=128000,
        description="Maximum tokens allowed per single LLM invocation.",
    )
    max_cost_per_workflow: float = Field(
        default=5.0,
        gt=0,
        description="Maximum cumulative USD cost for the entire workflow run.",
    )
    loop_timeout_seconds: float = Field(
        default=300.0,
        gt=0,
        description="Wall-clock timeout in seconds for a single agent node execution.",
    )
    max_loop_iterations: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum reasoning loop iterations per agent node.",
    )


class PIIConfig(BaseModel):
    """PII/PHI masking configuration.

    Attributes:
        enabled: Whether PII masking is active.
        masking_level: How aggressively to mask detected PII.
        safe_writeback_agents: Agent IDs allowed to receive unmasked data during DB write-back.
        custom_patterns: Additional regex patterns to detect as PII (pattern_name -> regex_string).
    """

    enabled: bool = Field(default=True, description="Enable/disable PII masking.")
    masking_level: MaskingLevel = Field(
        default=MaskingLevel.FULL,
        description="Masking intensity: full, partial (last-4), or hash (SHA-256).",
    )
    safe_writeback_agents: list[str] = Field(
        default_factory=list,
        description="Agent IDs allowed to receive unmasked PII during database write-back steps.",
    )
    custom_patterns: dict[str, str] = Field(
        default_factory=dict,
        description="Custom regex patterns for PII detection (name -> regex string).",
    )


class InjectionFirewallConfig(BaseModel):
    """Prompt injection firewall configuration.

    Attributes:
        enabled: Whether the firewall is active.
        threat_threshold: Similarity score threshold (0.0–1.0) above which an input is flagged.
        allowlisted_patterns: Regex patterns for known-safe content that bypasses the firewall.
        block_on_detection: If True, raise an error; if False, log a warning and sanitize.
    """

    enabled: bool = Field(default=True, description="Enable/disable prompt injection firewall.")
    threat_threshold: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="Cosine similarity threshold for semantic injection detection.",
    )
    allowlisted_patterns: list[str] = Field(
        default_factory=list,
        description="Regex patterns for content that bypasses the firewall.",
    )
    block_on_detection: bool = Field(
        default=True,
        description="If True, block execution on detection. If False, sanitize and warn.",
    )


class CompressionConfig(BaseModel):
    """Context window compression configuration.

    Attributes:
        max_context_tokens: Maximum token count before compression triggers.
        strategy: Compression strategy to apply when threshold is exceeded.
        preserve_system_prompt: Whether to always preserve the system prompt message.
        summary_max_tokens: Maximum tokens for the summary when using SUMMARIZE strategy.
    """

    max_context_tokens: int = Field(
        default=12000,
        ge=256,
        description="Maximum context window tokens before compression activates.",
    )
    strategy: CompressionStrategy = Field(
        default=CompressionStrategy.TRUNCATE,
        description="Strategy for reducing context size.",
    )
    preserve_system_prompt: bool = Field(
        default=True,
        description="Always preserve the system prompt message during compression.",
    )
    summary_max_tokens: int = Field(
        default=500,
        ge=50,
        le=4096,
        description="Maximum tokens for the compressed summary (SUMMARIZE strategy).",
    )


class ConsensusConfig(BaseModel):
    """Agent-to-agent consensus configuration.

    Attributes:
        enabled: Whether consensus execution is active for this agent.
        instances: Number of parallel agent instances to spawn.
        threshold: Minimum agreement fraction required (0.0–1.0).
        varied_temperature_range: Temperature range for varied system prompts.
    """

    enabled: bool = Field(default=False, description="Enable/disable consensus execution.")
    instances: int = Field(
        default=3,
        ge=2,
        le=7,
        description="Number of parallel agent instances for consensus.",
    )
    threshold: float = Field(
        default=0.66,
        ge=0.0,
        le=1.0,
        description="Minimum agreement fraction for consensus (majority rule).",
    )
    varied_temperature_range: tuple[float, float] = Field(
        default=(0.2, 0.9),
        description="Temperature range for generating varied system prompts.",
    )


class MiddlewareConfig(BaseModel):
    """Per-agent or workflow-level middleware configuration overrides.

    All fields are optional — when None, the system defaults are used.

    Attributes:
        budget: Budget and cost guardrail settings.
        pii: PII/PHI masking settings.
        injection_firewall: Prompt injection firewall settings.
        compression: Context window compression settings.
    """

    budget: BudgetConfig = Field(
        default_factory=BudgetConfig,
        description="Budget and cost guardrail configuration.",
    )
    pii: PIIConfig = Field(
        default_factory=PIIConfig,
        description="PII/PHI masking configuration.",
    )
    injection_firewall: InjectionFirewallConfig = Field(
        default_factory=InjectionFirewallConfig,
        description="Prompt injection firewall configuration.",
    )
    compression: CompressionConfig = Field(
        default_factory=CompressionConfig,
        description="Context window compression configuration.",
    )

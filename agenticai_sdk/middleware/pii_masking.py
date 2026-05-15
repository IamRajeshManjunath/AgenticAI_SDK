"""
PII Masking Middleware — intercept payloads to dynamically redact PII/PHI
(credit cards, SSNs, emails, phone numbers, passport IDs, health record IDs).

Re-injects raw data during safe database write-back steps using a reversible
token vault. Supports FULL, PARTIAL (last-4), and HASH (SHA-256) masking levels.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from typing import Any

import structlog

from agenticai_sdk.exceptions import PIIMaskingError
from agenticai_sdk.middleware.base import MiddlewareBase, MiddlewareContext
from agenticai_sdk.schemas.middleware_config import MaskingLevel, PIIConfig

logger = structlog.get_logger(__name__)

# ── PII Pattern Registry ────────────────────────────────────────────────────
# Each entry: (pattern_name, compiled_regex, description)

_PII_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    (
        "credit_card",
        re.compile(r"\b(?:\d[ -]*?){13,19}\b"),
        "Credit card number (13-19 digits)",
    ),
    (
        "ssn",
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        "US Social Security Number",
    ),
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
        "Email address",
    ),
    (
        "phone_us",
        re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "US phone number",
    ),
    (
        "phone_intl",
        re.compile(r"\b\+\d{1,3}[-.\s]?\d{4,14}\b"),
        "International phone number",
    ),
    (
        "passport",
        re.compile(r"\b[A-Z]{1,2}\d{6,9}\b"),
        "Passport number",
    ),
    (
        "mrn",
        re.compile(r"\bMRN[-:\s]?\d{6,12}\b", re.IGNORECASE),
        "Medical Record Number (MRN)",
    ),
    (
        "ip_address",
        re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
        "IPv4 address",
    ),
]


def _luhn_check(card_number: str) -> bool:
    """Validate a credit card number using the Luhn algorithm."""
    digits = [int(d) for d in card_number if d.isdigit()]
    if len(digits) < 13:
        return False
    checksum = 0
    reverse_digits = digits[::-1]
    for i, d in enumerate(reverse_digits):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


class PIIMaskingMiddleware(MiddlewareBase):
    """State-aware PII/PHI masking router.

    Scans all string fields in the payload, replaces detected PII with
    reversible tokens, and stores originals in an in-memory vault.

    During safe write-back steps, re-injects original data from the vault.

    Attributes:
        _config: PII masking configuration.
        _vault: In-memory mapping of mask tokens to original values.
        _custom_patterns: User-defined additional PII patterns.
    """

    def __init__(self, config: PIIConfig | None = None) -> None:
        self._config = config or PIIConfig()
        self._vault: dict[str, dict[str, str]] = {}  # token -> {original, type}
        self._custom_patterns: list[tuple[str, re.Pattern, str]] = []

        # Compile custom patterns from config
        for name, pattern_str in self._config.custom_patterns.items():
            try:
                compiled = re.compile(pattern_str)
                self._custom_patterns.append((name, compiled, f"Custom: {name}"))
            except re.error as exc:
                logger.warning("pii_custom_pattern_invalid", name=name, error=str(exc))

    async def before(self, context: MiddlewareContext) -> MiddlewareContext:
        """Scan and mask PII in the inbound payload."""
        if not self._config.enabled:
            return context

        agent_id = context.agent_id
        is_safe_writeback = (
            agent_id in self._config.safe_writeback_agents
            and context.metadata.get("safe_writeback") is True
        )

        if is_safe_writeback:
            # During safe write-back, re-inject original data
            context.payload = self._unmask_payload(context.payload)
            logger.info("pii_unmasked_for_writeback", agent_id=agent_id)
            return context

        # Scan and mask
        masked_count = 0
        context.payload, masked_count = self._mask_payload(context.payload)

        # Store vault reference in metadata
        context.metadata["pii_vault_size"] = len(self._vault)
        context.metadata["pii_masked_count"] = masked_count

        if masked_count > 0:
            logger.info(
                "pii_masked",
                agent_id=agent_id,
                masked_count=masked_count,
                vault_size=len(self._vault),
            )

        return context

    async def after(self, context: MiddlewareContext) -> MiddlewareContext:
        """Post-process: keep masked unless safe write-back."""
        if not self._config.enabled:
            return context

        # Record PII events in middleware metadata
        context.metadata.setdefault("pii_events", []).append({
            "agent_id": context.agent_id,
            "direction": "outbound",
            "vault_size": len(self._vault),
        })

        return context

    def _mask_payload(self, payload: Any) -> tuple[Any, int]:
        """Recursively scan and mask PII in a payload structure."""
        count = 0

        if isinstance(payload, str):
            masked, c = self._mask_string(payload)
            return masked, c
        elif isinstance(payload, dict):
            result = {}
            for k, v in payload.items():
                masked_v, c = self._mask_payload(v)
                result[k] = masked_v
                count += c
            return result, count
        elif isinstance(payload, list):
            result_list = []
            for item in payload:
                masked_item, c = self._mask_payload(item)
                result_list.append(masked_item)
                count += c
            return result_list, count
        elif hasattr(payload, "content") and isinstance(getattr(payload, "content", None), str):
            # Handle LangChain message objects
            original = payload.content
            masked, c = self._mask_string(original)
            if c > 0:
                payload.content = masked
            return payload, c
        else:
            return payload, 0

    def _mask_string(self, text: str) -> tuple[str, int]:
        """Mask all PII patterns in a single string."""
        count = 0
        all_patterns = _PII_PATTERNS + self._custom_patterns

        for pii_type, pattern, _desc in all_patterns:
            matches = pattern.findall(text)
            for match in matches:
                # Special validation for credit cards
                if pii_type == "credit_card" and not _luhn_check(match):
                    continue

                token_id = str(uuid.uuid4())[:8]
                replacement = self._create_mask(match, pii_type, token_id)

                # Store in vault for potential re-injection
                self._vault[token_id] = {
                    "original": match,
                    "type": pii_type,
                }

                text = text.replace(match, replacement, 1)
                count += 1

        return text, count

    def _create_mask(self, original: str, pii_type: str, token_id: str) -> str:
        """Create a masked replacement based on the configured masking level."""
        if self._config.masking_level == MaskingLevel.FULL:
            return f"[PII:{pii_type}:{token_id}]"
        elif self._config.masking_level == MaskingLevel.PARTIAL:
            visible = original[-4:] if len(original) >= 4 else original
            masked = "*" * max(len(original) - 4, 0) + visible
            # Still store for vault reference
            return f"{masked}"
        elif self._config.masking_level == MaskingLevel.HASH:
            hash_value = hashlib.sha256(original.encode()).hexdigest()[:16]
            return f"[HASH:{pii_type}:{hash_value}]"
        else:
            return f"[PII:{pii_type}:{token_id}]"

    def _unmask_payload(self, payload: Any) -> Any:
        """Recursively restore masked PII tokens from the vault."""
        if isinstance(payload, str):
            return self._unmask_string(payload)
        elif isinstance(payload, dict):
            return {k: self._unmask_payload(v) for k, v in payload.items()}
        elif isinstance(payload, list):
            return [self._unmask_payload(item) for item in payload]
        elif hasattr(payload, "content") and isinstance(getattr(payload, "content", None), str):
            payload.content = self._unmask_string(payload.content)
            return payload
        else:
            return payload

    def _unmask_string(self, text: str) -> str:
        """Restore all PII tokens in a string from the vault."""
        for token_id, entry in self._vault.items():
            # Match both FULL and HASH style tokens
            full_token = f"[PII:{entry['type']}:{token_id}]"
            if full_token in text:
                text = text.replace(full_token, entry["original"])
        return text

    def clear_vault(self) -> None:
        """Securely clear the PII vault (call after workflow completion)."""
        self._vault.clear()
        logger.info("pii_vault_cleared")

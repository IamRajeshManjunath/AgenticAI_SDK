"""
Dynamic Schema Mapping Engine — normalize and resolve minor upstream JSON API
payload format changes on the fly.

Uses fuzzy key matching (difflib) for deterministic resolution, with an optional
local LLM fallback for complex structural transformations.
"""

from __future__ import annotations

import difflib
import json
from typing import Any

import structlog

from agenticai_sdk.exceptions import SchemaMapperError

logger = structlog.get_logger(__name__)


class SchemaMapperEngine:
    """Dynamically normalizes JSON payloads against expected schemas.

    Resolution strategies (in priority order):
      1. Exact match — field names already match
      2. Case-insensitive match — ``userId`` → ``user_id``
      3. Fuzzy match — ``usr_name`` → ``user_name`` (via SequenceMatcher)
      4. LLM-assisted — complex structural transformations (optional)

    Caches resolved mappings for repeated patterns.

    Usage::

        mapper = SchemaMapperEngine()
        normalized = mapper.auto_resolve(payload, expected_schema)
    """

    def __init__(self, fuzzy_threshold: float = 0.7) -> None:
        self._fuzzy_threshold = fuzzy_threshold
        self._schema_cache: dict[str, dict[str, str]] = {}

    def auto_resolve(
        self,
        payload: dict[str, Any],
        expected_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """Deterministic schema resolution using fuzzy key matching.

        Args:
            payload: The incoming JSON payload with potentially mismatched keys.
            expected_schema: Expected schema definition as a dict of
                ``{field_name: field_type_or_description}``.

        Returns:
            Normalized payload with keys matching the expected schema.

        Raises:
            SchemaMapperError: If normalization encounters an unrecoverable issue.
        """
        try:
            cache_key = self._compute_cache_key(payload, expected_schema)

            if cache_key in self._schema_cache:
                mapping = self._schema_cache[cache_key]
                logger.debug("schema_mapper_cache_hit", cache_key=cache_key[:32])
                return self._apply_mapping(payload, mapping)

            expected_keys = set(expected_schema.keys())
            payload_keys = set(payload.keys())

            # Build field mapping
            mapping: dict[str, str] = {}  # payload_key -> expected_key

            for p_key in payload_keys:
                # Strategy 1: Exact match
                if p_key in expected_keys:
                    mapping[p_key] = p_key
                    continue

                # Strategy 2: Case-insensitive match
                lower_match = self._case_insensitive_match(p_key, expected_keys)
                if lower_match:
                    mapping[p_key] = lower_match
                    continue

                # Strategy 3: Fuzzy match
                fuzzy_match = self._fuzzy_match(p_key, expected_keys)
                if fuzzy_match:
                    mapping[p_key] = fuzzy_match
                    continue

                # No match — keep original key
                mapping[p_key] = p_key

            # Cache the mapping
            self._schema_cache[cache_key] = mapping

            result = self._apply_mapping(payload, mapping)

            # Log unmapped keys
            unmapped = [k for k, v in mapping.items() if k == v and k not in expected_keys]
            if unmapped:
                logger.info(
                    "schema_mapper_unmapped_keys",
                    unmapped_keys=unmapped,
                    expected_keys=list(expected_keys),
                )

            mapped_count = sum(1 for k, v in mapping.items() if k != v)
            if mapped_count > 0:
                logger.info(
                    "schema_mapper_resolved",
                    mapped_count=mapped_count,
                    mappings={k: v for k, v in mapping.items() if k != v},
                )

            return result

        except SchemaMapperError:
            raise
        except Exception as exc:
            raise SchemaMapperError(
                f"Schema normalization failed: {exc}",
                detail={"error": str(exc)},
            ) from exc

    async def normalize(
        self,
        payload: dict[str, Any],
        expected_schema: dict[str, Any],
        llm_client: Any | None = None,
    ) -> dict[str, Any]:
        """LLM-assisted schema normalization for complex transformations.

        First attempts deterministic auto_resolve. If significant mismatches
        remain, uses an LLM call to produce the mapping.

        Args:
            payload: The incoming JSON payload.
            expected_schema: Expected schema definition.
            llm_client: Optional LLM client for complex transformations.

        Returns:
            Normalized payload.
        """
        # First try deterministic resolution
        result = self.auto_resolve(payload, expected_schema)

        # Check if significant mismatches remain
        expected_keys = set(expected_schema.keys())
        result_keys = set(result.keys())
        missing = expected_keys - result_keys
        extra = result_keys - expected_keys

        if not missing and not extra:
            return result

        if llm_client is None or not missing:
            return result

        # LLM-assisted resolution for remaining mismatches
        try:
            prompt = (
                f"Map the following JSON payload keys to the expected schema.\n\n"
                f"Payload keys: {list(payload.keys())}\n"
                f"Expected keys: {list(expected_schema.keys())}\n"
                f"Missing from result: {list(missing)}\n"
                f"Extra in result: {list(extra)}\n\n"
                f"Return a JSON object mapping payload keys to expected keys. "
                f"Only include mappings that differ.\n"
                f"Example: {{\"old_key\": \"new_key\"}}"
            )

            if hasattr(llm_client, "ainvoke"):
                from langchain_core.messages import HumanMessage
                response = await llm_client.ainvoke([HumanMessage(content=prompt)])
                mapping_text = response.content
            else:
                mapping_text = "{}"

            # Parse LLM mapping
            llm_mapping = json.loads(mapping_text.strip().strip("`").strip())
            if isinstance(llm_mapping, dict):
                for old_key, new_key in llm_mapping.items():
                    if old_key in result and new_key in expected_keys:
                        result[new_key] = result.pop(old_key)

                logger.info(
                    "schema_mapper_llm_resolved",
                    llm_mappings=llm_mapping,
                )

        except Exception as exc:
            logger.warning("schema_mapper_llm_fallback_failed", error=str(exc))

        return result

    def _case_insensitive_match(self, key: str, expected_keys: set[str]) -> str | None:
        """Try case-insensitive and snake_case/camelCase normalization."""
        normalized_key = self._normalize_key(key)
        for expected in expected_keys:
            if self._normalize_key(expected) == normalized_key:
                return expected
        return None

    def _fuzzy_match(self, key: str, expected_keys: set[str]) -> str | None:
        """Find the best fuzzy match above the threshold."""
        best_match = None
        best_ratio = 0.0

        normalized_key = self._normalize_key(key)
        for expected in expected_keys:
            normalized_expected = self._normalize_key(expected)
            ratio = difflib.SequenceMatcher(None, normalized_key, normalized_expected).ratio()
            if ratio > best_ratio and ratio >= self._fuzzy_threshold:
                best_ratio = ratio
                best_match = expected

        return best_match

    @staticmethod
    def _normalize_key(key: str) -> str:
        """Normalize a key to lowercase with underscores for comparison."""
        import re

        # camelCase → snake_case
        key = re.sub(r"([a-z])([A-Z])", r"\1_\2", key)
        # Remove non-alphanumeric chars except underscore
        key = re.sub(r"[^a-zA-Z0-9_]", "_", key)
        return key.lower().strip("_")

    @staticmethod
    def _apply_mapping(payload: dict[str, Any], mapping: dict[str, str]) -> dict[str, Any]:
        """Apply a key mapping to a payload dict."""
        return {mapping.get(k, k): v for k, v in payload.items()}

    @staticmethod
    def _compute_cache_key(payload: dict[str, Any], expected: dict[str, Any]) -> str:
        """Compute a stable cache key from payload and expected key sets."""
        payload_sig = ",".join(sorted(payload.keys()))
        expected_sig = ",".join(sorted(expected.keys()))
        import hashlib
        return hashlib.md5(f"{payload_sig}|{expected_sig}".encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the schema mapping cache."""
        self._schema_cache.clear()
        logger.debug("schema_mapper_cache_cleared")

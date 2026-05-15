"""
Context Compression Middleware — monitor context window saturation and apply
dynamic summarization strategies to prevent out-of-token runtime failures.

Strategies:
  - TRUNCATE: Sliding-window drop of oldest messages (preserving system prompt)
  - SUMMARIZE: LLM-based summarization of the middle message section
  - DROP_SCHEMAS: Remove redundant tool schema descriptions from messages
"""

from __future__ import annotations

from typing import Any

import structlog

from agenticai_sdk.exceptions import ContextCompressionError
from agenticai_sdk.middleware.base import MiddlewareBase, MiddlewareContext
from agenticai_sdk.schemas.middleware_config import CompressionConfig, CompressionStrategy

logger = structlog.get_logger(__name__)


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken if available, else heuristic."""
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except (ImportError, Exception):
        return int(len(text.split()) * 1.3)


def _messages_to_text(messages: list) -> str:
    """Convert a message list to a single text string for token counting."""
    parts: list[str] = []
    for msg in messages:
        if isinstance(msg, dict):
            parts.append(str(msg.get("content", "")))
        elif hasattr(msg, "content"):
            parts.append(str(getattr(msg, "content", "")))
        else:
            parts.append(str(msg))
    return "\n".join(parts)


class ContextCompressionMiddleware(MiddlewareBase):
    """Context window management middleware.

    Monitors total token count in the message history and applies
    compression when the configured threshold is exceeded.

    Compression is applied only on the ``before()`` hook (inbound pass)
    so that the agent node receives a right-sized context window.

    Attributes:
        _config: Compression configuration.
    """

    def __init__(self, config: CompressionConfig | None = None) -> None:
        self._config = config or CompressionConfig()

    async def before(self, context: MiddlewareContext) -> MiddlewareContext:
        """Check context size and compress if needed."""
        messages = context.payload.get("messages", [])
        if not messages:
            return context

        # Count total tokens
        full_text = _messages_to_text(messages)
        total_tokens = _count_tokens(full_text)

        if total_tokens <= self._config.max_context_tokens:
            logger.debug(
                "context_within_budget",
                agent_id=context.agent_id,
                total_tokens=total_tokens,
                max_tokens=self._config.max_context_tokens,
            )
            return context

        logger.info(
            "context_compression_triggered",
            agent_id=context.agent_id,
            total_tokens=total_tokens,
            max_tokens=self._config.max_context_tokens,
            strategy=self._config.strategy.value,
        )

        try:
            if self._config.strategy == CompressionStrategy.TRUNCATE:
                compressed_messages = self._truncate(messages, total_tokens)
            elif self._config.strategy == CompressionStrategy.SUMMARIZE:
                compressed_messages = await self._summarize(messages, context)
            elif self._config.strategy == CompressionStrategy.DROP_SCHEMAS:
                compressed_messages = self._drop_schemas(messages)
            else:
                compressed_messages = self._truncate(messages, total_tokens)

            # Update payload
            context.payload["messages"] = compressed_messages

            # Record compression stats
            compressed_text = _messages_to_text(compressed_messages)
            compressed_tokens = _count_tokens(compressed_text)
            compression_ratio = 1 - (compressed_tokens / total_tokens) if total_tokens > 0 else 0

            context.metadata["compression_stats"] = {
                "original_tokens": total_tokens,
                "compressed_tokens": compressed_tokens,
                "compression_ratio": round(compression_ratio, 3),
                "strategy": self._config.strategy.value,
                "original_message_count": len(messages),
                "compressed_message_count": len(compressed_messages),
            }

            logger.info(
                "context_compressed",
                agent_id=context.agent_id,
                original_tokens=total_tokens,
                compressed_tokens=compressed_tokens,
                ratio=round(compression_ratio, 3),
                messages_before=len(messages),
                messages_after=len(compressed_messages),
            )

        except Exception as exc:
            raise ContextCompressionError(
                f"Context compression failed for agent '{context.agent_id}': {exc}",
                detail={"agent_id": context.agent_id, "strategy": self._config.strategy.value},
            ) from exc

        return context

    async def after(self, context: MiddlewareContext) -> MiddlewareContext:
        """Post-process: no compression on outbound (output is typically small)."""
        return context

    def _truncate(self, messages: list, total_tokens: int) -> list:
        """Sliding-window truncation: keep system prompt + most recent messages.

        Preserves the first message if it's a system prompt, then keeps
        as many recent messages as fit within the token budget.
        """
        if not messages:
            return messages

        # Check if first message is a system prompt
        first_msg = messages[0]
        is_system = False
        if hasattr(first_msg, "type"):
            is_system = first_msg.type == "system"
        elif isinstance(first_msg, dict):
            is_system = first_msg.get("type") == "system" or first_msg.get("role") == "system"

        preserved: list = []
        remaining = messages

        if is_system and self._config.preserve_system_prompt:
            preserved = [first_msg]
            remaining = messages[1:]

        # Binary search for optimal window size
        target_tokens = self._config.max_context_tokens
        if preserved:
            preserved_text = _messages_to_text(preserved)
            target_tokens -= _count_tokens(preserved_text)

        # Take messages from the end until we hit the target
        windowed: list = []
        running_tokens = 0
        for msg in reversed(remaining):
            msg_text = _messages_to_text([msg])
            msg_tokens = _count_tokens(msg_text)
            if running_tokens + msg_tokens > target_tokens:
                break
            windowed.insert(0, msg)
            running_tokens += msg_tokens

        return preserved + windowed

    async def _summarize(self, messages: list, context: MiddlewareContext) -> list:
        """Summarize the middle section of messages using a lightweight LLM call.

        Preserves the system prompt (first message) and the most recent messages.
        Compresses the middle section into a single summary message.
        """
        if len(messages) <= 3:
            return self._truncate(messages, _count_tokens(_messages_to_text(messages)))

        # Split into head (system), middle (to summarize), tail (recent)
        head = [messages[0]]
        tail_count = min(4, len(messages) // 3)
        tail = messages[-tail_count:]
        middle = messages[1:-tail_count] if tail_count < len(messages) - 1 else []

        if not middle:
            return self._truncate(messages, _count_tokens(_messages_to_text(messages)))

        # Build summary text from middle messages
        middle_text = _messages_to_text(middle)

        # Create a concise summary (we use a simple extractive approach
        # to avoid requiring an LLM call in the middleware)
        summary_lines = []
        for msg in middle:
            content = ""
            if hasattr(msg, "content"):
                content = str(msg.content)
            elif isinstance(msg, dict):
                content = str(msg.get("content", ""))
            # Take first 100 chars of each message as key points
            if content.strip():
                msg_type = getattr(msg, "type", "message") if hasattr(msg, "type") else "message"
                summary_lines.append(f"[{msg_type}] {content[:150].strip()}")

        summary_text = (
            f"[COMPRESSED CONTEXT — {len(middle)} messages summarized]\n"
            + "\n".join(summary_lines[:10])  # Cap at 10 key points
        )

        # Truncate summary if still too long
        max_summary_tokens = self._config.summary_max_tokens
        if _count_tokens(summary_text) > max_summary_tokens:
            words = summary_text.split()
            target_words = int(max_summary_tokens / 1.3)
            summary_text = " ".join(words[:target_words])

        # Create summary message
        try:
            from langchain_core.messages import SystemMessage

            summary_msg = SystemMessage(content=summary_text)
        except ImportError:
            summary_msg = {"role": "system", "content": summary_text}

        return head + [summary_msg] + tail

    def _drop_schemas(self, messages: list) -> list:
        """Remove redundant tool schema descriptions from messages.

        Identifies messages containing tool schema JSON blocks and replaces
        them with compact references like "[Tool: tool_name available]".
        """
        import json

        compressed = []
        schema_pattern_keywords = [
            '"type": "function"', '"parameters":', '"properties":',
            '"json_schema"', '"tool_choice"', '"function_call"',
        ]

        for msg in messages:
            content = ""
            if hasattr(msg, "content"):
                content = str(msg.content)
            elif isinstance(msg, dict):
                content = str(msg.get("content", ""))

            # Check if this message contains heavy tool schema definitions
            schema_matches = sum(1 for kw in schema_pattern_keywords if kw in content)
            if schema_matches >= 2 and len(content) > 500:
                # Extract tool names if possible
                tool_names: list[str] = []
                try:
                    # Try to find tool name references
                    for line in content.split("\n"):
                        if '"name"' in line:
                            parts = line.split('"name"')
                            if len(parts) > 1:
                                name_match = parts[1].strip().strip(':').strip().strip('"').strip(',').strip('"')
                                if name_match and len(name_match) < 50:
                                    tool_names.append(name_match)
                except Exception:
                    pass

                tools_ref = ", ".join(tool_names[:5]) if tool_names else "multiple tools"
                compact = f"[Tool schemas available: {tools_ref}]"

                # Create compact replacement message
                if hasattr(msg, "content"):
                    try:
                        from langchain_core.messages import SystemMessage

                        compressed.append(SystemMessage(content=compact))
                    except ImportError:
                        compressed.append({"role": "system", "content": compact})
                else:
                    compressed.append({"role": msg.get("role", "system"), "content": compact})
            else:
                compressed.append(msg)

        return compressed

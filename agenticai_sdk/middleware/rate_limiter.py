"""
Rate Limiter Middleware — protects agents and workflows from excessive execution rates.
Supports Redis backend for multi-instance production or in-memory fallback for dev.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "")

# In-memory fallback (dev)
_token_bucket: dict[str, list[float]] = defaultdict(list)

try:
    import aioredis  # type: ignore[import-untyped]

    HAS_REDIS = bool(REDIS_URL)
except ImportError:
    HAS_REDIS = False


class RateLimiterMiddleware:
    """
    Middleware that enforces rate limits per workflow, agent, or API key.

    Uses Redis (sliding window) when REDIS_URL is set, otherwise falls back
    to an in-memory token bucket (single-process dev only).
    """

    def __init__(self, max_requests_per_minute: int = 60, target_id: str = "global"):
        self.max_requests_per_minute = max_requests_per_minute
        self.target_id = target_id

    async def __call__(self, state: dict[str, Any], next_handler) -> dict[str, Any]:
        if HAS_REDIS:
            await self._check_redis()
        else:
            self._check_memory()
        return await next_handler(state)

    async def _check_redis(self):
        try:
            redis = await aioredis.from_url(REDIS_URL)
            key = f"ratelimit:{self.target_id}"
            current = await redis.incr(key)
            if current == 1:
                await redis.expire(key, 60)
            if current > self.max_requests_per_minute:
                logger.warning(
                    "rate_limit_exceeded_redis",
                    target_id=self.target_id,
                    limit=self.max_requests_per_minute,
                    current=current,
                )
                raise PermissionError(
                    f"Rate limit exceeded for {self.target_id} "
                    f"(Limit: {self.max_requests_per_minute}/min)"
                )
            await redis.close()
        except PermissionError:
            raise
        except Exception as exc:
            logger.error("redis_rate_limit_failed", error=str(exc))
            # Fall through on Redis error — don't block traffic for infra issues

    def _check_memory(self):
        now = time.time()
        minute_ago = now - 60.0
        _token_bucket[self.target_id] = [
            t for t in _token_bucket[self.target_id] if t > minute_ago
        ]
        if len(_token_bucket[self.target_id]) >= self.max_requests_per_minute:
            logger.warning(
                "rate_limit_exceeded",
                target_id=self.target_id,
                limit=self.max_requests_per_minute,
            )
            raise PermissionError(
                f"Rate limit exceeded for {self.target_id} "
                f"(Limit: {self.max_requests_per_minute}/min)"
            )
        _token_bucket[self.target_id].append(now)
        logger.debug(
            "rate_limiter_passed",
            target_id=self.target_id,
            current_rpm=len(_token_bucket[self.target_id]),
        )

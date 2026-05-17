"""
Rate Limiter Middleware — protects agents and workflows from excessive execution rates.
"""

import time
import structlog
from typing import Any
from collections import defaultdict

logger = structlog.get_logger(__name__)

# Basic in-memory store for rate limits (in production this would be Redis/Memcached)
_token_bucket: dict[str, list[float]] = defaultdict(list)

class RateLimiterMiddleware:
    """
    Middleware that enforces local rate limits per workflow or agent.
    If the allowed executions per minute is exceeded, it immediately rejects the request.
    """

    def __init__(self, max_requests_per_minute: int = 60, target_id: str = "global"):
        self.max_requests_per_minute = max_requests_per_minute
        self.target_id = target_id

    async def __call__(self, state: dict[str, Any], next_handler) -> dict[str, Any]:
        """
        Intercepts execution and validates rate usage.
        """
        now = time.time()
        minute_ago = now - 60.0

        # Clean old records
        _token_bucket[self.target_id] = [t for t in _token_bucket[self.target_id] if t > minute_ago]

        if len(_token_bucket[self.target_id]) >= self.max_requests_per_minute:
            logger.warning("rate_limit_exceeded", target_id=self.target_id, limit=self.max_requests_per_minute)
            raise PermissionError(f"Rate limit exceeded for {self.target_id} (Limit: {self.max_requests_per_minute}/min)")

        _token_bucket[self.target_id].append(now)
        logger.debug("rate_limiter_passed", target_id=self.target_id, current_rpm=len(_token_bucket[self.target_id]))

        # Execute Node Logic
        return await next_handler(state)

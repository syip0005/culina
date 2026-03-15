"""In-memory sliding-window rate limiter keyed by user ID."""

from __future__ import annotations

import time
from collections import defaultdict
from uuid import UUID


class RateLimiter:
    """Simple per-user sliding-window rate limiter.

    Keeps a list of timestamps per key and prunes expired entries on access.
    Suitable for single-process deployments; swap for Redis-backed impl later.
    """

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[UUID, list[float]] = defaultdict(list)

    def check(self, user_id: UUID) -> bool:
        """Record a hit and return True if within limits, False if exceeded."""
        now = time.monotonic()
        bucket = self._hits[user_id]

        # Prune expired entries
        cutoff = now - self._window
        self._hits[user_id] = bucket = [t for t in bucket if t > cutoff]

        if len(bucket) >= self._max:
            return False

        bucket.append(now)
        return True

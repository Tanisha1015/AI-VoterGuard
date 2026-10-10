"""A small in-memory sliding-window rate limiter (per client IP). Nothing but the IP is stored."""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import Request

from app.errors import ApiError

CITIZEN_LIMIT = 20  # requests ...
CITIZEN_WINDOW_SECONDS = 60.0  # ... per minute per client IP


class RateLimiter:
    """Allow at most ``limit`` calls per ``window`` seconds for each key."""

    def __init__(self, limit: int, window: float, clock: Callable[[], float] = time.monotonic) -> None:
        self.limit = limit
        self.window = window
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        """Record a call for ``key`` and return True, or return False when the limit is reached."""
        now = self._clock()
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and now - hits[0] >= self.window:
                hits.popleft()
            if len(hits) >= self.limit:
                return False
            hits.append(now)
            self._prune(now)
            return True

    def _prune(self, now: float) -> None:
        """Forget keys whose calls are all outside the window (keeps memory bounded)."""
        if len(self._hits) < 1024:
            return
        stale = [k for k, h in self._hits.items() if not h or now - h[-1] >= self.window]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        """Forget all calls (used by tests)."""
        with self._lock:
            self._hits.clear()


citizen_limiter = RateLimiter(CITIZEN_LIMIT, CITIZEN_WINDOW_SECONDS)


def citizen_rate_limit(request: Request) -> None:
    """FastAPI dependency: 20 citizen lookups per minute per client IP, else 429."""
    ip = request.client.host if request.client else "unknown"
    if not citizen_limiter.allow(ip):
        raise ApiError(429, "RATE_LIMITED", "Too many requests. Please wait a minute and try again.")

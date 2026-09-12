"""In-process sliding-window rate limiting for sensitive endpoints.

Pure-ASGI middleware: matched requests are counted per client host and
bucket (auth endpoints, LLM-billed generation endpoints); everything else —
including the SSE stream — passes through untouched. Limits come from
``Settings`` so deployments can tune or disable them per environment.

Single-process by design (same scope as the SSE bus): a multi-worker
deployment needs the reverse proxy to enforce the equivalent limits (see
ADR 0007).
"""

import math
import time
from collections import defaultdict, deque
from collections.abc import Callable, Sequence

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

WINDOW_SECONDS = 60.0

RouteRule = tuple[str, str, str]  # (method, path, bucket)

AUTH_BUCKET = "auth"
GENERATION_BUCKET = "generation"

# The LLM-billed endpoints: with a provider key configured, unthrottled
# access converts into an open tap on the owner's provider budget.
RULES: tuple[RouteRule, ...] = (
    ("POST", "/api/v1/auth/login", AUTH_BUCKET),
    ("POST", "/api/v1/auth/register", AUTH_BUCKET),
    ("POST", "/api/v1/auth/refresh", AUTH_BUCKET),
    ("POST", "/api/v1/assessments", GENERATION_BUCKET),
    ("POST", "/api/v1/learning-paths/generate", GENERATION_BUCKET),
    ("POST", "/api/v1/resumes/generate", GENERATION_BUCKET),
    ("GET", "/api/v1/market/insights", GENERATION_BUCKET),
)


class SlidingWindowLimiter:
    """Sliding-window request counter keyed by arbitrary strings."""

    # Sweep cadence: fully-expired buckets are dropped once every N checks so
    # a flood of unique keys cannot grow memory without bound.
    _SWEEP_EVERY = 512

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._checks = 0

    def check(self, key: str, limit: int, window: float = WINDOW_SECONDS) -> tuple[bool, int]:
        """Record a hit for *key*; return ``(allowed, retry_after_seconds)``.

        ``retry_after_seconds`` is 0 for allowed requests and otherwise the
        whole seconds until the window frees up (minimum 1).
        """
        now = self._clock()
        hits = self._hits[key]
        cutoff = now - window
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return False, max(1, math.ceil(hits[0] + window - now))
        hits.append(now)
        self._checks += 1
        if self._checks % self._SWEEP_EVERY == 0:
            self._drop_expired(cutoff)
        return True, 0

    def _drop_expired(self, cutoff: float) -> None:
        """Forget buckets whose every recorded hit is older than the window."""
        stale = [key for key, hits in self._hits.items() if not hits or hits[-1] <= cutoff]
        for key in stale:
            del self._hits[key]

    def reset(self) -> None:
        """Forget all recorded hits (used by the test suite for isolation)."""
        self._hits.clear()


def bucket_for(method: str, path: str, rules: Sequence[RouteRule] = RULES) -> str | None:
    """Return the rate-limit bucket for a route, or None when unthrottled."""
    for rule_method, rule_path, bucket in rules:
        if method == rule_method and path == rule_path:
            return bucket
    return None


class RateLimitMiddleware:
    """Reject requests that exceed their bucket's per-client limit with 429."""

    def __init__(
        self,
        app: ASGIApp,
        limiter: SlidingWindowLimiter,
        limits: Callable[[], dict[str, int]],
    ) -> None:
        self.app = app
        self.limiter = limiter
        self.limits = limits

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        bucket = bucket_for(scope.get("method", ""), scope.get("path", ""))
        if bucket is None or (limit := self.limits().get(bucket, 0)) <= 0:
            await self.app(scope, receive, send)
            return
        client = scope.get("client")
        key = f"{bucket}:{client[0] if client else 'unknown'}"
        allowed, retry_after = self.limiter.check(key, limit)
        if allowed:
            await self.app(scope, receive, send)
            return
        await _reject(retry_after)(scope, receive, send)


def _reject(retry_after: int) -> ASGIApp:
    return JSONResponse(
        {"detail": "Too many requests"},
        status_code=429,
        headers={"Retry-After": str(retry_after)},
    )

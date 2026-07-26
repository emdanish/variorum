from __future__ import annotations

import time
from collections import deque

from starlette.requests import Request
from starlette.responses import JSONResponse

# Per-bucket limits: (max requests, window seconds), keyed by client IP.
# Generous by design — this is abuse protection, not fine-grained quota. For a
# real production deployment, pair this with rate limiting at the edge (reverse
# proxy / API gateway), which survives restarts and scales across processes.
_BUCKET_LIMITS: dict[str, tuple[int, float]] = {
    "auth": (20, 60.0),
    "ai": (30, 60.0),
    "webhook": (120, 60.0),
}

_AI_SUFFIXES = ("/ask", "/open-pr", "/generate-tests")


def classify(path: str) -> str | None:
    """Map a request path to a rate-limit bucket, or None if unlimited."""
    if path.startswith("/api/v1/auth/github/"):
        return "auth"
    if path == "/webhooks/github":
        return "webhook"
    if path.endswith(_AI_SUFFIXES):
        return "ai"
    return None


class RateLimiter:
    """In-process fixed-window limiter. Single-process only (matches the MVP's
    BackgroundTasks model); state resets on restart."""

    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], deque[float]] = {}

    def allow(self, bucket: str, client: str, now: float) -> bool:
        limit, window = _BUCKET_LIMITS[bucket]
        dq = self._hits.setdefault((bucket, client), deque())
        cutoff = now - window
        while dq and dq[0] < cutoff:
            dq.popleft()
        if len(dq) >= limit:
            return False
        dq.append(now)
        return True


_limiter = RateLimiter()


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    bucket = classify(request.url.path)
    if bucket is not None and not _limiter.allow(bucket, _client_ip(request), time.monotonic()):
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please slow down and try again."},
        )
    return await call_next(request)

"""Small in-process rate limiter.

This protects a single-process development / small deployment instance. A
multi-instance production deployment must use the Redis adapter noted in the
architecture docs; no claim of distributed rate limiting is made here.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_rate_limit(request: Request, bucket: str, limit: int) -> None:
    now = time.monotonic()
    key = f"{bucket}:{_client_key(request)}"
    window = _hits[key]
    while window and now - window[0] > 60:
        window.popleft()
    if len(window) >= limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please wait a moment and try again.",
            headers={"Retry-After": "60"},
        )
    window.append(now)


def login_limit(request: Request) -> None:
    enforce_rate_limit(request, "login", settings.login_rate_limit_per_minute)


def assistant_limit(request: Request) -> None:
    enforce_rate_limit(request, "assistant", settings.assistant_rate_limit_per_minute)

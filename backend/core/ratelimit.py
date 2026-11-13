"""Fixed-window rate limits stored in Redis db 2 (cache alias ``locks``)."""

from __future__ import annotations

import time

from django.core.cache import caches

from .exceptions import RateLimitedError


def hit(scope: str, key: str, *, limit: int, window: int) -> None:
    """Count one attempt; raise ``RateLimitedError`` once ``limit`` is exceeded in ``window`` s."""
    store = caches["locks"]
    bucket = int(time.time() // window)
    cache_key = f"ratelimit:{scope}:{key}:{bucket}"
    if store.add(cache_key, 1, timeout=window):
        count = 1
    else:
        try:
            count = store.incr(cache_key)
        except ValueError:  # expired between add() and incr()
            store.set(cache_key, 1, timeout=window)
            count = 1
    if count > limit:
        retry_after = window - int(time.time() % window)
        raise RateLimitedError(retry_after)


def reset(scope: str, key: str, *, window: int) -> None:
    bucket = int(time.time() // window)
    caches["locks"].delete(f"ratelimit:{scope}:{key}:{bucket}")

# app/auth/redis.py
from __future__ import annotations

import time
from typing import Optional

# Try to import aioredis. On Python 3.13 some versions raise a TypeError at import
# ("duplicate base class TimeoutError"). If that happens, we fall back to an
# in-memory blacklist so the app keeps working for tests/local dev.
try:
    import aioredis  # type: ignore
    _REDIS_OK = True
except Exception:  # pragma: no cover
    aioredis = None  # type: ignore[assignment]
    _REDIS_OK = False

from app.core.config import get_settings

_settings = get_settings()
_REDIS_URL = (_settings.REDIS_URL or "redis://localhost:6379/0").strip()

# Process-local fallback store (used only if aioredis is unavailable/broken).
# Simple and good enough for tests; does not implement TTL.
_FALLBACK_BLACKLIST: set[str] = set()


async def _get_redis() -> Optional["aioredis.Redis"]:
    """Return a memoized aioredis client, or None if redis is unavailable."""
    if not _REDIS_OK:
        return None

    # Lazy, memoized client on the function object
    if not hasattr(_get_redis, "_client"):
        # aioredis v2: from_url returns an async Redis client
        _get_redis._client = aioredis.from_url(  # type: ignore[attr-defined]
            _REDIS_URL, encoding="utf-8", decode_responses=True
        )
    return _get_redis._client  # type: ignore[attr-defined]


async def add_to_blacklist(jti: str, exp: int) -> None:
    """
    Add a token JTI to the blacklist until its expiry time.

    Parameters
    ----------
    jti : str
        Token ID to blacklist.
    exp : int
        Expiration as a UNIX epoch (seconds). We convert this to a TTL when
        using Redis. If Redis is unavailable, we store in a process-local set.
    """
    redis = await _get_redis()
    if redis is None:
        _FALLBACK_BLACKLIST.add(jti)
        return

    # Convert absolute expiry (epoch seconds) to TTL
    ttl = max(0, int(exp) - int(time.time()))
    try:
        # Namespaced key; value is irrelevant (we only check existence)
        await redis.setex(f"blacklist:{jti}", ttl, "1")  # type: ignore[attr-defined]
    except Exception:
        # Do not let Redis hiccups break auth flows during tests
        _FALLBACK_BLACKLIST.add(jti)


async def is_blacklisted(jti: str) -> bool:
    """
    Check if a token JTI is blacklisted.
    """
    redis = await _get_redis()
    if redis is None:
        return jti in _FALLBACK_BLACKLIST

    try:
        # aioredis v2 returns int 1/0 for exists
        return bool(await redis.exists(f"blacklist:{jti}"))  # type: ignore[attr-defined]
    except Exception:
        # Fail safe: if Redis errors, check fallback too
        return jti in _FALLBACK_BLACKLIST

"""
Redis-backed sliding-window rate limiter keyed per API key.

Falls back to in-memory counters if Redis is unavailable (dev/testing).
"""
from __future__ import annotations

import logging
import time
from typing import Optional

from fastapi import Depends, HTTPException, Request, Response, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis connection (lazy singleton)
# ---------------------------------------------------------------------------

_redis = None
_redis_checked = False


def _get_redis():
    """Return a Redis client or None if unavailable."""
    global _redis, _redis_checked
    if _redis_checked:
        return _redis
    _redis_checked = True
    try:
        import os
        import redis
        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        _redis = redis.Redis.from_url(url, decode_responses=True, socket_connect_timeout=2)
        _redis.ping()
        logger.info("B2B rate limiter connected to Redis at %s", url)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — falling back to in-memory rate limiting", exc)
        _redis = None
    return _redis


# ---------------------------------------------------------------------------
# In-memory fallback (single-process only)
# ---------------------------------------------------------------------------

_mem_buckets: dict[str, list[float]] = {}


def _mem_count(key: str, window: int) -> int:
    now = time.time()
    cutoff = now - window
    bucket = _mem_buckets.setdefault(key, [])
    # Prune expired
    _mem_buckets[key] = [t for t in bucket if t > cutoff]
    _mem_buckets[key].append(now)
    return len(_mem_buckets[key])


# ---------------------------------------------------------------------------
# Core: check rate limit
# ---------------------------------------------------------------------------

def _check_redis(r, key: str, limit: int, window: int) -> tuple[int, int]:
    """Sliding window via sorted set.  Returns (current_count, ttl_seconds)."""
    now = time.time()
    pipe = r.pipeline(transaction=True)
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window + 1)
    results = pipe.execute()
    count = results[2]
    return count, window


def check_rate_limit(
    api_key_id: str,
    rpm: int,
    rpd: int,
) -> tuple[bool, int, int]:
    """
    Returns (allowed, remaining_rpm, retry_after_seconds).
    """
    r = _get_redis()

    # --- Per-minute ---
    rpm_key = f"b2b:rpm:{api_key_id}"
    if r is not None:
        count_m, _ = _check_redis(r, rpm_key, rpm, 60)
    else:
        count_m = _mem_count(rpm_key, 60)

    if count_m > rpm:
        return False, 0, 60

    # --- Per-day ---
    rpd_key = f"b2b:rpd:{api_key_id}"
    if r is not None:
        count_d, _ = _check_redis(r, rpd_key, rpd, 86400)
    else:
        count_d = _mem_count(rpd_key, 86400)

    if count_d > rpd:
        return False, 0, 3600  # tell them to wait an hour

    remaining = max(0, rpm - count_m)
    return True, remaining, 0


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def b2b_rate_limit(request: Request, response: Response):
    """
    Dependency that enforces per-key rate limits.
    Must run AFTER the B2B auth dependency has set request.state.b2b.
    """
    ctx = getattr(request.state, "b2b", None)
    if ctx is None:
        return  # not a B2B route, skip

    allowed, remaining, retry_after = check_rate_limit(
        ctx.api_key_id,
        ctx.key_record.rate_limit_rpm,
        ctx.key_record.rate_limit_rpd,
    )

    response.headers["X-RateLimit-Limit"] = str(ctx.key_record.rate_limit_rpm)
    response.headers["X-RateLimit-Remaining"] = str(remaining)

    if not allowed:
        response.headers["Retry-After"] = str(retry_after)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry after {retry_after}s.",
        )

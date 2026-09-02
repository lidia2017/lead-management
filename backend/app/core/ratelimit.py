"""Rate limiting for the public submit endpoint, as a FastAPI dependency.

The public form is an abuse magnet (bots, spam). A per-IP fixed-window limit
sheds that load before it reaches the DB / email pipeline. Counters live in
Redis so the limit is shared across every API replica.

Disabled by default (tests + single-node dev need no Redis); enabled via
``RATE_LIMIT_ENABLED``. Fail-open: if Redis is unreachable we log and allow the
request rather than take the endpoint down.
"""
from __future__ import annotations

import logging
import time

from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger("ratelimit")

_PERIODS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}


def _parse(spec: str) -> tuple[int, int]:
    count, period = spec.split("/")
    return int(count), _PERIODS[period.strip().lower()]


def rate_limit_public(request: Request) -> None:
    if not settings.rate_limit_enabled:
        return
    try:
        import redis

        limit, window = _parse(settings.rate_limit_public)
        client = redis.Redis.from_url(settings.redis_url, socket_timeout=2)
        ip = request.client.host if request.client else "unknown"
        bucket = int(time.time()) // window
        key = f"rl:public:{ip}:{bucket}"
        current = client.incr(key)
        if current == 1:
            client.expire(key, window)
        if current > limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
    except HTTPException:
        raise
    except Exception:
        logger.warning("Rate-limit check failed; allowing request (fail-open)")

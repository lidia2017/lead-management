"""Best-effort idempotency for the public submit endpoint.

A prospect double-clicking (or a client retry after a dropped response) should
not create duplicate leads. Clients send an ``Idempotency-Key`` header; we map
key -> created lead id in Redis with a TTL. A repeat with the same key returns
the original lead instead of inserting a new one.

Best-effort by design: if Redis is unavailable the request still succeeds
(we simply lose dedupe for that call) rather than failing the submission.
"""
from __future__ import annotations

import logging
import uuid

from app.core.config import settings

logger = logging.getLogger("idempotency")

_KEY_PREFIX = "idem:lead:"


def _client():
    import redis  # imported lazily; only needed when the feature is enabled

    return redis.Redis.from_url(settings.redis_url, socket_timeout=2)


def is_enabled() -> bool:
    return settings.idempotency_enabled


def lookup(idempotency_key: str) -> uuid.UUID | None:
    """Return a previously-created lead id for this key, if any."""
    if not idempotency_key:
        return None
    try:
        val = _client().get(_KEY_PREFIX + idempotency_key)
        return uuid.UUID(val.decode()) if val else None
    except Exception:
        logger.warning("Idempotency lookup failed; proceeding without dedupe")
        return None


def store(idempotency_key: str, lead_id: uuid.UUID) -> None:
    if not idempotency_key:
        return
    try:
        _client().set(
            _KEY_PREFIX + idempotency_key,
            str(lead_id),
            ex=settings.idempotency_ttl_seconds,
        )
    except Exception:
        logger.warning("Idempotency store failed; dedupe not recorded")

"""Best-effort, race-free idempotency for the public submit endpoint.

A prospect double-clicking (or a client retry after a dropped response) should
not create duplicate leads. Clients send an ``Idempotency-Key`` header.

Flow (all keyed in Redis with a TTL):
  1. ``lookup`` — fast path: if the key already maps to a completed lead id,
     return it without doing any work.
  2. ``reserve`` — atomic ``SET NX``: exactly one concurrent request wins and
     proceeds to create the lead; the others see the key already exists.
  3. ``finalize`` — overwrite the reservation with the real lead id.
  4. ``release`` — drop the reservation if creation failed, so a retry works.

Using ``SET NX`` (not GET-then-SET) closes the race where two concurrent
requests with the same key both create a lead.

Best-effort by design: if Redis is unavailable we log and let the request
proceed (losing dedupe for that call) rather than failing the submission.
"""
from __future__ import annotations

import logging
import uuid

from app.core.config import settings

logger = logging.getLogger("idempotency")

_KEY_PREFIX = "idem:lead:"
_PENDING = "pending"


def _client():
    import redis  # imported lazily; only needed when the feature is enabled

    return redis.Redis.from_url(settings.redis_url, socket_timeout=2)


def is_enabled() -> bool:
    return settings.idempotency_enabled


def _as_lead_id(raw: bytes | None) -> uuid.UUID | None:
    if not raw:
        return None
    val = raw.decode()
    if val == _PENDING:
        return None
    try:
        return uuid.UUID(val)
    except ValueError:
        return None


def lookup(idempotency_key: str) -> uuid.UUID | None:
    """Return a previously-created lead id for this key, if creation completed."""
    if not idempotency_key:
        return None
    try:
        return _as_lead_id(_client().get(_KEY_PREFIX + idempotency_key))
    except Exception:
        logger.warning("Idempotency lookup failed; proceeding without dedupe")
        return None


def reserve(idempotency_key: str) -> bool:
    """Atomically claim the key. Returns True if this caller won the claim.

    Fail-open: on a Redis error we return True (proceed) so the submission is
    never blocked by the idempotency store being down.
    """
    if not idempotency_key:
        return True
    try:
        acquired = _client().set(
            _KEY_PREFIX + idempotency_key,
            _PENDING,
            nx=True,
            ex=settings.idempotency_ttl_seconds,
        )
        return bool(acquired)
    except Exception:
        logger.warning("Idempotency reserve failed; proceeding without dedupe")
        return True


def finalize(idempotency_key: str, lead_id: uuid.UUID) -> None:
    if not idempotency_key:
        return
    try:
        _client().set(
            _KEY_PREFIX + idempotency_key,
            str(lead_id),
            ex=settings.idempotency_ttl_seconds,
        )
    except Exception:
        logger.warning("Idempotency finalize failed; dedupe not recorded")


def release(idempotency_key: str) -> None:
    """Drop a reservation whose creation failed, so a retry can proceed."""
    if not idempotency_key:
        return
    try:
        _client().delete(_KEY_PREFIX + idempotency_key)
    except Exception:
        logger.warning("Idempotency release failed")

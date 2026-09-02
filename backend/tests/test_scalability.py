"""Unit tests for the scalability helpers that don't require live Redis."""
from __future__ import annotations

import io
import uuid

import pytest

from app.core.ratelimit import _parse, rate_limit_public
from app.services import idempotency, lead_service
from app.services.storage import LocalFileStorage


class FakeRedis:
    """Minimal in-memory stand-in supporting the SET NX / GET / DEL we use."""

    def __init__(self) -> None:
        self.store: dict[str, bytes] = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.store:
            return None
        self.store[key] = value.encode() if isinstance(value, str) else value
        return True

    def delete(self, key):
        self.store.pop(key, None)


def test_rate_limit_spec_parsing():
    assert _parse("10/minute") == (10, 60)
    assert _parse("5/second") == (5, 1)
    assert _parse("100/hour") == (100, 3600)


def test_rate_limit_disabled_is_noop():
    # With RATE_LIMIT_ENABLED unset (default False), the dependency returns
    # without touching Redis even for a request with no client.
    class _Req:
        client = None

    assert rate_limit_public(_Req()) is None  # type: ignore[arg-type]


def test_idempotency_disabled_by_default():
    assert idempotency.is_enabled() is False


def test_submissions_are_independent_when_idempotency_disabled(client):
    # Same payload twice -> two distinct leads (dedupe is off by default).
    def submit():
        return client.post(
            "/api/leads",
            data={"first_name": "Dup", "last_name": "Check", "email": "dup@example.com"},
            files={"resume": ("cv.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
        )

    first, second = submit().json(), submit().json()
    assert first["id"] != second["id"]


def test_idempotency_reserve_is_race_free(monkeypatch):
    fake = FakeRedis()
    monkeypatch.setattr(idempotency, "_client", lambda: fake)
    monkeypatch.setattr(idempotency.settings, "idempotency_enabled", True)

    key = "same-key"
    assert idempotency.is_enabled() is True
    assert idempotency.reserve(key) is True   # first caller wins the claim
    assert idempotency.reserve(key) is False  # concurrent duplicate is blocked
    assert idempotency.lookup(key) is None    # still "pending", not a lead yet

    lead_id = uuid.uuid4()
    idempotency.finalize(key, lead_id)
    assert idempotency.lookup(key) == lead_id  # now resolves to the real lead

    idempotency.release(key)
    assert idempotency.lookup(key) is None
    assert idempotency.reserve(key) is True    # reclaimable after release


def test_idempotency_reserve_fails_open_on_redis_error(monkeypatch):
    def boom():
        raise RuntimeError("redis down")

    monkeypatch.setattr(idempotency, "_client", boom)
    monkeypatch.setattr(idempotency.settings, "idempotency_enabled", True)
    # Store unavailable -> proceed (True) rather than blocking the submission.
    assert idempotency.reserve("k") is True


def test_create_lead_removes_file_when_commit_fails(tmp_path):
    storage = LocalFileStorage(str(tmp_path))

    class BoomSession:
        def add(self, obj):
            pass

        def commit(self):
            raise RuntimeError("db down")

        def rollback(self):
            pass

        def refresh(self, obj):
            pass

    with pytest.raises(RuntimeError):
        lead_service.create_lead(
            BoomSession(),  # type: ignore[arg-type]
            first_name="A",
            last_name="B",
            email="a@b.com",
            resume_bytes=b"data",
            resume_filename="cv.pdf",
            resume_content_type="application/pdf",
            storage=storage,
        )

    # No orphaned resume left behind after the failed commit.
    assert list(tmp_path.iterdir()) == []

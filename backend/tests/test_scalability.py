"""Unit tests for the scalability helpers that don't require live Redis."""
from __future__ import annotations

import io

import pytest

from app.core.ratelimit import _parse, rate_limit_public
from app.services import idempotency


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

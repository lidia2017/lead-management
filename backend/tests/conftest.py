"""Pytest fixtures. Uses a throwaway SQLite DB + temp upload dir so tests need
no Postgres and touch no real files."""
from __future__ import annotations

import os
import tempfile

import pytest

# Configure the environment BEFORE importing app modules (settings is cached).
_TMP = tempfile.mkdtemp(prefix="leadtest-")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(_TMP, 'test.db')}"
os.environ["UPLOAD_DIR"] = os.path.join(_TMP, "uploads")
os.environ["EMAIL_BACKEND"] = "console"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["SEED_ATTORNEY_EMAIL"] = "attorney@example.com"
os.environ["SEED_ATTORNEY_PASSWORD"] = "changeme123"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.seed import seed_attorney  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_db():
    init_db()
    seed_attorney()
    yield


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def auth_headers(client: TestClient) -> dict:
    resp = client.post(
        "/api/auth/login",
        json={"email": "attorney@example.com", "password": "changeme123"},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

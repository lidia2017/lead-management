"""End-to-end API tests covering the core requirements."""
from __future__ import annotations

import io


def _submit_lead(client, email="prospect@example.com"):
    return client.post(
        "/api/leads",
        data={"first_name": "Pat", "last_name": "Prospect", "email": email},
        files={"resume": ("cv.pdf", io.BytesIO(b"%PDF-1.4 fake"), "application/pdf")},
    )


def test_health(client):
    assert client.get("/api/health").json()["status"] == "ok"


def test_public_lead_submission_creates_pending_lead(client):
    resp = _submit_lead(client)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["state"] == "PENDING"
    assert body["email"] == "prospect@example.com"
    assert body["resume_filename"] == "cv.pdf"


def test_rejects_bad_email(client):
    resp = client.post(
        "/api/leads",
        data={"first_name": "Pat", "last_name": "P", "email": "not-an-email"},
        files={"resume": ("cv.pdf", io.BytesIO(b"%PDF-1.4"), "application/pdf")},
    )
    assert resp.status_code == 422


def test_rejects_unsupported_resume_type(client):
    resp = client.post(
        "/api/leads",
        data={"first_name": "Pat", "last_name": "P", "email": "a@b.com"},
        files={"resume": ("x.exe", io.BytesIO(b"MZ"), "application/x-msdownload")},
    )
    assert resp.status_code == 400


def test_list_requires_auth(client):
    assert client.get("/api/leads").status_code == 401


def test_list_and_filter_with_auth(client, auth_headers):
    _submit_lead(client, email="one@example.com")
    resp = client.get("/api/leads", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert all(item["state"] in ("PENDING", "REACHED_OUT") for item in data["items"])

    filtered = client.get("/api/leads?state=PENDING", headers=auth_headers)
    assert filtered.status_code == 200


def test_state_transition_and_illegal_transition(client, auth_headers):
    lead_id = _submit_lead(client, email="trans@example.com").json()["id"]

    # PENDING -> REACHED_OUT is allowed.
    ok = client.patch(
        f"/api/leads/{lead_id}", json={"state": "REACHED_OUT"}, headers=auth_headers
    )
    assert ok.status_code == 200
    assert ok.json()["state"] == "REACHED_OUT"

    # REACHED_OUT -> PENDING is rejected.
    bad = client.patch(
        f"/api/leads/{lead_id}", json={"state": "PENDING"}, headers=auth_headers
    )
    assert bad.status_code == 409


def test_resume_download_requires_auth(client, auth_headers):
    lead_id = _submit_lead(client, email="dl@example.com").json()["id"]
    assert client.get(f"/api/leads/{lead_id}/resume").status_code == 401

    ok = client.get(f"/api/leads/{lead_id}/resume", headers=auth_headers)
    assert ok.status_code == 200
    assert ok.content.startswith(b"%PDF")

"""Tests for the FastAPI backend."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from api.server import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_get_default_form(client):
    resp = client.get("/form")
    assert resp.status_code == 200
    data = resp.json()
    assert "pages" in data
    assert "title" in data


def test_submit_and_retrieve(client):
    payload = {
        "form_id": "test-form",
        "responses": {"full_name": "Bob", "email": "bob@example.com"},
    }
    resp = client.post("/submit", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert body["form_id"] == "test-form"
    assert body["responses"]["full_name"] == "Bob"
    sub_id = body["id"]

    # List submissions
    resp2 = client.get("/submissions")
    assert resp2.status_code == 200
    ids = [s["id"] for s in resp2.json()]
    assert sub_id in ids

    # Get single submission
    resp3 = client.get(f"/submissions/{sub_id}")
    assert resp3.status_code == 200
    assert resp3.json()["id"] == sub_id


def test_get_missing_submission(client):
    resp = client.get("/submissions/nonexistent-id")
    assert resp.status_code == 404

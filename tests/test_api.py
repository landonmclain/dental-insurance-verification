"""Tests for the FastAPI app (api.py): health, verify, events, 404."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from insurance_verify.api import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_verify_returns_job_id():
    resp = client.post("/verify", json={"card_id": "card_0000"})
    assert resp.status_code == 200
    body = resp.json()
    assert "job_id" in body
    assert body["job_id"]


def test_verify_rejects_unknown_card():
    resp = client.post("/verify", json={"card_id": "card_9999"})
    assert resp.status_code == 404


def test_verify_rejects_bad_card_id():
    resp = client.post("/verify", json={"card_id": "../../etc/passwd"})
    assert resp.status_code == 404


def test_events_streams_result_and_end():
    # Start a verification, then read its SSE stream.
    up = client.post("/verify", json={"card_id": "card_0000"})
    job_id = up.json()["job_id"]

    with client.stream("GET", f"/events/{job_id}") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        steps = []
        result_detail = None
        for line in resp.iter_lines():
            if line and line.startswith("data: "):
                ev = json.loads(line[6:])
                steps.append(ev["step"])
                if ev["step"] == "result":
                    result_detail = ev["detail"]
                if ev["step"] == "end":
                    break

    assert "result" in steps
    assert steps[-1] == "end"
    assert result_detail is not None
    summary = json.loads(result_detail)
    assert summary["eligibility_status"] in ("active", "inactive")


def test_events_unknown_job_404():
    resp = client.get("/events/does-not-exist")
    assert resp.status_code == 404

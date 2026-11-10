"""Tests for the real-time event layer (events.py)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from insurance_verify.events import EventBroker, broker, sse_format, start_verification


def _make_gt(tmp_path: Path) -> Path:
    gt = {
        "member_id": "123456789",
        "group_id": "5121024",
        "payer_id": "AMTAS00425",
        "subscriber_first": "Jane",
        "subscriber_last": "Doe",
        "payer_name": "Ameritas",
        "plan_name": "DENTAL PLAN PLUS",
    }
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")
    (tmp_path / "card.json").write_text(json.dumps(gt))
    return png


def _drain(q, timeout: float = 5.0) -> list[dict]:
    """Drain a queue until an 'end' event or timeout."""
    events = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            ev = q.get(timeout=0.2)
        except Exception:
            continue
        events.append(ev)
        if ev.get("step") == "end":
            break
    return events


def test_start_verification_returns_job_id(tmp_path: Path):
    png = _make_gt(tmp_path)
    job_id = start_verification(str(png))
    assert job_id
    assert broker.subscribe(job_id) is not None


def test_start_verification_emits_result_and_end(tmp_path: Path):
    png = _make_gt(tmp_path)
    job_id = start_verification(str(png))
    q = broker.subscribe(job_id)
    events = _drain(q)

    steps = [e["step"] for e in events]
    # Result event must precede end.
    assert "result" in steps
    assert steps[-1] == "end"
    assert steps.index("result") < steps.index("end")

    result = next(e for e in events if e["step"] == "result")
    summary = json.loads(result["detail"])
    assert summary["eligibility_status"] in ("active", "inactive")
    assert summary["benefits"]


def test_start_verification_error_path(tmp_path: Path):
    # A nonexistent image path -> the pipeline raises -> error event emitted.
    job_id = start_verification(str(tmp_path / "missing.png"))
    q = broker.subscribe(job_id)
    events = _drain(q)
    steps = [e["step"] for e in events]
    assert "error" in steps
    assert steps[-1] == "end"


def test_sse_format():
    frame = sse_format(
        {"step": "extract", "status": "started", "detail": "Reading card", "elapsed_ms": 5}
    )
    assert frame.startswith("data: ")
    assert frame.endswith("\n\n")
    payload = json.loads(frame[len("data: ") :].strip())
    assert payload["step"] == "extract"


def test_broker_unknown_job_returns_none():
    assert broker.subscribe("does-not-exist") is None


def test_broker_close_removes_job():
    b = EventBroker()
    job = b.create_job("card.png")
    assert b.subscribe(job) is not None
    b.close(job)
    assert b.subscribe(job) is None

"""Tests for the pipeline engine."""

from __future__ import annotations

import json
from pathlib import Path

from insurance_verify.pipeline import Pipeline, run_pipeline
from insurance_verify.schemas.card import CardFields, ExtractionResult
from insurance_verify.schemas.eligibility import EligibilityRequest270, Subscriber
from insurance_verify.schemas.summary import BenefitSummary


def _make_gt(tmp_path: Path, member_id: str = "123456789", payer_id: str = "AMTAS00425") -> Path:
    """Write a synthetic ground-truth sidecar and return the PNG path."""
    gt = {
        "member_id": member_id,
        "group_id": "5121024",
        "payer_id": payer_id,
        "subscriber_first": "Jane",
        "subscriber_last": "Doe",
        "payer_name": "Ameritas",
        "plan_name": "DENTAL PLAN PLUS",
    }
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")
    (tmp_path / "card.json").write_text(json.dumps(gt))
    return png


def test_run_emits_events_in_order(tmp_path: Path):
    png = _make_gt(tmp_path)
    events: list[dict] = []
    run_pipeline(png, emit=events.append)

    steps = [e["step"] for e in events]
    # Each step emits started + done, so expect pairs in order.
    assert steps[0] == "extract"
    assert "validate" in steps
    assert "270" in steps
    assert "eligibility" in steps
    assert "summarize" in steps
    assert steps[-1] == "done"
    # Order is preserved (dedupe the started/done pairs).
    order = []
    for s in steps:
        if s != "done" and (not order or order[-1] != s):
            order.append(s)
    assert order == ["extract", "extract_result", "validate", "270", "eligibility", "summarize"]


def test_run_returns_benefit_summary(tmp_path: Path):
    png = _make_gt(tmp_path)
    summary = run_pipeline(png)
    assert isinstance(summary, BenefitSummary)
    assert summary.eligibility_status in ("active", "inactive")
    assert summary.benefits


def test_extract_reads_ground_truth_sidecar(tmp_path: Path):
    png = _make_gt(tmp_path, member_id="999888777", payer_id="AMTAS00425")
    result = Pipeline()._extract(png)
    assert result.card.member_id == "999888777"
    assert result.card.payer_id == "AMTAS00425"
    assert result.card.subscriber_first == "Jane"
    assert result.overall_confidence == 0.99
    assert result.tier == "ocr"


def test_extract_falls_back_without_sidecar(tmp_path: Path):
    png = tmp_path / "upload.png"
    png.write_bytes(b"some-image-bytes")
    result = Pipeline()._extract(png)
    # Fallback produces a plausible member id and a known payer.
    assert result.card.member_id
    assert result.card.payer_id in ("84103", "AMTAS00425", "62308", "52133", "10134")
    assert result.overall_confidence == 0.9


def test_validate_ok_for_valid_card():
    result = ExtractionResult(
        card=CardFields(member_id="123", payer_id="AMTAS00425"),
        overall_confidence=0.9,
    )
    assert Pipeline()._validate(result) is True
    assert result.needs_review is False


def test_validate_fails_without_member_id():
    result = ExtractionResult(
        card=CardFields(member_id="", payer_id="AMTAS00425"),
        overall_confidence=0.9,
    )
    assert Pipeline()._validate(result) is False
    assert result.needs_review is True


def test_validate_fails_without_payer_id():
    result = ExtractionResult(
        card=CardFields(member_id="123", payer_id=None),
        overall_confidence=0.9,
    )
    assert Pipeline()._validate(result) is False
    assert result.needs_review is True


def test_build_270_from_card():
    card = CardFields(
        member_id="123",
        payer_id="AMTAS00425",
        payer_name="Ameritas",
        subscriber_first="Jane",
        subscriber_last="Doe",
    )
    req = Pipeline()._build_270(card)
    assert isinstance(req, EligibilityRequest270)
    assert req.payer_id == "AMTAS00425"
    assert req.subscriber.member_id == "123"
    assert req.subscriber.first_name == "Jane"


def test_check_eligibility_returns_response():
    req = EligibilityRequest270(
        payer_id="AMTAS00425",
        subscriber=Subscriber(member_id="123456789"),
    )
    resp = Pipeline()._check_eligibility(req)
    assert resp.status in ("active", "inactive")
    assert resp.benefits


def test_summarize_returns_summary():
    req = EligibilityRequest270(subscriber=Subscriber(member_id="123"))
    resp = Pipeline()._check_eligibility(req)
    summary = Pipeline()._summarize(resp)
    assert isinstance(summary, BenefitSummary)
    assert summary.headline

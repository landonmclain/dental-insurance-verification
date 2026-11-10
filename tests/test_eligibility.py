"""Tests for the mock eligibility service and the benefit summarizer."""

from __future__ import annotations

import json

from insurance_verify.eligibility.mock import check_eligibility
from insurance_verify.schemas.eligibility import (
    BenefitStatus,
    EligibilityRequest270,
    EligibilityResponse271,
    Subscriber,
)
from insurance_verify.schemas.summary import BenefitItem, BenefitSummary
from insurance_verify.summarize.basic import summarize


def _req(member_id: str = "123456789") -> EligibilityRequest270:
    return EligibilityRequest270(
        payer_id="AMTAS00425",
        subscriber=Subscriber(member_id=member_id, first_name="Jane", last_name="Doe"),
    )


# --- check_eligibility ---


def test_check_eligibility_returns_response():
    resp = check_eligibility(_req())
    assert isinstance(resp, EligibilityResponse271)
    assert resp.status == "active"
    assert resp.benefits
    assert all(isinstance(b, BenefitStatus) for b in resp.benefits)


def test_check_eligibility_serves_example_fixture():
    # The mock echoes the hand-authored fixture as the raw 271, with no x12.
    resp = check_eligibility(_req())
    assert resp.x12 == ""
    body = json.loads(resp.raw)
    assert body["payerId"] == "AMTAS00425"


def test_check_eligibility_deterministic():
    a = check_eligibility(_req("111111111"))
    b = check_eligibility(_req("111111111"))
    assert a.status == b.status


def test_check_eligibility_echoes_trace_and_subscriber():
    req = _req()
    req.trace_number = "TRACE-1"
    resp = check_eligibility(req)
    assert resp.trace_number == "TRACE-1"
    assert resp.subscriber is req.subscriber


def test_check_eligibility_benefits_match_status():
    resp = check_eligibility(_req())
    for b in resp.benefits:
        assert b.status == resp.status


# --- summarize ---


def test_summarize_active_headline():
    resp = check_eligibility(_req())
    summary = summarize(resp)
    assert isinstance(summary, BenefitSummary)
    if resp.status == "active":
        assert "ACTIVE" in summary.headline
    else:
        assert "INACTIVE" in summary.headline


def test_summarize_has_benefits_and_missing():
    summary = summarize(check_eligibility(_req()))
    assert summary.benefits
    assert all(isinstance(b, BenefitItem) for b in summary.benefits)
    # Dental 271s are thin; the summarizer flags items for human confirmation.
    assert summary.missing


def test_summarize_patient_name():
    summary = summarize(check_eligibility(_req()))
    assert summary.patient_name == "Jane Doe"


def test_summarize_inactive_headline_mentions_verify():
    resp = EligibilityResponse271(
        subscriber=Subscriber(member_id="1", first_name="Jane", last_name="Doe"),
        status="inactive",
        benefits=[],
    )
    summary = summarize(resp)
    assert "INACTIVE" in summary.headline
    assert "verify" in summary.headline.lower()


def test_summarize_unknown_status():
    resp = EligibilityResponse271(status="unknown", benefits=[])
    summary = summarize(resp)
    assert "UNKNOWN" in summary.headline

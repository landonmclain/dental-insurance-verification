"""Tests for the Pydantic schemas (card, eligibility, summary)."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from insurance_verify.schemas.card import CardFields, ExtractionResult
from insurance_verify.schemas.eligibility import (
    BenefitStatus,
    EligibilityRequest270,
    EligibilityResponse271,
    Provider,
    Subscriber,
)
from insurance_verify.schemas.summary import BenefitItem, BenefitSummary

# --- CardFields ---


def test_card_fields_requires_member_id():
    with pytest.raises(ValidationError):
        CardFields()  # member_id is required


def test_card_fields_defaults():
    card = CardFields(member_id="123")
    assert card.group_id is None
    assert card.payer_id is None
    assert card.relationship == "self"
    assert card.subscriber_dob is None


def test_card_fields_rejects_bad_relationship():
    with pytest.raises(ValidationError):
        CardFields(member_id="123", relationship="cousin")


# --- ExtractionResult ---


def test_extraction_result_clamps_confidence_high():
    result = ExtractionResult(card=CardFields(member_id="1"), overall_confidence=1.5)
    assert result.overall_confidence == 1.0


def test_extraction_result_clamps_confidence_low():
    result = ExtractionResult(card=CardFields(member_id="1"), overall_confidence=-0.5)
    assert result.overall_confidence == 0.0


def test_extraction_result_defaults():
    result = ExtractionResult(card=CardFields(member_id="1"), overall_confidence=0.8)
    assert result.tier == "ocr"
    assert result.needs_review is False
    assert result.confidences == {}


# --- Eligibility schemas ---


def test_subscriber_defaults():
    s = Subscriber(member_id="ABC123")
    assert s.relationship == "self"
    assert s.first_name is None


def test_eligibility_request_270_defaults():
    req = EligibilityRequest270(subscriber=Subscriber(member_id="1"))
    # Dental care is the default service type for this pipeline.
    assert req.service_type_code == "35"
    assert req.trace_number == ""
    assert req.service_date == date.today()
    assert req.provider is None
    assert req.trading_partner_id is None


def test_eligibility_request_270_carries_provider_and_address():
    req = EligibilityRequest270(
        trading_partner_id="STEDI",
        provider=Provider(npi="1999999984", organization_name="Demo Dental Group"),
        subscriber=Subscriber(
            member_id="ABC123",
            first_name="Jane",
            last_name="Doe",
            dob=date(1990, 1, 1),
            address_line1="123 Main St",
            address_city="Springfield",
            address_state="MO",
            address_zip="65804",
        ),
    )
    assert req.trading_partner_id == "STEDI"
    assert req.provider.npi == "1999999984"
    assert req.subscriber.dob == date(1990, 1, 1)
    assert req.subscriber.address_zip == "65804"


def test_benefit_status_defaults():
    b = BenefitStatus(status="active")
    assert b.service_type_code is None
    assert b.coverage_type is None


def test_eligibility_response_271_defaults():
    resp = EligibilityResponse271()
    assert resp.status == "unknown"
    assert resp.benefits == []
    assert resp.subscriber is None


def test_eligibility_response_271_rejects_bad_status():
    with pytest.raises(ValidationError):
        EligibilityResponse271(status="bogus")


# --- Summary schemas ---


def test_benefit_item_defaults():
    item = BenefitItem(name="Cleanings")
    assert item.value is None


def test_benefit_summary_defaults():
    s = BenefitSummary()
    assert s.eligibility_status == "unknown"
    assert s.benefits == []
    assert s.missing == []
    assert s.headline == ""

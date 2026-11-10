"""Tests for the Stedi eligibility client (eligibility/stedi.py).

The HTTP call is mocked so tests stay hermetic; we verify payload building
and 271 response parsing.
"""

from __future__ import annotations

import json
import urllib.request
from datetime import date

import pytest

from insurance_verify.eligibility import stedi
from insurance_verify.schemas.eligibility import (
    EligibilityRequest270,
    Provider,
    Subscriber,
)


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = body

    def read(self):
        return json.dumps(self._body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _request() -> EligibilityRequest270:
    return EligibilityRequest270(
        trading_partner_id="STEDI",
        provider=Provider(npi="1999999984", organization_name="Demo Dental Group"),
        subscriber=Subscriber(
            member_id="SVM894853",
            first_name="Anthony",
            last_name="Graves",
            dob=date(1991, 6, 17),
        ),
    )


def test_build_payload():
    payload = stedi._build_payload(_request())
    assert payload["payerId"] == "STEDI"
    assert payload["subscriber"]["memberId"] == "SVM894853"
    assert payload["subscriber"]["dateOfBirth"] == "1991-06-17"
    assert payload["subscriber"]["name"]["person"]["firstName"] == "Anthony"
    assert payload["provider"]["npi"] == "1999999984"
    assert payload["encounter"]["services"] == [{"value": "35", "system": "STC"}]


def test_check_eligibility_parses_active(monkeypatch):
    body = {
        "benefitsInformation": [
            {"code": "1", "name": "Active Coverage", "serviceTypeCodes": ["35"]},
            {"code": "C", "name": "Deductible", "benefitAmount": "50", "serviceTypeCodes": ["35"]},
        ]
    }
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _FakeResponse(body))
    monkeypatch.setenv("STEDI_API_KEY", "test-key")

    resp = stedi.check_eligibility(_request())
    assert resp.status == "active"
    assert len(resp.benefits) == 2
    assert resp.benefits[0].status == "active"
    assert resp.benefits[1].description == "Deductible"


def test_check_eligibility_inactive_on_aaa(monkeypatch):
    body = {"AAA": [{"errorCode": "51"}]}
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _FakeResponse(body))
    monkeypatch.setenv("STEDI_API_KEY", "test-key")

    resp = stedi.check_eligibility(_request())
    assert resp.status == "inactive"


def test_check_eligibility_inactive_on_subscriber_aaa_errors(monkeypatch):
    # Stedi returns subscriber-level AAA errors (e.g. invalid member ID) here.
    body = {"subscriber": {"aaaErrors": [{"code": "72", "description": "Invalid ID"}]}}
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _FakeResponse(body))
    monkeypatch.setenv("STEDI_API_KEY", "test-key")

    resp = stedi.check_eligibility(_request())
    assert resp.status == "inactive"


def test_plan_dates_normalized_to_current_window(monkeypatch):
    # Stedi test subscribers return stale plan dates; the backend normalizes
    # them to a current window.
    body = {
        "subscriber": {"dates": {"plan": {"start": "2024-01-01", "end": "2024-12-31"}}},
        "benefitsInformation": [
            {"code": "1", "name": "Active Coverage", "serviceTypeCodes": ["35"]}
        ],
    }
    monkeypatch.setattr(urllib.request, "urlopen", lambda *a, **k: _FakeResponse(body))
    monkeypatch.setenv("STEDI_API_KEY", "test-key")

    resp = stedi.check_eligibility(_request())
    plan = json.loads(resp.raw)["subscriber"]["dates"]["plan"]
    today = date.today()
    assert plan["start"] == today.replace(day=1).isoformat()
    assert plan["end"] == date(today.year + 1, today.month, 1).isoformat()


def test_check_eligibility_requires_key(monkeypatch):
    monkeypatch.delenv("STEDI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        stedi.check_eligibility(_request())

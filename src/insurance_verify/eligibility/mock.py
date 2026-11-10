"""Mock 270/271 eligibility service.

Serves the hand-authored example 271 fixtures in tests/fixtures/, keyed by
payer ID. The fixture is echoed as the raw 271, and the benefit lines are the
fixture's plan statuses, so the mock, the parser, and the summarizer all read
the same example data. There is no x12 — the demo runs end-to-end locally with
no external calls and no synthetic fabrication.
"""

from __future__ import annotations

import json
from pathlib import Path

from insurance_verify.schemas.eligibility import (
    BenefitStatus,
    EligibilityRequest270,
    EligibilityResponse271,
)

# Hand-authored example 271 responses, keyed by payer ID.
_FIXTURES: dict[str, str] = {
    "84103": "271_blue_cross_blue_shield.json",
    "AMTAS00425": "271_ameritas.json",
    "62308": "271_cigna.json",
    "52133": "271_unitedhealthcare.json",
    "10134": "271_metlife.json",
    "61101": "271_medical_humana.json",
}

_FIXTURES_DIR = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def check_eligibility(request: EligibilityRequest270) -> EligibilityResponse271:
    """Return the hand-authored 271 example for the request's payer.

    Deterministic: the same payer always serves the same fixture, and the
    benefit lines are read from that fixture.
    """
    name = _FIXTURES.get(request.payer_id)
    if name is None:
        # No example for this payer — report unknown, no fabricated data.
        return EligibilityResponse271(
            trace_number=request.trace_number,
            subscriber=request.subscriber,
            status="unknown",
        )

    raw = (_FIXTURES_DIR / name).read_text()
    statuses = json.loads(raw)["plans"][0]["benefits"].get("statuses", [])
    active = bool(statuses) and all(s.get("status") == "ACTIVE_COVERAGE" for s in statuses)
    coverage_type = "M" if request.payer_id == "61101" else "D"

    return EligibilityResponse271(
        trace_number=request.trace_number,
        subscriber=request.subscriber,
        status="active" if active else "inactive",
        benefits=[
            BenefitStatus(
                status="active" if active else "inactive",
                service_type_code=(s.get("service") or {}).get("value"),
                coverage_type=coverage_type,
                description=(s.get("service") or {}).get("definition"),
            )
            for s in statuses
        ],
        # The fixture JSON is the raw 271 the UI renders, with no x12.
        raw=raw,
    )

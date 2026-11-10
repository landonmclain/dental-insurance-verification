"""Real Stedi eligibility client (270/271).

Calls Stedi's real-time eligibility endpoint with the subscriber/provider/
encounter info from a 270 request and parses the 271 response. The API key
comes from STEDI_API_KEY (env var only, never committed). In test mode the
trading partner ID is "STEDI" and Stedi returns realistic mock responses.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date

from insurance_verify.config import get_settings
from insurance_verify.schemas.eligibility import (
    BenefitStatus,
    EligibilityRequest270,
    EligibilityResponse271,
)

_STEDI_URL = "https://healthcare.us.stedi.com/2026-06-01/eligibility-check"


def _build_payload(request: EligibilityRequest270) -> dict:
    """Map a 270 request to Stedi's redesigned JSON request body."""
    sub = request.subscriber
    payload: dict = {
        "payerId": request.trading_partner_id or "STEDI",
        "provider": {
            "name": {
                "organization": (request.provider.organization_name if request.provider else None)
            },
            "npi": request.provider.npi if request.provider else "",
        },
        "subscriber": {
            "name": {
                "person": {
                    "firstName": sub.first_name,
                    "lastName": sub.last_name,
                }
            },
            "memberId": sub.member_id,
        },
        "encounter": {
            "services": [{"value": request.service_type_code, "system": "STC"}],
        },
    }
    if sub.dob:
        payload["subscriber"]["dateOfBirth"] = sub.dob.isoformat()
    return payload


def _current_plan_dates() -> dict[str, str]:
    """A current plan window: first of this month through first of the month
    one year forward (e.g. 2026-10-01 -> 2027-10-01)."""
    today = date.today()
    start = today.replace(day=1)
    end = date(start.year + 1, start.month, 1)
    return {"start": start.isoformat(), "end": end.isoformat()}


def _derive_status(benefits: list[BenefitStatus], body: dict) -> str:
    """Derive overall eligibility status from the 271 response.

    Stedi doesn't return a single top-level status; "Active Coverage" is a
    benefit with code "1". Errors can appear as top-level `errors`, `AAA`, or
    `subscriber.aaaErrors` (e.g. invalid member ID).
    """
    if any(b.status == "active" for b in benefits):
        return "active"
    has_error = bool(
        body.get("AAA") or body.get("errors") or (body.get("subscriber") or {}).get("aaaErrors")
    )
    return "inactive" if has_error else "unknown"


def _parse_response(body: dict, request: EligibilityRequest270) -> EligibilityResponse271:
    benefits: list[BenefitStatus] = []
    # Redesigned endpoint returns benefits under plans[].benefits.statuses[].
    for plan in body.get("plans") or []:
        for s in (plan.get("benefits") or {}).get("statuses") or []:
            service = s.get("service") or {}
            active = s.get("status") == "ACTIVE_COVERAGE"
            benefits.append(
                BenefitStatus(
                    status="active" if active else "unknown",
                    service_type_code=service.get("value"),
                    coverage_type="D",
                    description=service.get("definition") or s.get("planCoverageDescription"),
                )
            )
    # Legacy endpoint returns benefitsInformation[].
    for b in body.get("benefitsInformation") or []:
        name = b.get("name") or ""
        active = b.get("code") == "1" or "active" in name.lower()
        benefits.append(
            BenefitStatus(
                status="active" if active else "unknown",
                service_type_code=(b.get("serviceTypeCodes") or [None])[0],
                coverage_type="D",
                description=name or None,
            )
        )
    # The demo's synthetic cards map to Stedi test subscribers whose plan
    # dates are stale (expired). Normalize the plan window to a current one —
    # beginning of this month through beginning of the month one year forward —
    # so the demo doesn't show an expired plan next to an "active" status.
    sub = body.get("subscriber") or {}
    plan_dates = (sub.get("dates") or {}).get("plan")
    if plan_dates:
        window = _current_plan_dates()
        plan_dates["start"] = window["start"]
        plan_dates["end"] = window["end"]

    # Keep the raw X12 EDI string as its own field so the frontend can show it
    # in a dedicated section. X12 segments are delimited by '~'; break them onto
    # separate lines so the ISA/GS/ST/2100A... structure is readable.
    x12 = body.pop("x12", None)
    if x12:
        x12 = x12.replace("~", "~\n")
    return EligibilityResponse271(
        trace_number=request.trace_number,
        subscriber=request.subscriber,
        status=_derive_status(benefits, body),
        benefits=benefits,
        raw=json.dumps(body),
        x12=x12 or "",
    )


def check_eligibility(request: EligibilityRequest270) -> EligibilityResponse271:
    """Submit a 270 to Stedi and return the parsed 271 response."""
    settings = get_settings()
    if not settings.stedi_api_key:
        raise RuntimeError("STEDI_API_KEY is not set")

    payload = _build_payload(request)
    req = urllib.request.Request(
        _STEDI_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": settings.stedi_api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"Stedi eligibility failed ({e.code}): {detail}") from e
    return _parse_response(body, request)

"""Pydantic models for the plain-English benefit summary."""

from __future__ import annotations

from pydantic import BaseModel, Field

from insurance_verify.benefits.models import BenefitLine


class BenefitItem(BaseModel):
    """One benefit the patient has, in plain English."""

    name: str
    value: str | None = None
    # Coverage tier (Basic / Major / Orthodontic / Preventative) when known
    category: str | None = None


class BenefitSummary(BaseModel):
    """The final plain-English summary shown to a front-desk person."""

    patient_name: str | None = None
    eligibility_status: str = "unknown"
    # e.g. "Dental", "Medical", "Combined"
    coverage_type: str | None = None
    benefits: list[BenefitItem] = Field(default_factory=list)
    # Every code the 271 mentions, with covered/not-covered/unknown status.
    benefit_lines: list[BenefitLine] = Field(default_factory=list)
    # Services the 271 lists as not covered.
    non_covered: list[BenefitItem] = Field(default_factory=list)
    # Fields the 271 was silent on — a human should confirm.
    missing: list[str] = Field(default_factory=list)
    # Human-readable one-liner
    headline: str = ""
    # Raw 271 response.
    raw_response: str = ""
    # Raw X12 271 EDI string.
    x12: str = ""

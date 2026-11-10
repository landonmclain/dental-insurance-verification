"""Pydantic models for the 270/271 eligibility exchange (simplified)."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Subscriber(BaseModel):
    """Subscriber identifying info for a 270 request."""

    member_id: str
    first_name: str | None = None
    last_name: str | None = None
    dob: date | None = None
    relationship: Literal["self", "spouse", "child", "other"] = "self"
    # Subscriber address (intake data).
    address_line1: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zip: str | None = None


class Provider(BaseModel):
    """The provider (dental practice) requesting the eligibility check."""

    npi: str
    organization_name: str | None = None


class EligibilityRequest270(BaseModel):
    """A simplified 270 (eligibility/benefit inquiry) request."""

    payer_id: str | None = None
    payer_name: str | None = None
    # Stedi payer ID (trading partner service ID); "STEDI" in test mode.
    trading_partner_id: str | None = None
    subscriber: Subscriber
    provider: Provider | None = None
    # Service type being checked ("35" = dental care)
    service_type_code: str = "35"
    service_date: date = Field(default_factory=date.today)
    trace_number: str = ""


class BenefitStatus(BaseModel):
    """One benefit line from a 271 response."""

    # e.g. "active", "inactive", "terminated"
    status: str
    # e.g. "30" health benefit plan coverage
    service_type_code: str | None = None
    # e.g. "D" dental
    coverage_type: str | None = None
    description: str | None = None


class EligibilityResponse271(BaseModel):
    """A simplified 271 (eligibility/benefit response)."""

    trace_number: str = ""
    subscriber: Subscriber | None = None
    status: Literal["active", "inactive", "unknown"] = "unknown"
    benefits: list[BenefitStatus] = Field(default_factory=list)
    # Raw 271 response text.
    raw: str = ""
    # Raw X12 271 EDI string, segments on separate lines.
    x12: str = ""

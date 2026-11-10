"""Pydantic models for an insurance card and its extracted fields."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CardFields(BaseModel):
    """The fields we care about on a dental insurance card."""

    member_id: str = Field(description="Member/subscriber ID as printed on the card")
    group_id: str | None = Field(default=None, description="Group number, if present")
    payer_id: str | None = Field(default=None, description="Payer ID (clearinghouse routing)")
    subscriber_first: str | None = None
    subscriber_last: str | None = None
    subscriber_dob: date | None = None
    relationship: Literal["self", "spouse", "child", "other"] = "self"
    payer_name: str | None = None
    plan_name: str | None = None
    # Subscriber address (intake data, not printed on the card).
    subscriber_address_line1: str | None = None
    subscriber_address_city: str | None = None
    subscriber_address_state: str | None = None
    subscriber_address_zip: str | None = None


class ExtractionResult(BaseModel):
    """The result of extracting fields from a card image."""

    card: CardFields
    confidences: dict[str, float] = Field(default_factory=dict)
    overall_confidence: float = 0.0
    tier: Literal["ocr", "vlm"] = "ocr"
    needs_review: bool = False
    # Raw model output, for debugging.
    raw_text: str | None = None

    @field_validator("overall_confidence")
    @classmethod
    def _clamp(cls, v: float) -> float:
        return max(0.0, min(1.0, v))

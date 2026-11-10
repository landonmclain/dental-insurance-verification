"""Pipeline engine: extract -> validate -> 270 -> 271 -> summary, emitting
progress events via a callback.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from pathlib import Path

from insurance_verify.config import get_settings
from insurance_verify.schemas.card import CardFields, ExtractionResult
from insurance_verify.schemas.eligibility import (
    EligibilityRequest270,
    EligibilityResponse271,
    Provider,
    Subscriber,
)
from insurance_verify.schemas.summary import BenefitSummary
from synth.payers import PRACTICE, get_payer

# An event is a dict: {"step": str, "status": str, "detail": str, "elapsed_ms": int}
EventCallback = Callable[[dict], None]


def _noop(event: dict) -> None:
    pass


class Pipeline:
    """Runs the verification pipeline, emitting progress events."""

    def __init__(self, emit: EventCallback = _noop):
        self._emit = emit
        self._start = time.monotonic()

    def _event(self, step: str, status: str, detail: str = "") -> None:
        self._emit(
            {
                "step": step,
                "status": status,
                "detail": detail,
                "elapsed_ms": int((time.monotonic() - self._start) * 1000),
            }
        )

    def run(self, image_path: str | Path) -> BenefitSummary:
        """Run the full pipeline on a card image and return a benefit summary."""
        self._start = time.monotonic()

        # 1. Extract
        self._event("extract", "started", "Reading card")
        result = self._extract(image_path)
        self._event("extract", "done", f"confidence: {result.overall_confidence:.2f}")
        self._event("extract_result", "done", result.model_dump_json())

        # 2. Validate
        self._event("validate", "started", "Checking fields")
        validated = self._validate(result)
        self._event("validate", "done", "Fields OK" if validated else "Needs review")

        # 3. Build 270
        self._event("270", "started", "Building eligibility request")
        request = self._build_270(result.card)
        self._event("270", "done", f"payer: {request.payer_id or 'unknown'}")

        # 4. Eligibility call
        self._event("eligibility", "started", "Sending for verification")
        response = self._check_eligibility(request)
        self._event("eligibility", "done", f"status: {response.status}")

        # 5. Summarize
        self._event("summarize", "started", "Writing benefit summary")
        summary = self._summarize(response)
        self._event("summarize", "done", "Summary ready")

        self._event("done", "done", "Verification complete")
        return summary

    # Step implementations, selected by tier

    def _extract(self, image_path: str | Path) -> ExtractionResult:
        """mock: read the card's sidecar answer key (no model, no network).
        llm/live: real VLM OCR on the card image.
        """
        if get_settings().extraction_mode == "vlm":
            from insurance_verify.extract.vlm import extract_vlm

            return extract_vlm(image_path)

        p = Path(image_path)
        gt_path = p.with_suffix(".json")
        if gt_path.exists():
            gt = json.loads(gt_path.read_text())
            card = CardFields(
                member_id=gt.get("member_id", ""),
                group_id=gt.get("group_id"),
                payer_id=gt.get("payer_id"),
                subscriber_first=gt.get("subscriber_first"),
                subscriber_last=gt.get("subscriber_last"),
                payer_name=gt.get("payer_name"),
                plan_name=gt.get("plan_name"),
                subscriber_dob=gt.get("subscriber_dob"),
                subscriber_address_line1=gt.get("subscriber_address_line1"),
                subscriber_address_city=gt.get("subscriber_address_city"),
                subscriber_address_state=gt.get("subscriber_address_state"),
                subscriber_address_zip=gt.get("subscriber_address_zip"),
            )
            confidences = {
                k: 0.99 for k in ("member_id", "payer_id", "subscriber_first", "subscriber_last")
            }
            return ExtractionResult(
                card=card,
                confidences=confidences,
                overall_confidence=0.99,
                tier="ocr",
                needs_review=False,
            )

        # No sidecar: deterministic stub fields.
        import hashlib

        try:
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
        except OSError:
            digest = p.name
        seed = int(digest[:8], 16)
        member_id = f"{seed % 10**9:09d}"
        payer_id = ["84103", "AMTAS00425", "62308", "52133", "10134"][seed % 5]
        card = CardFields(
            member_id=member_id,
            payer_id=payer_id,
            subscriber_first="Demo",
            subscriber_last="Patient",
            payer_name=f"Payer {payer_id}",
        )
        return ExtractionResult(
            card=card,
            confidences={"member_id": 0.9, "payer_id": 0.9},
            overall_confidence=0.9,
            tier="ocr",
            needs_review=False,
        )

    def _validate(self, result: ExtractionResult) -> bool:
        """Deterministic validation: required fields present, ID format sane."""
        card = result.card
        ok = bool(card.member_id and card.payer_id)
        result.needs_review = not ok
        return ok

    def _build_270(self, card: CardFields) -> EligibilityRequest270:
        payer = get_payer(card.payer_id) if card.payer_id else None
        return EligibilityRequest270(
            payer_id=card.payer_id,
            payer_name=card.payer_name,
            # Stedi routing: test mode uses "STEDI".
            trading_partner_id=payer.stedi_payer_id if payer else None,
            provider=Provider(
                npi=PRACTICE.npi,
                organization_name=PRACTICE.organization_name,
            ),
            subscriber=Subscriber(
                member_id=card.member_id,
                first_name=card.subscriber_first,
                last_name=card.subscriber_last,
                dob=card.subscriber_dob,
                address_line1=card.subscriber_address_line1,
                address_city=card.subscriber_address_city,
                address_state=card.subscriber_address_state,
                address_zip=card.subscriber_address_zip,
            ),
        )

    def _check_eligibility(self, request: EligibilityRequest270) -> EligibilityResponse271:
        """Real Stedi 270/271 call, or the deterministic mock for tests."""
        if get_settings().eligibility_mode == "stedi":
            from insurance_verify.eligibility.stedi import check_eligibility

            return check_eligibility(request)
        from insurance_verify.eligibility.mock import check_eligibility

        return check_eligibility(request)

    def _summarize(self, response: EligibilityResponse271) -> BenefitSummary:
        from insurance_verify.summarize.basic import summarize

        return summarize(response)


def run_pipeline(image_path: str | Path, emit: EventCallback = _noop) -> BenefitSummary:
    """Convenience wrapper: run the pipeline on an image, emitting events."""
    return Pipeline(emit=emit).run(image_path)

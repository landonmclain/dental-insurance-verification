"""Normalized benefit models produced by parsing a raw 271 response.

The raw Stedi 271 spreads benefit data across several sub-arrays
(``statuses``, ``coPayment``, ``coInsurance``, ``deductible``,
``outOfPocket``, ``limitations``, ``nonCovered``), each keyed by a service
code (CDT or STC). ``parse_271`` joins them into a single ``BenefitCatalog``
so the summary and coverage search have one source of truth.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BenefitLimit(BaseModel):
    """One limitation on a service, typed so the UI can tell them apart.

    A 271 limitation is either a dollar benefit maximum (e.g. "$1500 lifetime
    max"), a visit/quantity limit (e.g. "2 visits per calendar year"), a bare
    list of CDT codes, or a free-text note. ``codes`` holds the CDT procedure
    codes the limit applies to, when the payer reports them alongside it.
    """

    kind: Literal["dollar", "visits", "codes", "note"]
    # Human-readable text, e.g. "$1500 lifetime max" or "2 visits per year"
    text: str
    # CDT procedure codes this limit applies to (e.g. ["D0210", "D0330"])
    codes: list[str] = Field(default_factory=list)


class BenefitLine(BaseModel):
    """One service (procedure) and everything the 271 says about it."""

    # Service code, e.g. "D0120" (CDT) or "35" (STC)
    code: str
    # Code system: "CDT" or "STC"
    system: str | None = None
    # Human description (Stedi's definition, or the plan coverage description)
    description: str | None = None
    # Category from the code map (e.g. "Preventive", "Restorative")
    category: str | None = None
    # Coverage status from statuses[], e.g. "ACTIVE_COVERAGE"
    status: str | None = None
    coverage_level: str | None = None
    # Money figures, joined from the coPayment/coInsurance/deductible/outOfPocket
    # sub-arrays by service code. Strings because Stedi returns them as strings.
    copay: str | None = None
    coinsurance: str | None = None
    deductible: str | None = None
    out_of_pocket: str | None = None
    # Typed limitations (dollar maxes, visit limits, codes, notes)
    limitations: list[BenefitLimit] = Field(default_factory=list)
    # True when the service appears in the nonCovered[] sub-array
    non_covered: bool = False
    # Prior authorization requirement from priorAuthIndicator, normalized to
    # "required" / "not required" / "unknown" (X12 authOrCertIndicator).
    prior_auth: str | None = None


class PlanFigures(BaseModel):
    """Plan-level money figures, kept as raw-ish entries for the summary."""

    deductible: list[dict] = Field(default_factory=list)
    out_of_pocket: list[dict] = Field(default_factory=list)
    copay: list[dict] = Field(default_factory=list)
    coinsurance: list[dict] = Field(default_factory=list)


class BenefitCatalog(BaseModel):
    """The full normalized view of one 271 response."""

    plan_name: str | None = None
    # Every service code seen in any benefit sub-array, joined
    lines: list[BenefitLine] = Field(default_factory=list)
    figures: PlanFigures = Field(default_factory=PlanFigures)

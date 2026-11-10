"""Rule-based 271 -> plain-English benefit summary, driven by the parsed catalog.

Parses the raw 271 with ``parse_271`` and builds the summary from the real
data: plan-level deductible / out-of-pocket max, per-category copay and
coinsurance, limitations, and non-covered services. ``missing`` lists fields
the 271 was silent on, so a human knows what to confirm.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from insurance_verify.benefits import BenefitCatalog, detect_card_type, parse_271
from insurance_verify.benefits.codes import categorize, describe
from insurance_verify.schemas.eligibility import EligibilityResponse271
from insurance_verify.schemas.summary import BenefitItem, BenefitSummary

# Generic plan-level buckets, not dental services a front desk acts on.
_SKIP_CATEGORIES = {"Health Coverage", "Dental Care"}

# Derived coverage-tier data: code ranges -> coverage tier (own data, committed).
_DATA = Path(__file__).parent.parent / "benefits" / "data"
try:
    _COVERAGE_CATEGORIES = json.loads((_DATA / "coverage_categories.json").read_text())
except FileNotFoundError:
    _COVERAGE_CATEGORIES = []


def _code_category(code: str) -> str | None:
    """Resolve a CDT code to its coverage tier (Basic/Major/Orthodontic/...)."""
    for section in _COVERAGE_CATEGORIES:
        for rng in section["ranges"]:
            parts = [p.strip() for p in rng.replace("\u2013", "-").split("-")]
            start = parts[0]
            end = parts[1] if len(parts) > 1 else start
            if start <= code <= end:
                return section["category"]
    return None


def _is_zero(value: str | None) -> bool:
    """True when a money/percent value is zero (e.g. a $0 copay)."""
    if value is None:
        return False
    try:
        return float(str(value).replace("$", "").replace(",", "")) == 0
    except (TypeError, ValueError):
        return False


def _plural(n: str, word: str) -> str:
    base = word[:-1] if word.endswith("s") else word  # source is often already plural
    return base if n == "1" else f"{base}s"


def _clean_limit(text: str) -> str:
    """Normalize raw payer limitation text into something readable."""
    t = text.strip()
    if not t:
        return t
    # "Age max 15" -> "Up to age 15"
    m = re.match(r"^Age max\s+(\d+)$", t, re.I)
    if m:
        return f"Up to age {m.group(1)}"
    # "1 VISITS per 6 MONTH" -> "1 visit per 6 months"
    m = re.match(r"^(\d+)\s+([A-Z]+)\s+per\s+(\d+)\s+([A-Z]+)$", t)
    if m:
        qty, qunit, per, punit = m.groups()
        return f"{qty} {_plural(qty, qunit.lower())} per {per} {_plural(per, punit.lower())}"
    # Title-case all-caps words ("SEALANTS ARE COVERED..." -> "Sealants Are Covered...")
    return re.sub(r"\b([A-Z]{2,})\b", lambda mm: mm.group(1).title(), t)


def _pct(value: str | None) -> str | None:
    """Coinsurance comes back as a fraction (0.1 = 10%); render as a percent."""
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return str(value)
    if 0 < f <= 1:
        return f"{int(round(f * 100))}%"
    return f"{int(round(f))}%"


def _money(value: str | None) -> str | None:
    """Render a money string, adding a $ if it's a bare number."""
    if value is None:
        return None
    v = str(value).strip()
    if v and v[0].isdigit():
        return f"${v}"
    return v


def _figure(figures: list[dict]) -> str | None:
    """Format the first money figure (e.g. deductible) as '$X per PERIOD'."""
    for f in figures:
        amount = f.get("amount")
        if amount is None:
            continue
        period = f.get("time_period")
        base = _money(str(amount))
        if period:
            return f"{base} per {period.replace('_', ' ').title()}"
        return base
    return None


def _category_benefits(catalog: BenefitCatalog) -> list[BenefitItem]:
    """Per-category copay/coinsurance for covered services. A line counts as
    covered when it has ACTIVE_COVERAGE status OR carries copay/coinsurance
    data — some payers report money in a separate sub-array with no status.
    """
    by_cat: dict[str, list] = {}
    for line in catalog.lines:
        if not line.category:
            continue
        if line.category in _SKIP_CATEGORIES:
            continue
        if line.status != "ACTIVE_COVERAGE" and not (line.coinsurance or line.copay):
            continue
        by_cat.setdefault(line.category, []).append(line)

    items: list[BenefitItem] = []
    for cat in sorted(by_cat):
        lines = by_cat[cat]
        coins = next((_pct(ln.coinsurance) for ln in lines if ln.coinsurance), None)
        copay = next(
            (_money(ln.copay) for ln in lines if ln.copay and not _is_zero(ln.copay)),
            None,
        )
        value = None
        if coins and copay:
            value = f"Coinsurance {coins} · Copay {copay}"
        elif coins:
            value = f"Coinsurance {coins}"
        elif copay:
            value = f"Copay {copay}"
        if not value:
            continue  # no real copay/coinsurance — don't show a bare "—"
        items.append(BenefitItem(name=f"{cat} coverage", value=value))
    return items


def _limitations(catalog: BenefitCatalog) -> list[BenefitItem]:
    """Frequency/quantity limits from the 271, grouped per code."""
    by_code: dict[str, list] = {}
    systems: dict[str, str | None] = {}
    for line in catalog.lines:
        if not line.limitations:
            continue
        by_code.setdefault(line.code or "Limit", []).extend(line.limitations)
        if line.code:
            systems.setdefault(line.code, line.system)

    items: list[BenefitItem] = []
    for code in sorted(by_code):
        seen: set[str] = set()
        uniq: list[str] = []
        for lim in by_code[code]:
            text = _clean_limit(lim.text)
            if text in seen:
                continue
            seen.add(text)
            uniq.append(text)
        system = systems.get(code)
        desc = describe(code, system)
        name = f"{code} · {desc}" if desc else code
        items.append(
            BenefitItem(
                name=name,
                value=" · ".join(uniq),
                category=_code_category(code) or categorize(code, system),
            )
        )
    return items


def _non_covered(catalog: BenefitCatalog) -> list[BenefitItem]:
    """Services the 271 explicitly lists as not covered."""
    items: list[BenefitItem] = []
    for line in catalog.lines:
        if not line.non_covered:
            continue
        items.append(
            BenefitItem(
                name=f"{line.code} — {line.description or line.category or 'service'}",
                value="Not covered",
            )
        )
    return items


def summarize(response: EligibilityResponse271) -> BenefitSummary:
    """Turn a 271 response into a plain-English benefit summary."""
    sub = response.subscriber
    name = None
    if sub and (sub.first_name or sub.last_name):
        name = f"{sub.first_name or ''} {sub.last_name or ''}".strip()

    status = response.status
    status_label = {
        "active": "ACTIVE",
        "inactive": "INACTIVE",
        "unknown": "UNKNOWN",
    }.get(status, status.upper())

    try:
        catalog = parse_271(response.raw) if response.raw else BenefitCatalog()
    except (json.JSONDecodeError, ValueError):
        # Mock/legacy responses aren't JSON; fall back to an empty catalog.
        catalog = BenefitCatalog()

    benefits: list[BenefitItem] = []
    deductible = _figure(catalog.figures.deductible)
    oop = _figure(catalog.figures.out_of_pocket)
    ded_first = catalog.figures.deductible[0] if deductible else {}
    oop_first = catalog.figures.out_of_pocket[0] if oop else {}
    ded_value = "None" if _is_zero(ded_first.get("amount")) else deductible
    oop_value = "None" if _is_zero(oop_first.get("amount")) else oop
    if deductible:
        benefits.append(BenefitItem(name="Deductible", value=ded_value))
    if oop:
        benefits.append(BenefitItem(name="Out-of-pocket max", value=oop_value))
    benefits += _category_benefits(catalog)
    benefits += _limitations(catalog)

    # Non-covered services render in their own panel.
    non_covered = _non_covered(catalog)

    # Fields the 271 was silent on — a human should confirm.
    missing: list[str] = []
    if not deductible:
        missing.append("Deductible")
    if not oop:
        missing.append("Out-of-pocket maximum")
    if not any(ln.category == "Orthodontics" for ln in catalog.lines):
        missing.append("Orthodontic coverage")
    if not any(ln.category == "Waiting Period" for ln in catalog.lines):
        missing.append("Waiting periods")

    coverage_type = detect_card_type(catalog).title()
    coverage_phrase = (
        f" with {coverage_type.lower()} coverage" if coverage_type != "Unknown" else ""
    )
    headline = (
        f"{name or 'Patient'} is {status_label}{coverage_phrase}."
        if status == "active"
        else f"{name or 'Patient'} is {status_label} — verify before treatment."
    )

    return BenefitSummary(
        patient_name=name,
        eligibility_status=status,
        coverage_type=coverage_type,
        benefits=benefits,
        benefit_lines=catalog.lines,
        non_covered=non_covered,
        missing=missing,
        headline=headline,
        raw_response=response.raw,
        x12=response.x12,
    )

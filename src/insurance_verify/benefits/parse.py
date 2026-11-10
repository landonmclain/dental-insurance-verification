"""Parse a raw Stedi 271 response into a normalized BenefitCatalog.

The 271 spreads benefit data across several sub-arrays under
``plans[].benefits``: ``statuses`` (coverage status), ``coPayment``,
``coInsurance``, ``deductible``, ``outOfPocket`` (money), ``limitations``,
and ``nonCovered``. Each entry carries a ``service`` object with a ``value``
(the CDT or STC code) and ``system``. This module joins them by service code
into one catalog, so the summary and coverage search read a single structure.
"""

from __future__ import annotations

import json
import re

from insurance_verify.benefits.codes import categorize, describe
from insurance_verify.benefits.models import (
    BenefitCatalog,
    BenefitLimit,
    BenefitLine,
    PlanFigures,
)

# A CDT procedure code, e.g. D2140.
_CDT_RE = re.compile(r"^D\d{4}$")

# Service type codes that indicate a dental plan. STC 35 ("Dental Care") is
# excluded — it appears in medical plans too, so it is not a discriminator.
_DENTAL_STCS = {"23", "24", "25", "26", "32", "36", "38", "39", "40", "41"}
# Service type codes that indicate a medical plan.
_MEDICAL_STCS = {"1", "33", "47", "48", "49", "50", "54", "86", "88", "98", "AL", "MH", "UC"}


def _index(items: list[dict] | None) -> dict[str, list[dict]]:
    """Group benefit entries by their service code."""
    out: dict[str, list[dict]] = {}
    for it in items or []:
        code = (it.get("service") or {}).get("value")
        if code is None:
            continue
        out.setdefault(code, []).append(it)
    return out


def _first(items: list[dict] | None, key: str) -> str | None:
    """First non-empty value of ``key`` across the entries for a code."""
    for it in items or []:
        v = it.get(key)
        if v not in (None, ""):
            return str(v)
    return None


def _coinsurance_is_type_marker(items: list[dict] | None) -> bool:
    """True when a payer uses the coInsurance percent field as a procedure-type
    marker instead of a real coinsurance percentage (Ameritas does this). When
    present, coinsurance is suppressed for the whole response.
    """
    for it in items or []:
        for m in it.get("messages") or []:
            if isinstance(m, str) and "TYPE" in m.upper() and "COVERED AT" in m.upper():
                return True
    return False


def _system_of(code: str, *indexes: dict[str, list[dict]]) -> str | None:
    for idx in indexes:
        for it in idx.get(code) or []:
            sys = (it.get("service") or {}).get("system")
            if sys:
                return sys
    return None


def _normalize_prior_auth(v: str) -> str:
    """Map Stedi's priorAuthIndicator to a readable value.

    X12 authOrCertIndicator: Y = prior auth required, N = not required,
    U = unknown. Stedi returns values like "NOT_REQUIRED" and "U".
    """
    up = v.upper()
    if up in ("Y", "YES", "REQUIRED", "REQUIRED_YES"):
        return "required"
    if up in ("N", "NO", "NOT_REQUIRED", "NOT_REQUIRED_NO"):
        return "not required"
    if up in ("U", "UNKNOWN"):
        return "unknown"
    return v.lower().replace("_", " ")


def _prior_auth(code: str, *indexes: dict[str, list[dict]]) -> str | None:
    """First non-empty priorAuthIndicator across the entries for a code."""
    for idx in indexes:
        for it in idx.get(code) or []:
            v = it.get("priorAuthIndicator")
            if v not in (None, ""):
                return _normalize_prior_auth(str(v))
    return None


def _is_cdt_code_list(msg: str) -> bool:
    """True when a message is a space-separated list of CDT procedure codes."""
    tokens = msg.split()
    return len(tokens) > 0 and all(_CDT_RE.match(t) for t in tokens)


def _fmt_period(period: str) -> str:
    """Turn a raw timePeriod into a readable phrase."""
    return {
        "LIFETIME": "lifetime max",
        "LIFETIME_REMAINING": "lifetime remaining",
        "CALENDAR_YEAR": "per calendar year",
        "BENEFIT_YEAR": "per benefit year",
        "REMAINING": "remaining",
    }.get(period, period.replace("_", " ").lower())


def _plural(n: str, word: str) -> str:
    """Singular/plural a qualifier like VISITS -> visit(s)."""
    base = word[:-1] if word.upper().endswith("S") else word
    return base if n == "1" else f"{base}s"


def _delivered(d: dict, key: str, prefix: str = "") -> str | None:
    """One delivery limit phrase, e.g. "2 visit(s)" or "per 12 month(s)"."""
    entry = d.get(key) or {}
    value = entry.get("value")
    if value is None:
        return None
    qualifier = entry.get("qualifier", "")
    return f"{prefix}{value} {_plural(str(value), qualifier).lower()}"


def _limitations(items: list[dict] | None) -> list[BenefitLimit]:
    """Typed limitations (dollar maxes, visit limits, code lists, notes) for a
    code. CDT code lists in messages attach to the limit they belong to.
    """
    out: list[BenefitLimit] = []
    for it in items or []:
        codes: list[str] = []
        notes: list[str] = []
        for msg in it.get("messages") or []:
            if not isinstance(msg, str) or not msg:
                continue
            if _is_cdt_code_list(msg):
                codes.extend(msg.split())
            elif len(msg) < 80:
                notes.append(msg)

        # Dollar benefit maximum, e.g. "$1500 lifetime max"
        if it.get("amount") is not None:
            amt = it["amount"]
            if isinstance(amt, (int, float)) or (isinstance(amt, str) and amt.isdigit()):
                amt = f"${amt}"
            period = _fmt_period(it.get("timePeriod", ""))
            out.append(BenefitLimit(kind="dollar", text=f"{amt} {period}".strip(), codes=codes))
            out.extend(BenefitLimit(kind="note", text=n) for n in notes)
            continue

        # Visit/quantity limit, e.g. "2 visits per calendar year"
        parts: list[str] = []
        q = it.get("quantity")
        if isinstance(q, dict) and q.get("value") is not None:
            parts.append(f"{q['value']} {_plural(str(q['value']), q.get('qualifier', '')).lower()}")
        elif isinstance(q, (int, float, str)) and q not in (None, ""):
            parts.append(str(q))
        for sl in it.get("serviceLimits") or []:
            d = sl.get("delivery") or {}
            for key, prefix in (("quantity", ""), ("frequency", "per "), ("period", "")):
                seg = _delivered(d, key, prefix)
                if seg:
                    parts.append(seg)
            if sl.get("ageMaximum") is not None:
                parts.append(f"up to age {sl['ageMaximum']}")
        tp = it.get("timePeriod")
        if tp:
            parts.append(_fmt_period(tp))
        if parts:
            out.append(BenefitLimit(kind="visits", text=", ".join(parts), codes=codes))
            out.extend(BenefitLimit(kind="note", text=n) for n in notes)
            continue

        # Only messages: a bare code list or a note
        if codes:
            out.append(BenefitLimit(kind="codes", text=" ".join(codes), codes=codes))
        out.extend(BenefitLimit(kind="note", text=n) for n in notes)
    return out


def _figures(items: list[dict] | None) -> list[dict]:
    """Keep raw money entries (amount/percent, time period, network, code)."""
    out: list[dict] = []
    for it in items or []:
        svc = it.get("service") or {}
        entry = {
            "code": svc.get("value"),
            "system": svc.get("system"),
            "amount": it.get("amount"),
            "percent": it.get("percent"),
            "time_period": it.get("timePeriod"),
            "network": (it.get("network") or {}).get("indicator"),
        }
        out.append({k: v for k, v in entry.items() if v is not None})
    return out


def detect_card_type(catalog: BenefitCatalog) -> str:
    """Classify the plan as dental, medical, or unknown from the 271 codes.

    STC 35 (Dental Care) appears in medical plans too, so it is not used.
    """
    codes = {ln.code for ln in catalog.lines}
    if any(ln.system == "CDT" for ln in catalog.lines) or (codes & _DENTAL_STCS):
        return "dental"
    if codes & _MEDICAL_STCS:
        return "medical"
    return "unknown"


def parse_271(raw: str) -> BenefitCatalog:
    """Parse a raw 271 JSON string into a normalized BenefitCatalog."""
    body = json.loads(raw)
    catalog = BenefitCatalog()

    for plan in body.get("plans") or []:
        b = plan.get("benefits") or {}
        statuses = _index(b.get("statuses"))
        copay = _index(b.get("coPayment"))
        coinsurance = _index(b.get("coInsurance"))
        deductible = _index(b.get("deductible"))
        oop = _index(b.get("outOfPocket"))
        limitations = _index(b.get("limitations"))
        non_covered = _index(b.get("nonCovered"))
        # Ameritas-style: percent field is a type marker, not a real coinsurance.
        coinsurance_is_type_marker = _coinsurance_is_type_marker(b.get("coInsurance"))

        # Union of every service code seen in any sub-array.
        all_codes: set[str] = set()
        for idx in (statuses, copay, coinsurance, deductible, oop, limitations, non_covered):
            all_codes.update(idx.keys())

        for code in sorted(all_codes):
            st = statuses.get(code)
            svc = (st[0].get("service") or {}) if st else {}
            system = svc.get("system") or _system_of(
                code, copay, coinsurance, deductible, oop, limitations, non_covered
            )
            line = BenefitLine(
                code=code,
                system=system,
                description=svc.get("definition")
                or (st[0].get("planCoverageDescription") if st else None)
                or describe(code, system),
                category=categorize(code, system),
                status=st[0].get("status") if st else None,
                coverage_level=st[0].get("coverageLevel") if st else None,
                copay=_first(copay.get(code), "amount"),
                coinsurance=(
                    None if coinsurance_is_type_marker else _first(coinsurance.get(code), "percent")
                ),
                deductible=_first(deductible.get(code), "amount"),
                out_of_pocket=_first(oop.get(code), "amount"),
                limitations=_limitations(limitations.get(code)),
                non_covered=code in non_covered,
                prior_auth=_prior_auth(
                    code, statuses, copay, coinsurance, deductible, oop, limitations, non_covered
                ),
            )
            catalog.lines.append(line)

        catalog.plan_name = plan.get("name")
        catalog.figures = PlanFigures(
            deductible=_figures(b.get("deductible")),
            out_of_pocket=_figures(b.get("outOfPocket")),
            copay=_figures(b.get("coPayment")),
            coinsurance=_figures(b.get("coInsurance")),
        )
        # Only the first plan for now; multi-plan handling is a later concern.
        break

    return catalog

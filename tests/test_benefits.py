"""Tests for the 271 parser and data-driven summary, against real fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

from insurance_verify.benefits import detect_card_type, parse_271
from insurance_verify.schemas.eligibility import EligibilityResponse271
from insurance_verify.summarize.basic import summarize

FIXTURES = Path(__file__).parent / "fixtures"


def _raw(name: str) -> str:
    return (FIXTURES / name).read_text()


@pytest.fixture(scope="module")
def fixtures() -> dict[str, str]:
    return {p.stem: p.read_text() for p in FIXTURES.glob("271_*.json")}


# --- Parser ---------------------------------------------------------------


def test_parses_all_fixtures(fixtures):
    for name, raw in fixtures.items():
        cat = parse_271(raw)
        assert cat.lines, f"{name}: expected at least one benefit line"


def test_joins_money_subarrays_by_code(fixtures):
    # UHC reports CDT codes with copay/coinsurance/deductible in sub-arrays.
    cat = parse_271(fixtures["271_unitedhealthcare"])
    d0120 = next(ln for ln in cat.lines if ln.code == "D0120")
    assert d0120.status == "ACTIVE_COVERAGE"
    assert d0120.copay is not None
    assert d0120.coinsurance is not None
    assert d0120.deductible is not None


def test_uhc_cdt_granularity(fixtures):
    cat = parse_271(fixtures["271_unitedhealthcare"])
    cdt = [ln for ln in cat.lines if ln.system == "CDT"]
    assert cdt, "UHC should report CDT procedure codes"
    assert any(ln.code == "D0120" for ln in cdt)


def test_cigna_stc_only(fixtures):
    cat = parse_271(fixtures["271_cigna"])
    assert all(ln.system == "STC" for ln in cat.lines), "Cigna reports only STC codes"
    assert any(ln.code == "35" for ln in cat.lines)


def test_non_covered_detected(fixtures):
    cat = parse_271(fixtures["271_unitedhealthcare"])
    non = [ln for ln in cat.lines if ln.non_covered]
    assert non, "UHC fixture should contain non-covered services"
    assert all(ln.non_covered for ln in non)


def test_limitations_parsed(fixtures):
    cat = parse_271(fixtures["271_unitedhealthcare"])
    limited = [ln for ln in cat.lines if ln.limitations]
    assert limited, "UHC fixture should contain limitations"
    # Limitations are typed (dollar/visits/codes/note) with clean text.
    for ln in limited:
        for lim in ln.limitations:
            assert lim.kind in {"dollar", "visits", "codes", "note"}, lim
            assert lim.text and not lim.text.startswith("{"), lim


def test_cigna_limits_are_typed(fixtures):
    # Cigna reports dollar benefit maximums and visit limits; the parser
    # separates them and labels the lifetime max vs. remaining balance.
    cat = parse_271(fixtures["271_cigna"])
    xray = next(ln for ln in cat.lines if ln.code == "4")
    dollars = [lim for lim in xray.limitations if lim.kind == "dollar"]
    visits = [lim for lim in xray.limitations if lim.kind == "visits"]
    assert dollars, "code 4 should have dollar benefit maximums"
    assert visits, "code 4 should have visit limits"
    assert any("lifetime max" in d.text for d in dollars)
    assert any("lifetime remaining" in d.text for d in dollars)
    assert any(d.codes for d in dollars), "dollar limits should carry their CDT codes"


def test_categories_assigned(fixtures):
    cat = parse_271(fixtures["271_cigna"])
    assert all(ln.category for ln in cat.lines), "every line should get a category"


def test_plan_figures(fixtures):
    cat = parse_271(fixtures["271_unitedhealthcare"])
    assert cat.figures.deductible
    assert cat.figures.out_of_pocket
    assert cat.figures.copay
    assert cat.figures.coinsurance


def test_prior_auth_parsed(fixtures):
    # Metlife is the only fixture that reports priorAuthIndicator: NOT_REQUIRED
    # on the plan status, U (unknown) on the rest.
    cat = parse_271(fixtures["271_metlife"])
    with_auth = [ln for ln in cat.lines if ln.prior_auth]
    assert with_auth, "Metlife fixture should carry priorAuthIndicator"
    assert any(ln.prior_auth == "not required" for ln in with_auth)
    assert all(ln.prior_auth in {"not required", "unknown"} for ln in with_auth)


def test_prior_auth_absent_elsewhere(fixtures):
    # Payers that don't report priorAuthIndicator get no prior_auth value.
    for name in ("271_ameritas", "271_cigna", "271_unitedhealthcare"):
        cat = parse_271(fixtures[name])
        assert all(ln.prior_auth is None for ln in cat.lines), name


def test_detect_card_type_medical(fixtures):
    # A medical 271 (Humana) has no CDT codes and medical service types.
    cat = parse_271(fixtures["271_medical_humana"])
    assert detect_card_type(cat) == "medical"


def test_detect_card_type_dental(fixtures):
    # Dental plans report CDT codes and/or dental service types.
    for name in (
        "271_ameritas",
        "271_blue_cross_blue_shield",
        "271_cigna",
        "271_metlife",
        "271_unitedhealthcare",
    ):
        cat = parse_271(fixtures[name])
        assert detect_card_type(cat) == "dental", name


def test_summary_coverage_type_medical(fixtures):
    s = summarize(EligibilityResponse271(status="active", raw=fixtures["271_medical_humana"]))
    assert s.coverage_type == "Medical"


def test_summary_coverage_type_dental(fixtures):
    s = summarize(EligibilityResponse271(status="active", raw=fixtures["271_cigna"]))
    assert s.coverage_type == "Dental"


# --- Summarizer -----------------------------------------------------------


def test_summary_is_data_driven(fixtures):
    s = summarize(EligibilityResponse271(status="active", raw=fixtures["271_unitedhealthcare"]))
    names = {b.name for b in s.benefits}
    values = {b.value for b in s.benefits}
    # Data comes from the 271, not a hardcoded list.
    assert "Deductible" in names
    assert "Out-of-pocket max" in names
    assert "Cleanings" not in names
    # Hardcoded values (100%, 80%) must be gone.
    assert "100%" not in values
    assert "80%" not in values


def test_summary_shows_real_deductible(fixtures):
    s = summarize(EligibilityResponse271(status="active", raw=fixtures["271_ameritas"]))
    ded = next(b for b in s.benefits if b.name == "Deductible")
    assert ded.value and "$50" in ded.value


def test_summary_shows_category_coinsurance(fixtures):
    s = summarize(EligibilityResponse271(status="active", raw=fixtures["271_cigna"]))
    restorative = next(b for b in s.benefits if b.name == "Restorative coverage")
    assert restorative.value and "50%" in restorative.value


def test_summary_lists_non_covered(fixtures):
    s = summarize(EligibilityResponse271(status="active", raw=fixtures["271_unitedhealthcare"]))
    # Non-covered services live in their own field, not the summary benefits.
    assert s.non_covered, "summary should list non-covered services"
    assert all(b.value == "Not covered" for b in s.non_covered)
    assert not any(b.value == "Not covered" for b in s.benefits)


def test_summary_missing_is_dynamic(fixtures):
    # UHC has an OOP max, so it should NOT be flagged missing.
    s = summarize(EligibilityResponse271(status="active", raw=fixtures["271_unitedhealthcare"]))
    assert "Out-of-pocket maximum" not in s.missing
    # Ameritas has no OOP max, so it should be flagged.
    s2 = summarize(EligibilityResponse271(status="active", raw=fixtures["271_ameritas"]))
    assert "Out-of-pocket maximum" in s2.missing

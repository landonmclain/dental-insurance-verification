from pathlib import Path

from insurance_verify.ask import build_context
from insurance_verify.benefits import parse_271

FIXTURES = Path(__file__).parent / "fixtures"


def test_build_context_includes_payer_info():
    raw = (FIXTURES / "271_ameritas.json").read_text()
    cat = parse_271(raw)
    ctx = build_context(cat, raw, "Ameritas")
    assert "PAYER: Ameritas" in ctx
    assert "ELIGIBILITY STATUS: active" in ctx
    assert "PAYER ID: AMTAS00425" in ctx
    assert "8004875553" in ctx  # payer phone from the 271
    assert "GROUP@AMERITAS.COM" in ctx


def test_build_context_includes_subscriber_provider_and_card():
    raw = (FIXTURES / "271_ameritas.json").read_text()
    cat = parse_271(raw)
    card = {
        "payer_name": "Ameritas",
        "plan_name": "DENTAL PLAN PLUS",
        "group_id": "5121024",
        "member_id": "007007007",
        "subscriber_first": "FALCON",
        "subscriber_last": "DENT",
    }
    ctx = build_context(cat, raw, "Ameritas", card)
    # Subscriber echoed in the 271
    assert "SUBSCRIBER: FALCON DENT" in ctx
    assert "member 007007007" in ctx
    assert "DOB 1985-06-07" in ctx
    assert "gender FEMALE" in ctx
    assert "987 SOARING EAGLE LANE" in ctx
    # Provider from the 271
    assert "PROVIDER: NPI 1999999984" in ctx
    assert "type PROVIDER" in ctx
    # Card fields from OCR extraction
    assert "CARD: payer Ameritas" in ctx
    assert "group 5121024" in ctx


def test_build_context_without_payer_name():
    raw = (FIXTURES / "271_ameritas.json").read_text()
    cat = parse_271(raw)
    ctx = build_context(cat, raw)
    assert "PAYER: Unknown" in ctx
    assert "ELIGIBILITY STATUS: active" in ctx

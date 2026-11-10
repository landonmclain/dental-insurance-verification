"""Tier tests: one mode flag bundles every backend switch.

mock: stubbed extraction from the card's sidecar answer key, mock 271, demo
labels, no ask chat — no keys, no model, no network.
llm: real VLM OCR, mock 271, demo labels, ask chat — the key for the model
providers the tier's models use (OpenRouter, OpenAI, or neither for the local
model server) is required.
live: real VLM OCR, real Stedi 270/271, reference descriptions, ask chat —
the model providers' keys and Stedi required.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from insurance_verify import ask
from insurance_verify.api import app
from insurance_verify.benefits.codes import describe
from insurance_verify.config import get_settings
from insurance_verify.pipeline import Pipeline
from insurance_verify.schemas.eligibility import EligibilityResponse271

client = TestClient(app)

CARD = "data/cards/card_0000.png"


def test_mock_mode_bundles_switches():
    s = get_settings()
    assert s.mode == "mock"
    assert s.extraction_mode == "stub"
    assert s.eligibility_mode == "mock"
    assert s.desc_mode == "labels"
    assert not s.ask_enabled
    assert s.missing_keys() == []


def test_llm_mode_bundles_switches(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_OPENROUTER_API_KEY", "test-key")
    s = get_settings()
    assert s.extraction_mode == "vlm"
    assert s.eligibility_mode == "mock"
    assert s.desc_mode == "labels"
    assert s.ask_enabled
    assert s.missing_keys() == []


def test_live_mode_bundles_switches(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IV_MODE", "live")
    monkeypatch.setenv("IV_VISION_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("STEDI_API_KEY", "test-key")
    s = get_settings()
    assert s.extraction_mode == "vlm"
    assert s.eligibility_mode == "stedi"
    assert s.desc_mode == "full"
    assert s.ask_enabled
    assert s.missing_keys() == []


def test_llm_mode_without_openrouter_key_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.delenv("IV_OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY"):
        get_settings()


def test_llm_mode_openai_models_require_openai_key(monkeypatch: pytest.MonkeyPatch):
    # "openai:"-prefixed models use OpenAI, so the llm tier needs its key.
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("IV_ASK_MODEL", "openai:gpt-4o-mini")
    monkeypatch.delenv("IV_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_settings()


def test_local_models_need_no_cloud_key(monkeypatch: pytest.MonkeyPatch):
    # A model name with no provider prefix runs on the local server: no key needed.
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "minicpm-v4.6:1b")
    monkeypatch.delenv("IV_OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    s = get_settings()
    assert s.missing_keys() == []


def test_live_mode_without_stedi_key_fails(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IV_MODE", "live")
    monkeypatch.setenv("IV_OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("STEDI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="STEDI_API_KEY"):
        get_settings()


def test_descriptions_are_demo_labels_in_mock():
    # A code with reference text shows only our hand-written label in the demo tier.
    assert describe("D0120", "CDT") == "Exam, established patient"


def test_reference_text_shows_in_live(monkeypatch: pytest.MonkeyPatch):
    # Live mode shows reference CDT text. The string itself is not committed, so
    # the test compares against the demo label — live must differ from it.
    monkeypatch.setenv("IV_MODE", "live")
    monkeypatch.setenv("IV_VISION_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("STEDI_API_KEY", "test-key")
    assert describe("D0120", "CDT") != "Exam, established patient"


def test_stc_descriptions_show_in_every_tier():
    # STC text is our own words, so it is tier-independent.
    monkey = describe("35", "STC")
    assert monkey == "Dental care"


def test_mock_mode_run_makes_zero_model_calls(monkeypatch: pytest.MonkeyPatch):
    """The mock demo runs end-to-end on a committed card: any OpenRouter, Stedi,
    or local server call must explode the test. Extraction comes from the sidecar
    answer key, the 271 is the deterministic mock."""

    def _boom(*args, **kwargs):
        raise AssertionError(f"model/network call in mock mode: {args[:1]}")

    monkeypatch.setattr("insurance_verify.extract.vlm.extract_vlm", _boom)
    monkeypatch.setattr("insurance_verify.eligibility.stedi.check_eligibility", _boom)
    monkeypatch.setattr("urllib.request.urlopen", _boom)

    summary = Pipeline().run(CARD)
    assert summary.eligibility_status == "active"
    assert summary.benefits


def test_llm_mode_runs_real_vlm_on_the_committed_png(monkeypatch: pytest.MonkeyPatch):
    """The llm tier runs real OCR on the committed PNG — the card's sidecar
    answer key must not be used as a shortcut."""
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_OPENROUTER_API_KEY", "test-key")
    calls = []

    def fake_openrouter(image_path, model, api_key):
        calls.append((str(image_path), model))
        return {
            "member_id": "812345678",
            "group_id": "5121024",
            "payer_id": "75216",
            "subscriber_first": "Ava",
            "subscriber_last": "Nguyen",
            "payer_name": "Delta Dental",
            "plan_name": "PPO Standard",
        }

    monkeypatch.setattr("insurance_verify.extract.vlm._call_openrouter", fake_openrouter)
    result = Pipeline()._extract(CARD)
    assert calls, "the llm tier must call the VLM, not the sidecar"
    assert result.tier == "vlm"
    assert result.card.member_id == "812345678"


def test_llm_mode_openai_backend_runs_real_ocr(monkeypatch: pytest.MonkeyPatch):
    # With an "openai:" vision model, the llm tier routes OCR to the OpenAI backend.
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("IV_ASK_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("IV_OPENAI_API_KEY", "test-key")
    calls = []

    def fake_openai(image_path, model, api_key):
        calls.append(model)
        return {
            "member_id": "812345678",
            "group_id": "5121024",
            "payer_id": "75216",
            "subscriber_first": "Ava",
            "subscriber_last": "Nguyen",
            "payer_name": "Delta Dental",
            "plan_name": "PPO Standard",
        }

    monkeypatch.setattr("insurance_verify.extract.vlm._call_openai", fake_openai)
    result = Pipeline()._extract(CARD)
    assert calls == ["gpt-4o-mini"], "the openai prefix must route to the OpenAI backend"
    assert result.tier == "vlm"
    assert result.card.member_id == "812345678"


def test_live_mode_calls_real_stedi(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IV_MODE", "live")
    monkeypatch.setenv("IV_VISION_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("STEDI_API_KEY", "test-key")
    calls = []

    def fake_stedi(request):
        calls.append(request.payer_id)
        return EligibilityResponse271(
            trace_number=request.trace_number,
            subscriber=request.subscriber,
            status="active",
            benefits=[],
            raw="{}",
            x12="",
        )

    def fake_openrouter(image_path, model, api_key):
        return {
            "member_id": "812345678",
            "group_id": "5121024",
            "payer_id": "75216",
            "subscriber_first": "Ava",
            "subscriber_last": "Nguyen",
            "payer_name": "Delta Dental",
            "plan_name": "PPO Standard",
        }

    monkeypatch.setattr("insurance_verify.eligibility.stedi.check_eligibility", fake_stedi)
    monkeypatch.setattr("insurance_verify.extract.vlm._call_openrouter", fake_openrouter)

    summary = Pipeline().run(CARD)
    assert calls, "the live tier must call Stedi, not the mock 271"
    assert summary.eligibility_status == "active"


def test_ask_refused_in_mock_mode():
    r = client.post(
        "/ask",
        json={"question": "Is a cleaning covered?", "raw_271": "{}"},
    )
    assert r.status_code == 403
    assert "mock" in r.json()["detail"]


def test_ask_routes_openai_prefix(monkeypatch: pytest.MonkeyPatch):
    # An "openai:" ask model streams from the OpenAI backend, prefix stripped.
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("IV_ASK_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("IV_OPENAI_API_KEY", "test-key")
    seen = []

    def fake_stream(messages, model, api_key):
        seen.append(model)
        yield "hello"

    monkeypatch.setattr("insurance_verify.ask._stream_openai", fake_stream)
    tokens = list(ask._stream([{"role": "user", "content": "hi"}]))
    assert seen == ["gpt-4o-mini"]
    assert tokens == ["hello"]


def test_ask_routes_local_prefix(monkeypatch: pytest.MonkeyPatch):
    # "local:<model>" runs on the local server with the prefix stripped.
    monkeypatch.setenv("IV_MODE", "llm")
    monkeypatch.setenv("IV_VISION_MODEL", "local:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_ASK_MODEL", "local:minicpm-v4.6:1b")
    seen = []

    def fake_local(messages, model, url):
        seen.append((model, url))
        yield "ok"

    monkeypatch.setattr(ask, "_stream_local", fake_local)
    tokens = list(ask._stream([{"role": "user", "content": "hi"}]))
    assert seen == [("minicpm-v4.6:1b", "http://localhost:11434/v1")]
    assert tokens == ["ok"]


def test_config_endpoint_reports_the_tier(monkeypatch: pytest.MonkeyPatch):
    # Key flags are gone; the endpoint names the active model + provider per role.
    for name in (
        "IV_OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY",
        "IV_OPENAI_API_KEY",
        "OPENAI_API_KEY",
        "STEDI_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)
    cfg = client.get("/config").json()
    assert cfg["mode"] == "mock"
    assert cfg["ask_enabled"] is False
    assert cfg["vision_model"] == "openai:gpt-6-luna"
    assert cfg["vision_provider"] == "OpenAI"
    assert cfg["ask_provider"] == "OpenAI"
    assert cfg["stedi_key_set"] is False

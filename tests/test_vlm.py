"""Tests for the VLM OCR extraction path (extract/vlm.py).

The OpenRouter, OpenAI, and local HTTP calls are mocked so tests stay hermetic;
we verify parsing and the deterministic confidence computation. Each test sets
IV_VISION_MODEL explicitly so the mock matches the backend it exercises.
"""

from __future__ import annotations

from pathlib import Path

from insurance_verify.extract import vlm


def _mock_call(monkeypatch, data: dict):
    monkeypatch.setenv("IV_VISION_MODEL", "openrouter:minicpm-v4.6:1b")
    monkeypatch.setenv("IV_OPENROUTER_API_KEY", "test-key")
    monkeypatch.setattr(vlm, "_call_openrouter", lambda *a, **k: data)


def test_extract_vlm_parses_fields(monkeypatch, tmp_path: Path):
    _mock_call(
        monkeypatch,
        {
            "member_id": "123456789",
            "group_id": "5121024",
            "payer_id": "AMTAS00425",
            "subscriber_first": "Jane",
            "subscriber_last": "Doe",
            "payer_name": "Ameritas",
            "plan_name": "DENTAL PLAN PLUS",
        },
    )
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")

    result = vlm.extract_vlm(png)
    assert result.tier == "vlm"
    assert result.card.member_id == "123456789"
    assert result.card.payer_id == "AMTAS00425"
    assert result.card.subscriber_first == "Jane"
    assert result.card.plan_name == "DENTAL PLAN PLUS"


def test_extract_vlm_accepts_plan_key(monkeypatch, tmp_path: Path):
    # The model sometimes returns "plan" instead of "plan_name".
    _mock_call(
        monkeypatch,
        {
            "member_id": "123456789",
            "payer_id": "AMTAS00425",
            "subscriber_first": "Jane",
            "subscriber_last": "Doe",
            "plan": "DENTAL PLAN PLUS",
        },
    )
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")

    result = vlm.extract_vlm(png)
    assert result.card.plan_name == "DENTAL PLAN PLUS"


def test_extract_vlm_routes_openai_prefix(monkeypatch, tmp_path: Path):
    # A vision model prefixed with "openai:" goes to the OpenAI backend,
    # with the prefix stripped from the model name.
    monkeypatch.setenv("IV_VISION_MODEL", "openai:gpt-4o-mini")
    monkeypatch.setenv("IV_OPENAI_API_KEY", "test-key")
    calls = []

    def fake_openai(image_path, model, api_key):
        calls.append((model, api_key))
        return {
            "member_id": "123456789",
            "payer_id": "AMTAS00425",
            "subscriber_first": "Jane",
            "subscriber_last": "Doe",
            "payer_name": "Ameritas",
            "plan_name": "DENTAL PLAN PLUS",
        }

    monkeypatch.setattr(vlm, "_call_openai", fake_openai)
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")

    result = vlm.extract_vlm(png)
    assert calls == [("gpt-4o-mini", "test-key")]
    assert result.card.member_id == "123456789"
    assert result.card.plan_name == "DENTAL PLAN PLUS"


def test_extract_vlm_routes_local_model(monkeypatch, tmp_path: Path):
    # A bare model name goes to the local model server.
    monkeypatch.setenv("IV_VISION_MODEL", "minicpm-v4.6:1b")
    calls = []

    def fake_local(image_path, model, url):
        calls.append((model, url))
        return {
            "member_id": "123456789",
            "payer_id": "AMTAS00425",
            "subscriber_first": "Jane",
            "subscriber_last": "Doe",
            "payer_name": "Ameritas",
            "plan_name": "DENTAL PLAN PLUS",
        }

    monkeypatch.setattr(vlm, "_call_local", fake_local)
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")

    result = vlm.extract_vlm(png)
    # The default URL is the OpenAI-compatible endpoint root.
    assert calls == [("minicpm-v4.6:1b", "http://localhost:11434/v1")]
    assert result.card.member_id == "123456789"


def test_extract_vlm_strips_the_local_prefix(monkeypatch, tmp_path: Path):
    # "local:<model>" is the same route as a bare name, prefix stripped.
    monkeypatch.setenv("IV_VISION_MODEL", "local:minicpm-v4.6:1b")
    calls = []

    def fake_local(image_path, model, url):
        calls.append((model, url))
        return {
            "member_id": "123456789",
            "payer_id": "AMTAS00425",
            "subscriber_first": "Jane",
            "subscriber_last": "Doe",
            "payer_name": "Ameritas",
            "plan_name": "DENTAL PLAN PLUS",
        }

    monkeypatch.setattr(vlm, "_call_local", fake_local)
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")

    result = vlm.extract_vlm(png)
    assert calls == [("minicpm-v4.6:1b", "http://localhost:11434/v1")]
    assert result.card.member_id == "123456789"


def test_extract_vlm_confidence_matches_payer_format(monkeypatch, tmp_path: Path):
    # AMTAS00425 member format is \d{9}; a 9-digit member id validates -> high confidence.
    _mock_call(
        monkeypatch,
        {
            "member_id": "123456789",
            "payer_id": "AMTAS00425",
            "subscriber_first": "Jane",
            "subscriber_last": "Doe",
        },
    )
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")

    result = vlm.extract_vlm(png)
    assert result.confidences["member_id"] == 0.95
    assert result.confidences["payer_id"] == 0.95
    assert result.overall_confidence > 0.7


def test_extract_vlm_low_confidence_on_format_mismatch(monkeypatch, tmp_path: Path):
    # A member id that doesn't match the payer's format drops confidence.
    _mock_call(
        monkeypatch,
        {
            "member_id": "NOT-A-MATCH",
            "payer_id": "AMTAS00425",
            "subscriber_first": "Jane",
            "subscriber_last": "Doe",
        },
    )
    png = tmp_path / "card.png"
    png.write_bytes(b"fake-png-bytes")

    result = vlm.extract_vlm(png)
    assert result.confidences["member_id"] == 0.5

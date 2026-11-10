"""Test-wide fixtures.

The mock tier is the hermetic one: stubbed extraction, deterministic 271, ask
chat off — no keys, no model, no network. Tests that opt into a tier set
``IV_MODE`` themselves.

config.py loads the developer's .env at import, so tests clear every variable
.env can set: hermetic-ness does not depend on the machine.
"""

from __future__ import annotations

import pytest

# Every env var .env introduces (see .env.example). Cleared per test.
_ENV_VARS = (
    "IV_MODE",
    "IV_VISION_MODEL",
    "IV_ASK_MODEL",
    "IV_LOCAL_URL",
    "IV_OPENROUTER_API_KEY",
    "OPENROUTER_API_KEY",
    "IV_OPENAI_API_KEY",
    "OPENAI_API_KEY",
    "STEDI_API_KEY",
    "IV_DATA_DIR",
    "IV_CONFIDENCE_THRESHOLD",
)


@pytest.fixture(autouse=True)
def hermetic_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("IV_MODE", "mock")

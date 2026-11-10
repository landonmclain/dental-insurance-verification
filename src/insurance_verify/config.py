"""Configuration loaded from environment variables. Secrets never live in code."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env at import; real environment variables win over .env.
load_dotenv()

MODES = ("mock", "llm", "live")

# Model providers are chosen by the model name's prefix: "openrouter:x" uses
# OpenRouter, "openai:x" uses OpenAI, "local:x" (or a bare name) uses the local
# OpenAI-compatible server.
_PROVIDER_KEY = {"openrouter": "OPENROUTER_API_KEY", "openai": "OPENAI_API_KEY"}
# Display name for each prefix; a bare name is "local".
_PROVIDER_LABEL = {"openrouter": "OpenRouter", "openai": "OpenAI", "local": "Local"}
_KEY_FIELDS = {
    "OPENROUTER_API_KEY": "openrouter_api_key",
    "OPENAI_API_KEY": "openai_api_key",
    "STEDI_API_KEY": "stedi_api_key",
}


@dataclass(frozen=True)
class Settings:
    """Runtime settings. One mode flag bundles every backend switch."""

    mode: str = field(default_factory=lambda: os.getenv("IV_MODE", "mock"))
    # OpenRouter API key — OCR and the Q&A chat in llm/live.
    openrouter_api_key: str = field(
        default_factory=lambda: (
            os.getenv("IV_OPENROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY", "")
        )
    )
    # OpenAI API key — same tier rules, selected by an "openai:" model prefix.
    openai_api_key: str = field(
        default_factory=lambda: (
            os.getenv("IV_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY", "")
        )
    )
    vision_model: str = field(
        default_factory=lambda: os.getenv("IV_VISION_MODEL", "openai:gpt-6-luna")
    )
    # Text model for the Q&A chat; same prefix rule as vision.
    ask_model: str = field(
        default_factory=lambda: os.getenv("IV_ASK_MODEL", "openai:gpt-6-luna")
    )
    # Stedi eligibility API key (sandbox)
    stedi_api_key: str = field(default_factory=lambda: os.getenv("STEDI_API_KEY", ""))
    # Local OpenAI-compatible model server (Ollama, llama.cpp, Strata, LM Studio…)
    local_url: str = field(
        default_factory=lambda: os.getenv(
            "IV_LOCAL_URL", "http://localhost:11434/v1"
        )
    )
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("IV_DATA_DIR", "synth/output")))
    # Confidence below which a card is flagged for human review
    confidence_threshold: float = field(
        default_factory=lambda: float(os.getenv("IV_CONFIDENCE_THRESHOLD", "0.7"))
    )

    @property
    def extraction_mode(self) -> str:
        """mock: read the card's sidecar answer key (no model). llm/live: real VLM OCR."""
        return "vlm" if self.mode in ("llm", "live") else "stub"

    @property
    def eligibility_mode(self) -> str:
        """live: real Stedi 270/271. mock/llm: deterministic mock."""
        return "stedi" if self.mode == "live" else "mock"

    @property
    def desc_mode(self) -> str:
        """live: reference CDT text when the local data files are present; mock/llm:
        demo labels (gitignored, so a published clone has none)."""
        return "full" if self.mode == "live" else "labels"

    @property
    def ask_enabled(self) -> bool:
        """The Q&A chat needs a text model, so it is disabled in mock mode."""
        return self.mode in ("llm", "live")

    def missing_keys(self) -> list[str]:
        """Env var names the selected tier needs that are not set."""
        needed: list[str] = []
        if self.mode in ("llm", "live"):
            provider = _PROVIDER_KEY.get(self.vision_model.split(":", 1)[0])
            if provider:
                needed.append(provider)
        if self.ask_enabled:
            provider = _PROVIDER_KEY.get(self.ask_model.split(":", 1)[0])
            if provider:
                needed.append(provider)
        if self.mode == "live":
            needed.append("STEDI_API_KEY")
        return [
            name
            for name in dict.fromkeys(needed)
            if not getattr(self, _KEY_FIELDS[name])
        ]


def provider_of(model: str) -> str:
    """The provider a model name routes to, by its prefix."""
    return _PROVIDER_LABEL.get(model.split(":", 1)[0], "Local")


def get_settings() -> Settings:
    settings = Settings()
    if settings.mode not in MODES:
        raise RuntimeError(f"IV_MODE={settings.mode!r} is not one of {MODES}")
    missing = settings.missing_keys()
    if missing:
        raise RuntimeError(
            f"IV_MODE={settings.mode} requires {' + '.join(missing)}; "
            "use IV_MODE=mock to run with no keys"
        )
    return settings

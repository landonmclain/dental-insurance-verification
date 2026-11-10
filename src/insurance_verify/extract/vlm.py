"""Real OCR extraction via a vision-language model.

The backend is chosen by the IV_VISION_MODEL prefix: "openrouter:x" goes to
OpenRouter, "openai:x" goes to OpenAI, "local:x" (or a bare model name) goes to
the local server at IV_LOCAL_URL.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.request
from pathlib import Path

from insurance_verify.config import get_settings
from insurance_verify.schemas.card import CardFields, ExtractionResult
from synth.payers import get_payer

_PROMPT = """You are reading a dental insurance card image. Extract the following
fields and return ONLY a JSON object (no markdown, no prose) with these keys:
- member_id: the member/subscriber ID printed on the card (alphanumeric, e.g. "007007007")
- group_id: the group number printed on the card, or null if absent
- payer_id: the payer ID / routing code printed on the card (e.g. "AMTAS00425")
- subscriber_first: the member's first name as printed on the card
- subscriber_last: the member's last name as printed on the card
- payer_name: the insurance company / payer name as printed on the card (e.g. "Ameritas")
- plan_name: the plan or product name as printed on the card (e.g. "DENTAL PLAN PLUS")
Return valid JSON only."""


def _call_local(image_path: str | Path, model: str, url: str) -> dict:
    """Send the image to the local OpenAI-compatible server and return parsed JSON."""
    return _call_openai_completions(
        url.rstrip("/") + "/chat/completions", image_path, model, ""
    )


def _mime(path: Path) -> str:
    """Best-effort MIME type for the card image, defaulting to PNG."""
    return {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }.get(path.suffix.lower().lstrip("."), "image/png")


def _call_openai_completions(
    endpoint: str, image_path: str | Path, model: str, api_key: str
) -> dict:
    """Send the image to an OpenAI-compatible chat endpoint and return parsed JSON."""
    path = Path(image_path)
    img = base64.b64encode(path.read_bytes()).decode()
    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{_mime(path)};base64,{img}"},
                    },
                ],
            }
        ],
        "temperature": 0,
    }
    req = urllib.request.Request(
        endpoint,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = json.loads(resp.read())
    content = body["choices"][0]["message"]["content"]
    # Strip markdown code fences if the model wraps the JSON.
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    return json.loads(content)


def _call_openrouter(image_path: str | Path, model: str, api_key: str) -> dict:
    """Send the image to OpenRouter and return the parsed JSON response."""
    return _call_openai_completions(
        "https://openrouter.ai/api/v1/chat/completions", image_path, model, api_key
    )


def _call_openai(image_path: str | Path, model: str, api_key: str) -> dict:
    """Send the image to OpenAI and return the parsed JSON response."""
    return _call_openai_completions(
        "https://api.openai.com/v1/chat/completions", image_path, model, api_key
    )


def _confidences(card: CardFields) -> dict[str, float]:
    """Confidence from validating extracted IDs against the payer's known format,
    not the model's self-report.
    """
    payer = get_payer(card.payer_id) if card.payer_id else None
    conf: dict[str, float] = {}
    if payer and card.member_id:
        conf["member_id"] = 0.95 if re.fullmatch(payer.member_format, card.member_id) else 0.5
    else:
        conf["member_id"] = 0.5 if card.member_id else 0.0
    conf["payer_id"] = 0.95 if payer else 0.5
    conf["subscriber_first"] = 0.9 if card.subscriber_first else 0.0
    conf["subscriber_last"] = 0.9 if card.subscriber_last else 0.0
    return conf


def extract_vlm(image_path: str | Path) -> ExtractionResult:
    """Run real OCR on a card image and return an ExtractionResult."""
    settings = get_settings()
    model = settings.vision_model
    if model.startswith("openrouter:"):
        data = _call_openrouter(
            image_path, model.removeprefix("openrouter:"), settings.openrouter_api_key
        )
    elif model.startswith("openai:"):
        data = _call_openai(
            image_path, model.removeprefix("openai:"), settings.openai_api_key
        )
    else:
        data = _call_local(image_path, model.removeprefix("local:"), settings.local_url)
    card = CardFields(
        member_id=str(data.get("member_id", "") or ""),
        # The model sometimes returns "group" instead of "group_id".
        group_id=data.get("group_id") or data.get("group"),
        payer_id=data.get("payer_id"),
        subscriber_first=data.get("subscriber_first"),
        subscriber_last=data.get("subscriber_last"),
        payer_name=data.get("payer_name"),
        # The model sometimes returns "plan" instead of "plan_name".
        plan_name=data.get("plan_name") or data.get("plan"),
    )
    confidences = _confidences(card)
    overall = sum(confidences.values()) / len(confidences)
    return ExtractionResult(
        card=card,
        confidences=confidences,
        overall_confidence=overall,
        tier="vlm",
        needs_review=overall < settings.confidence_threshold,
        raw_text=json.dumps(data),
    )

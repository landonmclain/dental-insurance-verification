"""Grounded benefit Q&A: answer questions only from a run's parsed 271.

The LLM presents the deterministic ``BenefitCatalog`` — it never decides
coverage. Answers stream token-by-token over SSE.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Literal

from pydantic import BaseModel, Field

from insurance_verify.benefits import BenefitCatalog, parse_271
from insurance_verify.config import get_settings
from insurance_verify.summarize.basic import _figure, _money, _pct

_SYSTEM_PROMPT = """You are a dental benefits assistant for a front-desk team. Answer questions
about a patient's dental benefits using ONLY the benefit data provided below.

Rules:
- Answer only from the provided data. Never invent coverage, amounts, or limits.
- If the answer is not in the data, say "I don't have that information" and
  suggest what to confirm with the payer.
- Cite the relevant procedure codes (e.g. D2740) when you can.
- Be concise and plain-English.

BENEFIT DATA:
{context}"""


class AskMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str
    history: list[AskMessage] = Field(default_factory=list)
    raw_271: str
    payer_name: str | None = None
    # Fields read off the card image (payer, plan, group, member, subscriber).
    card: dict | None = None


def _eligibility_status(body: dict) -> str:
    """Derive the plan-level eligibility status from the 271 statuses."""
    for plan in body.get("plans") or []:
        for st in (plan.get("benefits") or {}).get("statuses") or []:
            if st.get("status") == "ACTIVE_COVERAGE":
                return "active"
    return "unknown"


def _payer_block(body: dict) -> str:
    """Payer identification and first contact (phone/email) from the 271."""
    payer = body.get("payer") or {}
    lines: list[str] = []
    pid = payer.get("identification")
    if pid:
        lines.append(f"PAYER ID: {pid}")
    contacts = payer.get("contacts") or []
    if contacts:
        c = contacts[0]
        bits: list[str] = []
        if c.get("name"):
            bits.append(str(c["name"]))
        if c.get("phoneNumbers"):
            bits.append("phone " + ", ".join(str(p) for p in c["phoneNumbers"]))
        if c.get("emails"):
            bits.append("email " + ", ".join(str(e) for e in c["emails"]))
        if bits:
            lines.append("PAYER CONTACT: " + "; ".join(bits))
    return "\n".join(lines)


def _subscriber_block(body: dict) -> str:
    """Subscriber identity echoed in the 271 (name, member, DOB, address, plan)."""
    sub = body.get("subscriber") or {}
    bits: list[str] = []
    name = (sub.get("name") or {}).get("person") or {}
    full = " ".join(x for x in [name.get("firstName"), name.get("lastName")] if x)
    if full:
        bits.append(full)
    if sub.get("memberId"):
        bits.append(f"member {sub['memberId']}")
    if sub.get("dateOfBirth"):
        bits.append(f"DOB {sub['dateOfBirth']}")
    if sub.get("gender"):
        bits.append(f"gender {sub['gender']}")
    addr = sub.get("address") or {}
    addr_parts = [
        addr.get("addressLine1"),
        addr.get("city"),
        addr.get("state"),
        addr.get("postalCode"),
    ]
    addr_str = ", ".join(x for x in addr_parts if x)
    if addr_str:
        bits.append(addr_str)
    plan_dates = (sub.get("dates") or {}).get("plan") or {}
    if plan_dates.get("start") and plan_dates.get("end"):
        bits.append(f"plan {plan_dates['start']} to {plan_dates['end']}")
    return "SUBSCRIBER: " + "; ".join(bits) if bits else ""


def _provider_block(body: dict) -> str:
    """Provider (practice) info from the 271."""
    prov = body.get("provider") or {}
    bits: list[str] = []
    if prov.get("npi"):
        bits.append(f"NPI {prov['npi']}")
    if prov.get("type"):
        bits.append(f"type {prov['type']}")
    name = (prov.get("name") or {}).get("person") or {}
    full = " ".join(x for x in [name.get("firstName"), name.get("lastName")] if x)
    if full:
        bits.append(f"name {full}")
    return "PROVIDER: " + "; ".join(bits) if bits else ""


def _card_block(card: dict | None) -> str:
    """What's printed on the insurance card (from OCR extraction)."""
    if not card:
        return ""
    bits: list[str] = []
    if card.get("payer_name"):
        bits.append(f"payer {card['payer_name']}")
    if card.get("plan_name"):
        bits.append(f"plan {card['plan_name']}")
    if card.get("group_id"):
        bits.append(f"group {card['group_id']}")
    if card.get("member_id"):
        bits.append(f"member {card['member_id']}")
    first, last = card.get("subscriber_first"), card.get("subscriber_last")
    if first or last:
        bits.append("subscriber " + " ".join(x for x in [first, last] if x))
    return "CARD: " + "; ".join(bits) if bits else ""


def build_context(
    catalog: BenefitCatalog,
    raw_271: str | None = None,
    payer_name: str | None = None,
    card: dict | None = None,
) -> str:
    """A compact, grounded text block for the LLM: benefit data plus the card
    fields and the subscriber/payer/provider context from the 271.
    """
    parts: list[str] = []
    parts.append(f"PAYER: {payer_name or 'Unknown'}")
    if raw_271:
        try:
            body = json.loads(raw_271)
        except (json.JSONDecodeError, ValueError):
            body = {}
        parts.append(f"ELIGIBILITY STATUS: {_eligibility_status(body)}")
        payer_block = _payer_block(body)
        if payer_block:
            parts.append(payer_block)
        sub_block = _subscriber_block(body)
        if sub_block:
            parts.append(sub_block)
        prov_block = _provider_block(body)
        if prov_block:
            parts.append(prov_block)
    card_block = _card_block(card)
    if card_block:
        parts.append(card_block)
    parts.append(f"PLAN: {catalog.plan_name or 'Unknown'}")

    deductible = _figure(catalog.figures.deductible)
    oop = _figure(catalog.figures.out_of_pocket)
    if deductible:
        parts.append(f"DEDUCTIBLE: {deductible}")
    if oop:
        parts.append(f"OUT-OF-POCKET MAX: {oop}")

    parts.append("")
    parts.append("COVERAGE:")
    for line in catalog.lines:
        if line.non_covered:
            status = "not covered"
        elif line.status == "ACTIVE_COVERAGE" or line.coinsurance or line.copay:
            status = "covered"
        else:
            status = "unknown"
        desc = line.description or line.category or "service"
        bits = [f"{line.code} {desc} — {status}"]
        if line.coinsurance:
            bits.append(f"coinsurance {_pct(line.coinsurance)}")
        if line.copay:
            bits.append(f"copay {_money(line.copay)}")
        if line.deductible:
            bits.append(f"deductible {_money(line.deductible)}")
        if line.limitations:
            lims = ", ".join(
                lim.text + (f" ({', '.join(lim.codes)})" if lim.codes else "")
                for lim in line.limitations
            )
            bits.append(f"limits: {lims}")
        parts.append("  " + "; ".join(bits))

    return "\n".join(parts)


def build_messages(question: str, history: list[AskMessage], context: str) -> list[dict]:
    """Build the chat messages: system prompt + in-run history + the question."""
    messages: list[dict] = [{"role": "system", "content": _SYSTEM_PROMPT.format(context=context)}]
    for h in history:
        messages.append({"role": h.role, "content": h.content})
    messages.append({"role": "user", "content": question})
    return messages


def _stream_local(messages: list[dict], model: str, url: str):
    """Stream tokens from the local OpenAI-compatible model server."""
    yield from _stream_openai_completions(
        url.rstrip("/") + "/chat/completions", messages, model, ""
    )


def _stream_openai_completions(
    endpoint: str, messages: list[dict], model: str, api_key: str
):
    """Stream tokens from an OpenAI-compatible chat completions endpoint."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
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
        for line in resp:
            line = line.decode().strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            chunk = json.loads(data)
            delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
            if delta:
                yield delta


def _stream_openrouter(messages: list[dict], model: str, api_key: str):
    """Stream tokens from an OpenRouter chat completion."""
    yield from _stream_openai_completions(
        "https://openrouter.ai/api/v1/chat/completions", messages, model, api_key
    )


def _stream_openai(messages: list[dict], model: str, api_key: str):
    """Stream tokens from an OpenAI chat completion."""
    yield from _stream_openai_completions(
        "https://api.openai.com/v1/chat/completions", messages, model, api_key
    )


def _stream(messages: list[dict]):
    """Pick the backend by IV_ASK_MODEL prefix and stream tokens."""
    settings = get_settings()
    model = settings.ask_model
    if model.startswith("openrouter:"):
        yield from _stream_openrouter(
            messages, model.removeprefix("openrouter:"), settings.openrouter_api_key
        )
    elif model.startswith("openai:"):
        yield from _stream_openai(
            messages, model.removeprefix("openai:"), settings.openai_api_key
        )
    elif model.startswith("local:"):
        yield from _stream_local(
            messages, model.removeprefix("local:"), settings.local_url
        )
    else:
        yield from _stream_local(messages, model, settings.local_url)


def stream_answer(req: AskRequest):
    """Async generator of SSE events for one grounded answer.

    Yields ``{"type": "token", "content": ...}`` frames as the model streams,
    then a ``{"type": "done"}`` frame, or ``{"type": "error", ...}`` on failure.
    """
    try:
        catalog = parse_271(req.raw_271)
    except (json.JSONDecodeError, ValueError) as exc:
        yield {"type": "error", "message": f"Could not parse benefits: {exc}"}
        return

    context = build_context(catalog, req.raw_271, req.payer_name, req.card)
    messages = build_messages(req.question, req.history, context)
    try:
        for token in _stream(messages):
            yield {"type": "token", "content": token}
        yield {"type": "done"}
    except Exception as exc:  # noqa: BLE001 - surface any failure to the client
        yield {"type": "error", "message": str(exc)}

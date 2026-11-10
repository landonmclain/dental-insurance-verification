"""FastAPI backend: verify endpoint + SSE event stream.

The frontend POSTs a card id, gets a job id, then subscribes to the SSE stream
to watch the pipeline run in real time. The pipeline runs on the committed
sample card image; there is no upload.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from insurance_verify.ask import AskRequest, stream_answer
from insurance_verify.config import get_settings, provider_of
from insurance_verify.events import broker, sse_format

app = FastAPI(title="Insurance Verify", version="0.1.0")

CARDS_DIR = Path("data/cards")


class VerifyRequest(BaseModel):
    card_id: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/config")
def config() -> dict:
    """Runtime mode, active vision/ask models and providers, and Stedi key status."""
    settings = get_settings()
    return {
        "mode": settings.mode,
        "ask_enabled": settings.ask_enabled,
        "vision_model": settings.vision_model,
        "vision_provider": provider_of(settings.vision_model),
        "ask_model": settings.ask_model,
        "ask_provider": provider_of(settings.ask_model),
        "stedi_key_set": bool(settings.stedi_api_key),
    }


@app.get("/cards")
def list_cards() -> list[dict]:
    """List the generated sample cards for the demo card picker."""
    cards: list[dict] = []
    for png in sorted(CARDS_DIR.glob("card_*.png")):
        card_id = png.stem
        payer = None
        sidecar = png.with_suffix(".json")
        if sidecar.exists():
            try:
                payer = json.loads(sidecar.read_text()).get("payer_name")
            except Exception:
                payer = None
        cards.append({"id": card_id, "payer": payer, "image_url": f"/cards/{card_id}/image"})
    return cards


@app.get("/cards/{card_id}/image")
def card_image(card_id: str) -> FileResponse:
    """Serve one generated sample card image."""
    png = CARDS_DIR / f"{card_id}.png"
    if not png.exists():
        raise HTTPException(status_code=404, detail="Card not found")
    return FileResponse(png, media_type="image/png")


@app.post("/verify")
async def verify(req: VerifyRequest) -> dict:
    """Run the pipeline on a committed sample card, return a job id to subscribe to."""
    png = CARDS_DIR / f"{req.card_id}.png"
    if not req.card_id.startswith("card_") or not png.exists():
        raise HTTPException(status_code=404, detail="Card not found")

    job_id = broker.create_job(str(png))
    return {"job_id": job_id}


@app.post("/ask")
async def ask(req: AskRequest) -> StreamingResponse:
    """Grounded benefit Q&A: stream an answer from the run's parsed 271.

    The request carries the raw 271 and in-run history, so the endpoint is
    stateless. Mock mode refuses (403) — the chat needs a text model.
    """
    if not get_settings().ask_enabled:
        raise HTTPException(
            status_code=403,
            detail="Q&A chat is not available in mock mode",
        )

    async def gen():
        q: asyncio.Queue = asyncio.Queue()

        def run() -> None:
            try:
                for event in stream_answer(req):
                    q.put_nowait(event)
            except Exception as exc:  # noqa: BLE001 - surface any failure
                q.put_nowait({"type": "error", "message": str(exc)})

        task = asyncio.create_task(asyncio.to_thread(run))
        while True:
            event = await q.get()
            yield sse_format(event)
            if event.get("type") in ("done", "error"):
                break
        await task

    return StreamingResponse(gen(), media_type="text/event-stream")


@app.get("/events/{job_id}")
async def events(job_id: str) -> StreamingResponse:
    """SSE stream of pipeline events for a job."""
    q = broker.subscribe(job_id)
    if q is None:
        raise HTTPException(status_code=404, detail="Unknown job")

    # Start the pipeline only once the client is subscribed.
    broker.start(job_id)

    async def gen():
        while True:
            try:
                event = await asyncio.to_thread(q.get, True, 30)
            except Exception:
                break
            yield sse_format(event)
            if event.get("step") == "end":
                broker.close(job_id)
                break

    return StreamingResponse(gen(), media_type="text/event-stream")

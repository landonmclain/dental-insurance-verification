"""Capture the raw 271 response for each generated card into data/captures/.

Submits each committed card id to the running backend, reads the SSE event
stream, and saves
the raw 271 (from the result event's summary.raw_response) to
data/captures/271_<payer>.json. These are full payer response bodies kept
local-only (gitignored); the small hand-authored fixtures in tests/fixtures/
are the publishable data the parser and summarizer are tested against.
"""

from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

BASE = "http://localhost:8000"
CARDS_DIR = Path("data/cards")
CAPTURES_DIR = Path("data/captures")


def post_verify(card_path: Path) -> str:
    """Submit a committed card id, return the job id."""
    payload = json.dumps({"card_id": card_path.stem}).encode()
    req = urllib.request.Request(
        f"{BASE}/verify",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())["job_id"]


def read_result(job_id: str) -> dict:
    """Read the SSE stream until the result event, return its summary dict."""
    req = urllib.request.Request(f"{BASE}/events/{job_id}")
    with urllib.request.urlopen(req, timeout=60) as resp:
        buffer = ""
        while True:
            chunk = resp.read(4096).decode()
            if not chunk:
                break
            buffer += chunk
            while "\n\n" in buffer:
                frame, buffer = buffer.split("\n\n", 1)
                line = frame.strip()
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event["step"] == "result":
                    return json.loads(event["detail"])
                if event["step"] == "error":
                    raise RuntimeError(f"pipeline error: {event['detail']}")
    raise RuntimeError("stream ended without a result")


def main() -> None:
    CAPTURES_DIR.mkdir(parents=True, exist_ok=True)
    saved = []
    for png in sorted(CARDS_DIR.glob("card_*.png")):
        sidecar = png.with_suffix(".json")
        payer = json.loads(sidecar.read_text()).get("payer_name", png.stem)
        slug = payer.lower().replace(" ", "_").replace("/", "_")
        print(f"[{png.stem}] {payer} ...", flush=True)
        job_id = post_verify(png)
        summary = read_result(job_id)
        raw = summary.get("raw_response", "")
        if not raw:
            print(f"  !! no raw_response for {payer}; summary keys: {list(summary)}")
            continue
        dest = CAPTURES_DIR / f"271_{slug}.json"
        dest.write_text(raw)
        saved.append((str(dest), payer))
        print(f"  saved {dest} ({len(raw)} bytes)", flush=True)
    print(f"\nSaved {len(saved)} captures to {CAPTURES_DIR}")


if __name__ == "__main__":
    sys.exit(main())

"""Render a synthetic card to a PNG using Pillow.

Draws a simple credit-card-style layout with the payer's colors, the member's
name, member/group IDs, payer ID, and plan name. Output is a PNG plus a
ground-truth JSON sidecar.
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from synth.generator import SyntheticCard

CARD_W, CARD_H = 640, 400
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_BOLD_PATH if bold else FONT_PATH
    try:
        return ImageFont.truetype(path, size)
    except OSError:
        return ImageFont.load_default()


def _text(draw: ImageDraw.ImageDraw, xy, text, size, fill, bold=False, anchor="la"):
    draw.text(xy, text, font=_font(size, bold), fill=fill, anchor=anchor)


def render_card(card: SyntheticCard, out_dir: Path, index: int) -> Path:
    """Render one card to PNG and write its ground-truth JSON. Returns the PNG path."""
    out_dir.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGB", (CARD_W, CARD_H), card.payer.primary)
    draw = ImageDraw.Draw(img)

    draw.rectangle([0, 0, CARD_W, 90], fill=card.payer.secondary)
    _text(draw, (30, 20), card.payer.name.upper(), 30, "white", bold=True)
    label = "MEDICAL INSURANCE" if card.payer.kind == "medical" else "DENTAL INSURANCE"
    _text(draw, (30, 58), label, 16, (220, 220, 220))

    f = card.fields
    name = f"{f.subscriber_first} {f.subscriber_last}".strip()
    _text(draw, (30, 120), "MEMBER", 13, (200, 200, 200))
    _text(draw, (30, 140), name, 26, "white", bold=True)

    _text(draw, (30, 190), "MEMBER ID", 13, (200, 200, 200))
    _text(draw, (30, 210), f.member_id, 24, "white", bold=True)

    if f.group_id:
        _text(draw, (340, 190), "GROUP", 13, (200, 200, 200))
        _text(draw, (340, 210), f.group_id, 24, "white", bold=True)

    _text(draw, (30, 260), "PAYER ID", 13, (200, 200, 200))
    _text(draw, (30, 280), f.payer_id or "", 20, "white", bold=True)
    if f.plan_name:
        _text(draw, (340, 260), "PLAN", 13, (200, 200, 200))
        _text(draw, (340, 280), f.plan_name, 18, "white")

    png_path = out_dir / f"card_{index:04d}.png"
    img.save(png_path)

    card.image_path = str(png_path)
    gt_path = out_dir / f"card_{index:04d}.json"
    gt_path.write_text(json.dumps(card.to_ground_truth_json(), indent=2))

    return png_path


def render_batch(cards: list[SyntheticCard], out_dir: Path) -> list[Path]:
    paths = []
    for i, card in enumerate(cards):
        paths.append(render_card(card, out_dir, i))
    return paths

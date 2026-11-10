"""Tests for the synthetic card generator and renderer."""

from __future__ import annotations

import json
import re
from pathlib import Path

from PIL import Image

from synth.generator import _gen_id, generate_batch, generate_card
from synth.payers import PAYERS, get_payer
from synth.render import CARD_H, CARD_W, render_batch, render_card

# --- _gen_id ---


def test_gen_id_digits():
    assert re.fullmatch(r"\d{9}", _gen_id(r"\d{9}"))


def test_gen_id_letters_then_digits():
    assert re.fullmatch(r"[A-Z]{3}\d{6}", _gen_id(r"[A-Z]{3}\d{6}"))


def test_gen_id_letters_exclude_ambiguous():
    # The generator uses a reduced alphabet without I/O.
    value = _gen_id(r"[A-Z]{5}")
    assert "I" not in value and "O" not in value


def test_gen_id_plain_text_passthrough():
    assert _gen_id("ABC") == "ABC"


# --- generate_card ---


def test_generate_card_fields_match_payer_format():
    for payer in PAYERS:
        card = generate_card(payer=payer, seed=1)
        if payer.stedi_member_id:
            # Payer has a valid Stedi test subscriber: member ID is fixed.
            assert card.fields.member_id == payer.stedi_member_id
        else:
            assert re.fullmatch(payer.member_format, card.fields.member_id)
        assert re.fullmatch(payer.group_format, card.fields.group_id)
        assert card.fields.payer_id == payer.payer_id
        assert card.fields.payer_name == payer.name


def test_generate_card_has_names_and_dob():
    card = generate_card(seed=2)
    assert card.fields.subscriber_first
    assert card.fields.subscriber_last
    assert card.fields.subscriber_dob is not None
    assert card.fields.relationship == "self"


def test_generate_card_ground_truth_matches_fields():
    card = generate_card(seed=3)
    gt = card.ground_truth
    assert gt["member_id"] == card.fields.member_id
    assert gt["group_id"] == card.fields.group_id
    assert gt["payer_id"] == card.fields.payer_id
    assert gt["subscriber_first"] == card.fields.subscriber_first
    assert gt["subscriber_last"] == card.fields.subscriber_last
    assert gt["subscriber_dob"] == card.fields.subscriber_dob.isoformat()


def test_generate_card_deterministic_under_seed():
    a = generate_card(seed=42)
    b = generate_card(seed=42)
    assert a.fields.member_id == b.fields.member_id
    assert a.fields.subscriber_first == b.fields.subscriber_first


def test_generate_batch_count():
    cards = generate_batch(5, seed=0)
    assert len(cards) == 5


def test_generate_batch_member_ids_consistent_per_payer():
    cards = generate_batch(20, seed=0)
    by_payer: dict[str, set[str]] = {}
    for c in cards:
        by_payer.setdefault(c.fields.payer_id, set()).add(c.fields.member_id)
    # Each payer maps to exactly one member ID (its Stedi test subscriber).
    for payer_id, ids in by_payer.items():
        assert len(ids) == 1, f"payer {payer_id} has multiple member IDs: {ids}"


# --- render ---


def test_render_card_creates_png_and_ground_truth(tmp_path: Path):
    card = generate_card(seed=5)
    png = render_card(card, tmp_path, 0)

    assert png.exists()
    assert png.name == "card_0000.png"

    img = Image.open(png)
    assert img.size == (CARD_W, CARD_H)

    gt_path = tmp_path / "card_0000.json"
    assert gt_path.exists()
    gt = json.loads(gt_path.read_text())
    assert gt["member_id"] == card.fields.member_id
    assert gt["image_path"] == str(png)


def test_render_card_sets_image_path_on_card(tmp_path: Path):
    card = generate_card(seed=6)
    render_card(card, tmp_path, 0)
    assert card.image_path.endswith("card_0000.png")


def test_render_batch_creates_all_files(tmp_path: Path):
    cards = generate_batch(3, seed=0)
    paths = render_batch(cards, tmp_path)
    assert len(paths) == 3
    for i, p in enumerate(paths):
        assert p.name == f"card_{i:04d}.png"
        assert (tmp_path / f"card_{i:04d}.json").exists()


# --- payers ---


def test_get_payer_found():
    assert get_payer("84103").name == "Blue Cross Blue Shield"


def test_get_payer_missing():
    assert get_payer("NOPE") is None

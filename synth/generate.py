"""Top-level synthetic card generation: data + render + ground truth."""

from __future__ import annotations

from pathlib import Path

from synth.generator import generate_batch
from synth.render import render_batch


def generate_dataset(count: int, out_dir: Path, seed: int | None = None) -> list[Path]:
    """Generate `count` synthetic cards, render them to PNG, write ground truth.

    Returns the list of rendered PNG paths.
    """
    cards = generate_batch(count, seed=seed)
    return render_batch(cards, out_dir)

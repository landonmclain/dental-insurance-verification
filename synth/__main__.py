"""CLI entry point: generate a batch of synthetic cards.

Usage:
    python -m synth --count 5 --out synth/output [--seed 0]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from synth.generate import generate_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic insurance cards")
    parser.add_argument("--count", type=int, default=5, help="Number of cards to generate")
    parser.add_argument("--out", type=Path, default=Path("synth/output"), help="Output directory")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    args = parser.parse_args()

    paths = generate_dataset(args.count, args.out, seed=args.seed)
    print(f"Generated {len(paths)} cards in {args.out}")


if __name__ == "__main__":
    main()

"""Publishing guards: label coverage, word budget, and no reference text shipped.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from insurance_verify.benefits import parse_271
from insurance_verify.benefits.codes import CDT_LABELS

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
LOCAL = ROOT / "src" / "insurance_verify" / "benefits" / "local"


def _shown_cdt_codes() -> set[str]:
    """CDT codes the benefits panel shows: the ones with coverage evidence.

    Mirrors ``coverageOf`` in BenefitsPanel.tsx — a line is known when it has
    nonCovered, ACTIVE_COVERAGE, a copay/coinsurance, or limitations.
    """
    shown = set()
    for p in FIXTURES.glob("271_*.json"):
        for ln in parse_271(p.read_text()).lines:
            if not ln.code.startswith("D"):
                continue
            if ln.non_covered or ln.status == "ACTIVE_COVERAGE" or ln.coinsurance or ln.copay:
                shown.add(ln.code)
            elif ln.limitations:
                shown.add(ln.code)
    return shown


def _reference_descriptions() -> set[str]:
    """Description strings from the local-only CDT data files."""
    out = set()
    for name in ("cdt_codes.json", "cdt_descriptions.json"):
        path = LOCAL / name
        if not path.exists():
            continue
        data = json.loads(path.read_text())
        for row in data:
            desc = row.get("description")
            if desc:
                out.add(desc)
    return out


def _tracked_text_files() -> list[Path]:
    listing = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True)
    files = []
    for rel in listing.stdout.split("\0"):
        if not rel:
            continue
        p = ROOT / rel
        if not p.exists():
            continue
        try:
            p.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        files.append(p)
    return files


def test_every_shown_cdt_code_has_a_label():
    missing = sorted(c for c in _shown_cdt_codes() if c not in CDT_LABELS)
    assert not missing, f"codes the panel shows, with no label: {missing}"


def test_labels_are_short_phrases():
    long = {c: s for c, s in CDT_LABELS.items() if len(s.split()) > 6}
    assert not long, f"labels over the 6-word budget: {long}"


def test_labels_are_plain_words():
    reference = _reference_descriptions()
    if not reference:
        pytest.skip("reference data not present locally")
    copied = {c: s for c, s in CDT_LABELS.items() if s in reference}
    assert not copied, f"labels copied from reference descriptions: {copied}"


def test_no_reference_description_in_committed_files():
    reference = _reference_descriptions()
    if not reference:
        pytest.skip("reference data not present locally")
    hits = []
    for path in _tracked_text_files():
        text = path.read_text()
        for desc in reference:
            if desc in text:
                hits.append((path.relative_to(ROOT), desc))
                break
    assert not hits, f"reference text in committed files: {hits}"


def test_local_data_files_are_not_committed():
    # coverage_categories.json (code ranges -> coverage tiers) is our own
    # derived data and is committed; the local reference files stay out.
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True
    ).stdout.splitlines()
    for name in (
        "cdt_codes.json",
        "cdt_descriptions.json",
        "cdt_rows.json",
        "cdt_labels.json",
        "cdt_guide.pdf",
    ):
        path = f"src/insurance_verify/benefits/local/{name}"
        assert path not in tracked, f"{path} is committed — must stay local-only"

"""Procedure code map: CDT + STC codes to category and description.

The 271 responses reference two code systems:
- **CDT** (Current Dental Terminology) — procedure codes like ``D0120``.
- **STC** (Service Type Code) — X12 service-type codes like ``35`` (dental).

We do NOT hold the full CDT list, so this map is two layers:
1. **Category by prefix** — deterministic for every code (CDT D0xxx=diagnostic,
   D1xxx=preventive, …; STC codes mapped explicitly). This gives every code a
   category with no external data.
2. **Curated descriptions** — hand-written for the common codes that actually
   appear in the 271 statuses (the ones users search). For anything else, the
   parser falls back to Stedi's own ``definition`` from the response.
"""

from __future__ import annotations

import json
from pathlib import Path

from insurance_verify.config import get_settings

# Description mode comes from the tier (IV_MODE): full = local reference
# descriptions; labels = hand-written demo labels (gitignored).

# Local-only reference directory, gitignored; every load below is optional so a
# fresh clone runs.
_LOCAL = Path(__file__).parent / "local"

# Hand-written demo labels for the codes the panels display.
CDT_LABELS: dict[str, str] = {}
try:
    CDT_LABELS = json.loads((_LOCAL / "cdt_labels.json").read_text())
except FileNotFoundError:
    pass

# Reference CDT descriptions (837 codes) — local-only, never committed.
try:
    _desc_rows = json.loads((_LOCAL / "cdt_descriptions.json").read_text())
    _REFERENCE_CODES: dict[str, str] = {r["code"]: r["description"] for r in _desc_rows}
except FileNotFoundError:
    _REFERENCE_CODES = {}

# Community CDT code -> description list, much fuller than our curated set.
# Local-only, never committed.
try:
    _COMMUNITY_CODES: dict[str, str] = {
        e["code"]: e["description"] for e in json.loads((_LOCAL / "cdt_codes.json").read_text())
    }
except FileNotFoundError:
    _COMMUNITY_CODES = {}

# STC (X12 service type) code -> (category, description)
STC: dict[str, tuple[str, str]] = {
    "4": ("Diagnostic", "Diagnostic X-Ray"),
    "7": ("Anesthesia", "Anesthesia"),
    "23": ("Orthodontics", "Orthodontics"),
    "24": ("Prosthodontics", "Prosthodontics (dentures)"),
    "25": ("Implants", "Dental implants"),
    "26": ("Prosthodontics", "Prosthodontics (crowns and bridges)"),
    "27": ("Oral Surgery", "Oral surgery"),
    "28": ("Endodontics", "Endodontics (root canals)"),
    "30": ("Health Coverage", "Health benefit plan coverage"),
    "32": ("Waiting Period", "Plan waiting period"),
    "35": ("Dental Care", "Dental care"),
    "36": ("Preventive", "Routine (preventive) dental"),
    "38": ("Restorative", "Restorative (fillings)"),
    "39": ("Prosthodontics", "Prosthodontics (removable)"),
    "40": ("Oral Surgery", "Oral surgery (extractions)"),
    "41": ("Prosthodontics", "Prosthodontics (fixed)"),
}

# CDT code prefix -> category. Covers every CDT code without the full list.
CDT_PREFIX_CATEGORY: dict[str, str] = {
    "D0": "Diagnostic",
    "D1": "Preventive",
    "D2": "Restorative",
    "D3": "Endodontics",
    "D4": "Periodontics",
    "D5": "Prosthodontics",
    "D6": "Implants",
    "D7": "Oral Surgery",
    "D8": "Orthodontics",
    "D9": "Adjunctive",
}


def categorize(code: str, system: str | None) -> str | None:
    """Return a human category for a code, or None if unknown."""
    if not code:
        return None
    if system == "STC" or (system is None and not code.startswith("D")):
        return STC.get(code, (None, None))[0]
    if code.startswith("D") and len(code) >= 2:
        return CDT_PREFIX_CATEGORY.get(code[:2])
    return None


def describe(code: str, system: str | None) -> str | None:
    """Description for a code, honoring the tier's description mode. STC
    descriptions are our own words; CDT text comes from reference data (full),
    demo labels (labels), or nothing (none).
    """
    mode = get_settings().desc_mode
    if system == "STC" or (system is None and not code.startswith("D")):
        return STC.get(code, (None, None))[1]
    if mode == "none":
        return None
    if mode == "labels":
        return CDT_LABELS.get(code)
    # full: reference text, then the community list
    return _REFERENCE_CODES.get(code) or _COMMUNITY_CODES.get(code)

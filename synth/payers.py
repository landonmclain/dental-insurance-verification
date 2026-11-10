"""Payer registry: real Stedi test payers with per-payer ID formats.

Each payer maps to a valid Stedi dental test subscriber (member ID, name, DOB)
so the 270 matches a Stedi mock request and returns active coverage. The
company names and payer IDs are the real ones Stedi's test payers use; the
member/group ID formats and card colors are tuned per payer. The full per-payer
table (with tuned ID formats and recognizers) is the private consulting piece.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Payer:
    name: str
    payer_id: str
    # Regex-ish format hints for member / group IDs (used by the generator and validator)
    member_format: str
    group_format: str
    # Colors for the card render
    primary: tuple[int, int, int]
    secondary: tuple[int, int, int]
    # Whether the card is dental, medical, or combined
    kind: str = "dental"
    # Stedi routing: the test-mode payer ID and the exact subscriber the test
    # payer accepts. When set, the generator puts these on the card so the 270
    # returns active coverage. In production each payer maps to a real Stedi ID.
    stedi_payer_id: str = "STEDI"
    stedi_member_id: str = ""
    stedi_first: str = ""
    stedi_last: str = ""
    stedi_dob: str = ""  # ISO date (YYYY-MM-DD)
    # Group number / plan name from the payer's 271 response (when known).
    group_id: str = ""
    plan_name: str | None = None


@dataclass(frozen=True)
class Practice:
    """The provider (dental practice) performing the verification.

    Constant across cards — it's the practice, not the patient.
    """

    npi: str
    organization_name: str


# The demo practice used for all synthetic cards.
PRACTICE = Practice(npi="1999999984", organization_name="Demo Dental Group")


# The real Stedi dental test payers. The full per-payer table is private.
PAYERS: list[Payer] = [
    Payer(
        "Blue Cross Blue Shield",
        "84103",
        r"[A-Z]{3}\d{9}",
        r"[A-Z]{3}\d{2}[A-Z]\d{4}",
        (0, 51, 102),
        (0, 30, 60),
        "dental",
        stedi_payer_id="84103",
        stedi_member_id="AFK987654321",
        stedi_first="Aardvark",
        stedi_last="Dent",
        stedi_dob="1970-12-12",
        group_id="CAA28A0001",
    ),
    Payer(
        "Ameritas",
        "AMTAS00425",
        r"\d{9}",
        r"\d{7}",
        (34, 139, 34),
        (0, 80, 0),
        "dental",
        stedi_payer_id="AMTAS00425",
        stedi_member_id="007007007",
        stedi_first="Falcon",
        stedi_last="Dent",
        stedi_dob="1985-06-07",
        group_id="5121024",
        plan_name="DENTAL PLAN PLUS",
    ),
    Payer(
        "Cigna",
        "62308",
        r"[A-Z]\d{10}",
        r"\d{7}",
        (70, 70, 90),
        (30, 30, 50),
        "dental",
        stedi_payer_id="62308",
        stedi_member_id="U3141592653",
        stedi_first="Jaguar",
        stedi_last="Dent",
        stedi_dob="1996-05-05",
        group_id="7778889",
    ),
    Payer(
        "UnitedHealthcare",
        "52133",
        r"\d{9}",
        r"\d{6}",
        (0, 90, 156),
        (0, 45, 78),
        "dental",
        stedi_payer_id="52133",
        stedi_member_id="404404404",
        stedi_first="Beaver",
        stedi_last="Dent",
        stedi_dob="1969-06-28",
        group_id="007007",
    ),
    Payer(
        "Metlife",
        "10134",
        r"\d{8}",
        r"\d{7}",
        (0, 102, 178),
        (0, 51, 102),
        "dental",
        stedi_payer_id="10134",
        stedi_member_id="88877788",
        stedi_first="Elephant",
        stedi_last="Dent",
        stedi_dob="1984-02-29",
        group_id="7771117",
    ),
    # A medical test payer, so the demo can show a medical card being flagged.
    # A dental request (STC 35) for this subscriber returns a medical 271.
    Payer(
        "Humana",
        "61101",
        r"[A-Z]{6}\d{3}",
        r"\d{7}",
        (0, 102, 178),
        (0, 51, 102),
        "medical",
        stedi_payer_id="61101",
        stedi_member_id="HUMANA123",
        stedi_first="Jane",
        stedi_last="Doe",
        stedi_dob="1975-05-05",
        plan_name="Humana Gold Plan",
    ),
]


def get_payer(payer_id: str) -> Payer | None:
    for p in PAYERS:
        if p.payer_id == payer_id:
            return p
    return None

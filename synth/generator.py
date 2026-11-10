"""Synthetic card data generation.

Every card is generated with Faker and an invented payer. No real patient data.
Each card ships with a perfect ground-truth record for evals.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from datetime import date

from faker import Faker

from insurance_verify.schemas.card import CardFields
from synth.payers import PAYERS, PRACTICE, Payer

_fake = Faker()
Faker.seed(0)


def _gen_id(pattern: str, rng: random.Random | None = None) -> str:
    """Generate an ID matching a simple format pattern.

    Supports \\d{n} and [A-Z]{n} tokens, e.g. r"\\d{9}" or r"[A-Z]{3}\\d{6}".
    Pass an rng for reproducible output.
    """
    rng = rng or random
    out = []
    i = 0
    while i < len(pattern):
        # \d{n}
        m = re.match(r"\\d\{(\d+)\}", pattern[i:])
        if m:
            out.append("".join(rng.choices("0123456789", k=int(m.group(1)))))
            i += len(m.group(0))
            continue
        # [A-Z]{n}
        m = re.match(r"\[A-Z\]\{(\d+)\}", pattern[i:])
        if m:
            out.append("".join(rng.choices("ABCDEFGHJKLMNPQRSTUVWXYZ", k=int(m.group(1)))))
            i += len(m.group(0))
            continue
        # bare [A-Z] (single letter)
        m = re.match(r"\[A-Z\]", pattern[i:])
        if m:
            out.append(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ"))
            i += len(m.group(0))
            continue
        out.append(pattern[i])
        i += 1
    return "".join(out)


@dataclass
class SyntheticCard:
    """A generated card: its fields plus the ground-truth answer key."""

    payer: Payer
    fields: CardFields
    ground_truth: dict[str, str]
    difficulty: str = "easy"
    image_path: str = ""

    def to_ground_truth_json(self) -> dict:
        return {
            "payer_id": self.payer.payer_id,
            "payer_name": self.payer.name,
            "member_id": self.fields.member_id,
            "group_id": self.fields.group_id,
            "subscriber_first": self.fields.subscriber_first,
            "subscriber_last": self.fields.subscriber_last,
            "subscriber_dob": (
                self.fields.subscriber_dob.isoformat() if self.fields.subscriber_dob else None
            ),
            "relationship": self.fields.relationship,
            "plan_name": self.fields.plan_name,
            "subscriber_address_line1": self.fields.subscriber_address_line1,
            "subscriber_address_city": self.fields.subscriber_address_city,
            "subscriber_address_state": self.fields.subscriber_address_state,
            "subscriber_address_zip": self.fields.subscriber_address_zip,
            "provider_npi": PRACTICE.npi,
            "provider_organization_name": PRACTICE.organization_name,
            "stedi_payer_id": self.payer.stedi_payer_id,
            "difficulty": self.difficulty,
            "image_path": self.image_path,
        }


def generate_card(payer: Payer | None = None, seed: int | None = None) -> SyntheticCard:
    """Generate one synthetic card with a random (or given) payer.

    When a seed is given, the whole card (payer, names, DOB, IDs) is
    reproducible: the same seed always yields the same card.
    """
    rng = random.Random(seed)
    payer = payer or rng.choice(PAYERS)

    # Per-call Faker seeded from the rng, so names/DOB are reproducible.
    fake = Faker()
    fake.seed_instance(rng.randint(0, 2**32 - 1))

    # Payers with a Stedi test subscriber use it exactly, so the 270 returns
    # active coverage.
    if payer.stedi_member_id:
        first = payer.stedi_first
        last = payer.stedi_last
        dob = date.fromisoformat(payer.stedi_dob)
        member_id = payer.stedi_member_id
    else:
        first = fake.first_name()
        last = fake.last_name()
        dob = fake.date_of_birth(minimum_age=18, maximum_age=75)
        member_id = _gen_id(payer.member_format, rng)

    # Subscriber address (intake data, not printed on the card).
    address_line1 = fake.street_address()
    address_city = fake.city()
    address_state = fake.state_abbr()
    address_zip = fake.zipcode()

    group_id = payer.group_id or _gen_id(payer.group_format, rng)

    fields = CardFields(
        member_id=member_id,
        group_id=group_id,
        payer_id=payer.payer_id,
        subscriber_first=first,
        subscriber_last=last,
        subscriber_dob=dob,
        relationship="self",
        payer_name=payer.name,
        # The payer's real plan name when known, else one derived from its name.
        plan_name=(
            payer.plan_name
            or (
                f"{payer.name} Plan"
                if "dental" in payer.name.lower()
                else f"{payer.name} Dental Plan"
            )
        ),
        subscriber_address_line1=address_line1,
        subscriber_address_city=address_city,
        subscriber_address_state=address_state,
        subscriber_address_zip=address_zip,
    )

    return SyntheticCard(
        payer=payer,
        fields=fields,
        ground_truth={
            "member_id": member_id,
            "group_id": group_id,
            "payer_id": payer.payer_id,
            "subscriber_first": first,
            "subscriber_last": last,
            "subscriber_dob": dob.isoformat(),
            "subscriber_address_line1": address_line1,
            "subscriber_address_city": address_city,
            "subscriber_address_state": address_state,
            "subscriber_address_zip": address_zip,
        },
    )


def generate_batch(count: int, seed: int | None = None) -> list[SyntheticCard]:
    rng = random.Random(seed)
    return [generate_card(seed=rng.randint(0, 10**9)) for _ in range(count)]

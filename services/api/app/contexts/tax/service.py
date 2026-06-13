"""Chapter VI-A declaration sections + capped eligible-deduction math.

Pure, Decimal-only. The eligible deduction (sum of each section capped to its
statutory limit) feeds the OLD-regime TDS computation. New regime ignores these.
"""

from decimal import Decimal

from pydantic import BaseModel

from app.core.money import D, Money, round_rupee

ZERO = D(0)


class TaxSection(BaseModel):
    key: str
    label: str
    cap: Decimal


# FY2025-26 Chapter VI-A limits (old regime).
SECTIONS: list[TaxSection] = [
    TaxSection(key="80C", label="80C — PF, ELSS, LIC, PPF, tuition", cap=D(150000)),
    TaxSection(key="80CCD1B", label="80CCD(1B) — NPS (additional)", cap=D(50000)),
    TaxSection(key="80D", label="80D — Health insurance premium", cap=D(50000)),
    TaxSection(key="80TTA", label="80TTA — Savings account interest", cap=D(10000)),
    TaxSection(key="80E", label="80E — Education loan interest", cap=D(0)),  # 0 = uncapped
    TaxSection(key="home_loan_interest", label="24(b) — Home loan interest", cap=D(200000)),
]
SECTION_KEYS = frozenset(s.key for s in SECTIONS)
_CAPS: dict[str, Decimal] = {s.key: s.cap for s in SECTIONS}


def section_cap(key: str) -> Decimal | None:
    return _CAPS.get(key)


def eligible_deduction(items: dict[str, Money]) -> Money:
    """Total deductible: each declared section capped to its limit (cap 0 means
    uncapped). Unknown sections are ignored."""
    total = ZERO
    for key, amount in items.items():
        cap = _CAPS.get(key)
        if cap is None or amount <= 0:
            continue
        eligible = amount if cap == 0 else min(amount, cap)
        total += eligible
    return round_rupee(total)

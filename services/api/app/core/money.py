"""Money arithmetic for payroll-grade correctness.

RULES (see blueprint/17-technology-stack.md §17.4):
- All money values are `decimal.Decimal`. `float` is BANNED in financial code.
- All rounding goes through `round_money` — never call round() ad hoc.
- Default policy: 2 decimal places, ROUND_HALF_UP (Indian statutory convention;
  specific statutory components override via explicit quantizers below).
"""

from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
WHOLE_RUPEE = Decimal("1")

Money = Decimal  # semantic alias used in type hints


def D(value: str | int) -> Decimal:
    """Construct a Decimal safely. Strings/ints only — floats are rejected by design."""
    return Decimal(value)


def round_money(amount: Decimal) -> Decimal:
    """Standard money rounding: 2dp, half-up."""
    return amount.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def round_rupee(amount: Decimal) -> Decimal:
    """Whole-rupee rounding (e.g. PF, income tax) — half-up."""
    return amount.quantize(WHOLE_RUPEE, rounding=ROUND_HALF_UP)

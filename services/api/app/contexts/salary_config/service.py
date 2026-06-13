"""Salary-component resolution engine (pure, Decimal-only).

Turns a component catalogue + a monthly CTC into an itemised earnings split.
Resolution order: fixed & %CTC first, then %basic (off the BASIC component),
then a single balancing component soaks up the remainder (CTC − employer PF −
everything else). This generalises the built-in 40%-basic / 50%-HRA split:
with the seeded BASIC/HRA/SPECIAL set it reproduces derive_structure exactly.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.money import D, Money, round_money

ZERO = D(0)


@dataclass(frozen=True)
class Component:
    code: str
    name: str
    component_type: str  # earning | reimbursement | deduction | employer
    calc_type: str       # fixed | pct_ctc | pct_basic | pct_gross | balancing
    value: Decimal


@dataclass(frozen=True)
class ResolvedLine:
    code: str
    name: str
    amount: Money


def resolve_earnings(
    monthly_ctc: Money,
    components: list[Component],
    *,
    employer_pf: Money = ZERO,
    basic_code: str = "BASIC",
) -> tuple[list[ResolvedLine], Money]:
    """Resolve the earning side of a structure. Returns (ordered lines, gross).
    `employer_pf` is the slice of CTC that is employer cost, not paid in gross."""
    earnings = [c for c in components if c.component_type in ("earning", "reimbursement")]
    amounts: dict[str, Money] = {}

    # pass 1 — independent components
    for c in earnings:
        if c.calc_type == "fixed":
            amounts[c.code] = round_money(c.value)
        elif c.calc_type == "pct_ctc":
            amounts[c.code] = round_money(monthly_ctc * c.value / D(100))

    basic = amounts.get(basic_code) or next(
        (amounts[c.code] for c in earnings if c.calc_type == "pct_ctc"), ZERO
    )

    # pass 2 — percentage of basic
    for c in earnings:
        if c.calc_type == "pct_basic":
            amounts[c.code] = round_money(basic * c.value / D(100))

    # pass 3 — balancing component soaks up the remainder
    running = sum(amounts.values(), ZERO)
    for c in earnings:
        if c.calc_type == "balancing":
            rem = monthly_ctc - employer_pf - running
            amounts[c.code] = rem if rem > 0 else ZERO
            running += amounts[c.code]

    lines = [ResolvedLine(c.code, c.name, amounts[c.code]) for c in earnings if c.code in amounts]
    gross = sum((line.amount for line in lines), ZERO)
    return lines, gross

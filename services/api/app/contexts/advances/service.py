"""Advance/loan recovery math (pure, Decimal-only)."""

from app.core.money import D, Money, round_rupee

ZERO = D(0)


def emi_for_month(emi_amount: Money, outstanding: Money) -> Money:
    """The amount to recover this month: the EMI, but never more than what is
    still owed (the final instalment clears the remainder). Floored at zero."""
    if outstanding <= 0 or emi_amount <= 0:
        return ZERO
    return round_rupee(min(emi_amount, outstanding))


def remaining_after(outstanding: Money, recovered: Money) -> Money:
    """Outstanding after applying a recovery, never negative."""
    rem = outstanding - recovered
    return rem if rem > 0 else ZERO

"""Arrear computation for back-dated salary changes (pure, Decimal-only)."""

from datetime import date

from app.core.money import D, Money, round_rupee


def retro_months(effective_from: date, today: date) -> int:
    """Whole months already elapsed since the effective date — the months that
    were paid at the old rate and now owe a top-up. 0 if effective this month
    or in the future."""
    months = (today.year - effective_from.year) * 12 + (today.month - effective_from.month)
    return max(months, 0)


def arrear_amount(old_gross: Money, new_gross: Money, months: int) -> Money:
    """Monthly gross difference × elapsed months (can be negative = recovery)."""
    if months <= 0:
        return D(0)
    return round_rupee((new_gross - old_gross) * months)

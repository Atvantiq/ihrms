"""Overtime pay math (pure, Decimal-only)."""

from decimal import Decimal

from app.core.money import D, Money, round_rupee

HOURS_PER_DAY = D(8)


def hourly_rate(monthly_gross: Money, working_days: int) -> Money:
    """Hourly rate from monthly gross over the month's standard hours."""
    if working_days <= 0:
        return D(0)
    return monthly_gross / (D(working_days) * HOURS_PER_DAY)


def ot_pay(hours: Decimal, rate_multiplier: Decimal, rate_per_hour: Money) -> Money:
    """Overtime pay for one entry: hours x multiplier x hourly rate."""
    if hours <= 0 or rate_per_hour <= 0:
        return D(0)
    return round_rupee(hours * rate_multiplier * rate_per_hour)

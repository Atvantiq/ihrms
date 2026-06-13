"""Timesheet week math — pure, Decimal-only, testable."""

from datetime import date, timedelta
from decimal import Decimal

STANDARD_WEEK_HOURS = Decimal("40")


def week_start(d: date) -> date:
    """Monday of the week containing d."""
    return d - timedelta(days=d.weekday())


def week_dates(start: date) -> list[date]:
    """The 7 dates (Mon–Sun) of a week given its Monday."""
    return [start + timedelta(days=i) for i in range(7)]


def total_hours(entries: list[Decimal]) -> Decimal:
    return sum(entries, Decimal(0))


def overtime(total: Decimal) -> Decimal:
    """Hours beyond the standard week (never negative)."""
    return max(total - STANDARD_WEEK_HOURS, Decimal(0))

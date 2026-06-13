"""Comp-off validity rules (pure)."""

from datetime import date, timedelta

VALIDITY_DAYS = 90


def expiry_for(earned_date: date) -> date:
    """A comp-off credit lapses VALIDITY_DAYS after the day it was earned."""
    return earned_date + timedelta(days=VALIDITY_DAYS)


def is_expired(expiry_date: date | None, today: date) -> bool:
    return expiry_date is not None and today > expiry_date

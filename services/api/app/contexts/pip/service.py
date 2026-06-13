"""PIP lifecycle rules (pure)."""

from datetime import date, timedelta

# Outcomes a PIP can be closed with (from the active state).
CLOSE_OUTCOMES = frozenset({"improved", "extended", "terminated", "closed"})


def checkpoint_dates(start: date) -> list[date]:
    """Standard 30/60/90-day checkpoint dates from the PIP start."""
    return [start + timedelta(days=n) for n in (30, 60, 90)]


def is_open(status: str) -> bool:
    return status == "active"


def is_valid_outcome(outcome: str) -> bool:
    return outcome in CLOSE_OUTCOMES

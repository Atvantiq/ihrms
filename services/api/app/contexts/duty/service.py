"""Duty-request helpers (pure)."""

from datetime import date, timedelta


def attendance_status_for(duty_type: str) -> str:
    """The attendance status an approved duty request writes for each day."""
    return "wfh" if duty_type == "wfh" else "present"


def date_range(start: date, end: date) -> list[date]:
    """Inclusive list of dates from start to end."""
    days = (end - start).days
    return [start + timedelta(days=n) for n in range(days + 1)]

"""Golden tests for duty-request helpers."""

from datetime import date

from app.contexts.duty.service import attendance_status_for, date_range


def test_status_mapping() -> None:
    assert attendance_status_for("wfh") == "wfh"
    assert attendance_status_for("on_duty") == "present"


def test_date_range_inclusive() -> None:
    r = date_range(date(2026, 6, 1), date(2026, 6, 3))
    assert r == [date(2026, 6, 1), date(2026, 6, 2), date(2026, 6, 3)]


def test_single_day_range() -> None:
    assert date_range(date(2026, 6, 1), date(2026, 6, 1)) == [date(2026, 6, 1)]

"""Golden tests for employee-records pure helpers."""

from datetime import date
from decimal import Decimal

from app.contexts.employee_records.service import (
    nominee_total_ok,
    special_dates,
)


def test_special_dates_projects_next_occurrence() -> None:
    today = date(2026, 6, 13)
    dates = special_dates(date(1990, 8, 1), date(2020, 3, 15), today)
    by_label = {d.label: d for d in dates}
    # birthday 1 Aug 2026 is the next occurrence after 13 Jun
    assert by_label["Birthday"].on == date(2026, 8, 1)
    assert by_label["Birthday"].in_days == (date(2026, 8, 1) - today).days
    # work anniversary 15 Mar already passed in 2026 -> rolls to 2027
    anniv = by_label["Work anniversary"]
    assert anniv.on == date(2027, 3, 15)
    assert anniv.years == 7  # 2020 -> 2027
    # sorted by soonest first
    assert dates[0].in_days <= dates[1].in_days


def test_special_dates_handles_feb_29() -> None:
    # Feb-29 birthday in a non-leap projection year falls back to Mar 1
    dates = special_dates(date(2000, 2, 29), None, date(2026, 1, 1))
    assert dates[0].on == date(2026, 3, 1)


def test_special_dates_empty_when_no_anchors() -> None:
    assert special_dates(None, None, date(2026, 6, 13)) == []


def test_nominee_total_guard() -> None:
    assert nominee_total_ok([Decimal(60)], Decimal(40)) is True   # exactly 100
    assert nominee_total_ok([Decimal(60)], Decimal("40.01")) is False
    assert nominee_total_ok([], Decimal(100)) is True
    assert nominee_total_ok([Decimal(50), Decimal(30)], Decimal(25)) is False

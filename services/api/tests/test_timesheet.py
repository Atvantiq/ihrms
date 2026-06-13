"""Golden tests for timesheet week math — pure, no DB."""

from datetime import date
from decimal import Decimal

from app.contexts.timesheet.service import (
    overtime,
    total_hours,
    week_dates,
    week_start,
)


def test_week_start_is_monday() -> None:
    # 2026-06-13 is a Saturday -> Monday is 2026-06-08
    assert week_start(date(2026, 6, 13)) == date(2026, 6, 8)
    # a Monday maps to itself
    assert week_start(date(2026, 6, 8)) == date(2026, 6, 8)


def test_week_dates_are_seven_mon_to_sun() -> None:
    days = week_dates(date(2026, 6, 8))
    assert len(days) == 7
    assert days[0] == date(2026, 6, 8)  # Monday
    assert days[-1] == date(2026, 6, 14)  # Sunday


def test_total_hours() -> None:
    assert total_hours([Decimal("8"), Decimal("7.5"), Decimal("4")]) == Decimal("19.5")
    assert total_hours([]) == Decimal("0")


def test_overtime_only_above_standard() -> None:
    assert overtime(Decimal("40")) == Decimal("0")
    assert overtime(Decimal("45")) == Decimal("5")
    assert overtime(Decimal("32")) == Decimal("0")

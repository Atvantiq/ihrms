"""Golden tests for leave quantity math — the correctness-critical core.

These are pure-function, table-driven tests: no DB, deterministic. They are
the safety net the dev team relies on when changing accrual/balance logic.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.contexts.leave.service import (
    accrued_to_date,
    available,
    working_days,
)


class TestWorkingDays:
    @pytest.mark.parametrize(
        "start,end,half,expected",
        [
            # single weekday
            (date(2026, 6, 22), date(2026, 6, 22), False, "1"),
            # Mon–Fri full week = 5
            (date(2026, 6, 22), date(2026, 6, 26), False, "5"),
            # Mon–Sun spanning a weekend = 5 working days
            (date(2026, 6, 22), date(2026, 6, 28), False, "5"),
            # Fri–Mon (incl weekend) = 2 working days
            (date(2026, 6, 26), date(2026, 6, 29), False, "2"),
            # half day on a single weekday
            (date(2026, 6, 22), date(2026, 6, 22), True, "0.5"),
            # two full weeks = 10
            (date(2026, 6, 1), date(2026, 6, 12), False, "10"),
        ],
    )
    def test_counts(self, start: date, end: date, half: bool, expected: str) -> None:
        assert working_days(start, end, half) == Decimal(expected)

    def test_end_before_start_raises(self) -> None:
        with pytest.raises(ValueError, match="before start"):
            working_days(date(2026, 6, 10), date(2026, 6, 1), False)

    def test_half_day_multi_day_raises(self) -> None:
        with pytest.raises(ValueError, match="single day"):
            working_days(date(2026, 6, 22), date(2026, 6, 23), True)

    def test_half_day_on_weekend_raises(self) -> None:
        with pytest.raises(ValueError, match="weekend"):
            working_days(date(2026, 6, 20), date(2026, 6, 20), True)

    def test_weekend_only_range_is_zero(self) -> None:
        # Sat–Sun, no working days
        assert working_days(date(2026, 6, 20), date(2026, 6, 21), False) == Decimal(0)


class TestWorkingDaysWithHolidays:
    def test_holiday_excluded(self) -> None:
        # Mon–Fri week with Wed a holiday = 4 working days
        hol = frozenset({date(2026, 6, 24)})
        assert working_days(date(2026, 6, 22), date(2026, 6, 26), False, hol) == Decimal("4")

    def test_holiday_on_weekend_no_double_subtract(self) -> None:
        # holiday falling on Saturday doesn't reduce the count further
        hol = frozenset({date(2026, 6, 20)})
        assert working_days(date(2026, 6, 22), date(2026, 6, 26), False, hol) == Decimal("5")

    def test_half_day_on_holiday_raises(self) -> None:
        hol = frozenset({date(2026, 6, 22)})
        with pytest.raises(ValueError, match="holiday"):
            working_days(date(2026, 6, 22), date(2026, 6, 22), True, hol)

    def test_full_range_all_holidays_is_zero(self) -> None:
        hol = frozenset({date(2026, 6, 22), date(2026, 6, 23)})
        assert working_days(date(2026, 6, 22), date(2026, 6, 23), False, hol) == Decimal(0)


class TestAccrual:
    def test_annual_upfront_gives_full_entitlement(self) -> None:
        got = accrued_to_date("annual_upfront", Decimal("7"), Decimal("0"), date(2026, 1, 5))
        assert got == Decimal("7")

    def test_event_based_gives_full_entitlement(self) -> None:
        got = accrued_to_date("event_based", Decimal("182"), Decimal("0"), date(2026, 8, 1))
        assert got == Decimal("182")

    @pytest.mark.parametrize(
        "month,expected",
        [
            (1, "1.5"),
            (6, "9.0"),
            (12, "18.0"),
        ],
    )
    def test_monthly_accrues_by_month(self, month: int, expected: str) -> None:
        got = accrued_to_date("monthly", Decimal("18"), Decimal("1.5"), date(2026, month, 15))
        assert got == Decimal(expected)

    def test_monthly_caps_at_annual_entitlement(self) -> None:
        # a rate that would exceed annual is capped
        got = accrued_to_date("monthly", Decimal("10"), Decimal("1.5"), date(2026, 12, 1))
        assert got == Decimal("10")


class TestAvailable:
    def test_available_formula(self) -> None:
        bal = {
            "accrued": Decimal("9"),
            "carried_forward": Decimal("3"),
            "used": Decimal("2"),
            "pending": Decimal("1"),
        }
        # 9 + 3 - 2 - 1 = 9
        assert available(bal) == Decimal("9")

    def test_available_can_go_to_zero(self) -> None:
        bal = {
            "accrued": Decimal("5"),
            "carried_forward": Decimal("0"),
            "used": Decimal("5"),
            "pending": Decimal("0"),
        }
        assert available(bal) == Decimal("0")

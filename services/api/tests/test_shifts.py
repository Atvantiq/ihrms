"""Golden tests for shift duration math (incl. overnight shifts)."""

from datetime import time

from app.contexts.shifts.service import crosses_midnight, shift_hours, shift_minutes
from app.core.money import D


class TestCrossesMidnight:
    def test_day_shift(self) -> None:
        assert crosses_midnight(time(9, 30), time(18, 30)) is False

    def test_night_shift(self) -> None:
        assert crosses_midnight(time(22, 0), time(6, 0)) is True

    def test_same_time_is_overnight(self) -> None:
        assert crosses_midnight(time(9, 0), time(9, 0)) is True


class TestShiftHours:
    def test_general_shift_less_break(self) -> None:
        # 09:30–18:30 = 9h, minus 60m break = 8h
        assert shift_hours(time(9, 30), time(18, 30), 60) == D("8.00")

    def test_no_break(self) -> None:
        assert shift_hours(time(9, 0), time(17, 0), 0) == D("8.00")

    def test_overnight_rolls_to_next_day(self) -> None:
        # 22:00–06:00 = 8h, minus 30m break = 7.5h
        assert shift_hours(time(22, 0), time(6, 0), 30) == D("7.50")

    def test_half_hour_precision(self) -> None:
        assert shift_minutes(time(9, 0), time(13, 30), 0) == 270
        assert shift_hours(time(9, 0), time(13, 30), 0) == D("4.50")

    def test_break_cannot_make_negative(self) -> None:
        assert shift_minutes(time(9, 0), time(10, 0), 120) == 0

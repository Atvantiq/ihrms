"""Golden tests for PIP lifecycle helpers."""

from datetime import date

from app.contexts.pip.service import (
    checkpoint_dates,
    is_open,
    is_valid_outcome,
)


def test_checkpoint_dates_30_60_90() -> None:
    assert checkpoint_dates(date(2026, 4, 1)) == [
        date(2026, 5, 1), date(2026, 5, 31), date(2026, 6, 30),
    ]


def test_is_open() -> None:
    assert is_open("active") is True
    assert is_open("closed") is False


def test_valid_outcomes() -> None:
    for o in ("improved", "extended", "terminated", "closed"):
        assert is_valid_outcome(o) is True
    assert is_valid_outcome("promoted") is False

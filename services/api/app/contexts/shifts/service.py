"""Shift duration math (pure). Handles night shifts that cross midnight."""

from datetime import time
from decimal import Decimal

from app.core.money import D


def crosses_midnight(start: time, end: time) -> bool:
    """A shift whose end time is at or before its start time runs overnight."""
    return end <= start


def shift_minutes(start: time, end: time, break_minutes: int) -> int:
    """Net worked minutes between start and end, less the break. Overnight
    shifts (end ≤ start) roll the end into the next day."""
    start_m = start.hour * 60 + start.minute
    end_m = end.hour * 60 + end.minute
    if end_m <= start_m:
        end_m += 24 * 60
    return max(end_m - start_m - break_minutes, 0)


def shift_hours(start: time, end: time, break_minutes: int) -> Decimal:
    """Net worked hours for a shift, rounded to two decimals."""
    return (D(shift_minutes(start, end, break_minutes)) / D(60)).quantize(D("0.01"))

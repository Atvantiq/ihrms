"""Golden tests for performance logic — bands, 9-box, increments."""

from app.contexts.performance.service import (
    apply_increment,
    band,
    nine_box,
    nine_box_label,
    suggested_increment_pct,
)
from app.core.money import D


def test_band() -> None:
    assert band(1) == 1
    assert band(2) == 1
    assert band(3) == 2
    assert band(4) == 3
    assert band(5) == 3


def test_nine_box_star_and_risk() -> None:
    assert nine_box(5, 5) == 9
    assert nine_box_label(nine_box(5, 5)) == "Star"
    assert nine_box(1, 1) == 1
    assert nine_box_label(nine_box(1, 1)) == "Risk"


def test_nine_box_mixed() -> None:
    # high performance, low potential -> performance_band 3, potential_band 1 -> cell 3
    assert nine_box(5, 1) == 3
    # low performance, high potential -> cell 7
    assert nine_box(1, 5) == 7


def test_suggested_increment() -> None:
    assert suggested_increment_pct(5) == D(15)
    assert suggested_increment_pct(3) == D(6)
    assert suggested_increment_pct(1) == D(0)


def test_apply_increment() -> None:
    assert apply_increment(D(1000000), D(10)) == D(1100000)
    assert apply_increment(D(1400000), D(15)) == D(1610000)
    assert apply_increment(D(1000000), D(0)) == D(1000000)

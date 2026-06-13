"""Golden tests for band-fit."""

from app.contexts.bands.service import band_fit
from app.core.money import D


def test_within_range() -> None:
    assert band_fit(D(1200000), D(800000), D(1600000)) == "within"


def test_at_boundaries_is_within() -> None:
    assert band_fit(D(800000), D(800000), D(1600000)) == "within"
    assert band_fit(D(1600000), D(800000), D(1600000)) == "within"


def test_below_range() -> None:
    assert band_fit(D(500000), D(800000), D(1600000)) == "below"


def test_above_range() -> None:
    assert band_fit(D(2000000), D(800000), D(1600000)) == "above"

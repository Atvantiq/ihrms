"""Golden tests for check-in mood labels."""

from app.contexts.check_ins.service import mood_label


def test_mood_labels() -> None:
    assert mood_label(1) == "struggling"
    assert mood_label(3) == "okay"
    assert mood_label(5) == "great"


def test_unknown_mood_defaults() -> None:
    assert mood_label(9) == "okay"

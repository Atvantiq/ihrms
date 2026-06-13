"""Golden tests for the career-ladder helper."""

from app.contexts.career.service import Rung, next_rung

RUNGS = [
    Rung("a", "Engineer", 1),
    Rung("b", "Senior", 2),
    Rung("c", "Staff", 3),
    Rung("d", "Principal", 4),
]


def test_next_rung_middle() -> None:
    nxt = next_rung(RUNGS, 2)
    assert nxt is not None and nxt.name == "Staff" and nxt.rank == 3


def test_next_rung_from_bottom() -> None:
    assert next_rung(RUNGS, 1).name == "Senior"  # type: ignore[union-attr]


def test_top_has_no_next() -> None:
    assert next_rung(RUNGS, 4) is None


def test_unsorted_input_picks_lowest_above() -> None:
    shuffled = [RUNGS[3], RUNGS[0], RUNGS[2], RUNGS[1]]
    assert next_rung(shuffled, 1).rank == 2  # type: ignore[union-attr]


def test_empty() -> None:
    assert next_rung([], 1) is None

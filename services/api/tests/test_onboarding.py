"""Golden tests for onboarding checklist progress."""

from app.contexts.onboarding.service import progress


def test_empty() -> None:
    p = progress([])
    assert p.done == 0 and p.total == 0 and p.pct == 0


def test_partial() -> None:
    p = progress(["done", "pending", "done", "pending"])
    assert p.done == 2 and p.total == 4 and p.pct == 50


def test_all_done() -> None:
    p = progress(["done", "done"])
    assert p.pct == 100


def test_rounding() -> None:
    # 1 of 3 -> 33%
    assert progress(["done", "pending", "pending"]).pct == 33
    # 2 of 3 -> 67%
    assert progress(["done", "done", "pending"]).pct == 67

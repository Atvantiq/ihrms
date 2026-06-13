"""Golden tests for ticket status transitions."""

from app.contexts.helpdesk.service import CATEGORIES, can_transition


def test_categories() -> None:
    assert {"payroll", "it", "leave"} <= set(CATEGORIES)


def test_valid_transitions() -> None:
    assert can_transition("open", "in_progress")
    assert can_transition("in_progress", "resolved")
    assert can_transition("resolved", "closed")
    assert can_transition("resolved", "in_progress")  # reopen


def test_invalid_transitions() -> None:
    assert not can_transition("closed", "open")
    assert not can_transition("open", "open")

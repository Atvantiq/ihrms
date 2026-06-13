"""Golden tests for recruitment pipeline transitions."""

from app.contexts.recruitment.service import can_transition, next_stage


def test_forward_one_step_allowed() -> None:
    assert can_transition("applied", "screening")
    assert can_transition("screening", "interview")
    assert can_transition("interview", "offer")
    assert can_transition("offer", "hired")


def test_skipping_stages_blocked() -> None:
    assert not can_transition("applied", "interview")
    assert not can_transition("applied", "offer")


def test_backward_blocked() -> None:
    assert not can_transition("interview", "screening")


def test_reject_from_any_active_stage() -> None:
    for s in ("applied", "screening", "interview", "offer"):
        assert can_transition(s, "rejected")


def test_terminal_stages_cannot_move() -> None:
    assert not can_transition("hired", "rejected")
    assert not can_transition("rejected", "applied")


def test_next_stage() -> None:
    assert next_stage("applied") == "screening"
    assert next_stage("offer") == "hired"
    assert next_stage("hired") is None

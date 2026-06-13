"""Recruitment pipeline rules — pure, testable."""

STAGES = ["applied", "screening", "interview", "offer", "hired", "rejected"]
_PIPELINE = ["applied", "screening", "interview", "offer", "hired"]


def can_transition(current: str, target: str) -> bool:
    """A candidate may move one step forward along the pipeline, or be
    rejected from any non-terminal stage. No backward moves or skips."""
    if current in ("hired", "rejected"):
        return False  # terminal
    if target == "rejected":
        return True
    if current in _PIPELINE and target in _PIPELINE:
        return _PIPELINE.index(target) == _PIPELINE.index(current) + 1
    return False


def next_stage(current: str) -> str | None:
    if current in _PIPELINE and current != "hired":
        return _PIPELINE[_PIPELINE.index(current) + 1]
    return None

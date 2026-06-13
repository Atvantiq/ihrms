"""Recruitment pipeline rules — pure, testable."""

from dataclasses import dataclass

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


@dataclass(frozen=True)
class CriterionScore:
    criterion: str
    average: float
    count: int


@dataclass(frozen=True)
class ScorecardAgg:
    criteria: list[CriterionScore]
    overall: float
    total_scores: int


def aggregate_scorecard(scores: list[tuple[str, int]]) -> ScorecardAgg:
    """Aggregate per-criterion interview scores into a candidate scorecard.

    `scores` is a list of (criterion, score) pairs (score 1-5). Returns the
    per-criterion average (rounded to 0.1), the count behind each, and an
    overall average across all scores. Empty input -> zeroed scorecard.
    """
    by_criterion: dict[str, list[int]] = {}
    for criterion, score in scores:
        by_criterion.setdefault(criterion, []).append(score)

    criteria = [
        CriterionScore(criterion=crit, average=round(sum(vals) / len(vals), 1), count=len(vals))
        for crit, vals in sorted(by_criterion.items())
    ]
    all_scores = [score for _, score in scores]
    overall = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0
    return ScorecardAgg(criteria=criteria, overall=overall, total_scores=len(all_scores))

"""Golden tests for the Pulse ranking core (pure, no DB)."""

from app.contexts.pulse.service import Decision, rank_decisions, severity_for_count


def _d(kind: str, severity: str, count: int) -> Decision:
    return Decision(
        kind=kind,
        severity=severity,  # type: ignore[arg-type]
        icon="•",
        title=kind,
        detail="",
        action_label="Open",
        action_href="/",
        count=count,
    )


class TestSeverityForCount:
    def test_below_medium_is_low(self) -> None:
        assert severity_for_count(0, high_at=5) == "low"

    def test_one_is_medium(self) -> None:
        assert severity_for_count(1, high_at=5) == "medium"

    def test_reaching_threshold_is_high(self) -> None:
        assert severity_for_count(5, high_at=5) == "high"
        assert severity_for_count(9, high_at=5) == "high"

    def test_custom_medium_floor(self) -> None:
        assert severity_for_count(2, high_at=10, medium_at=3) == "low"
        assert severity_for_count(3, high_at=10, medium_at=3) == "medium"


class TestRankDecisions:
    def test_high_before_medium_before_low(self) -> None:
        ranked = rank_decisions([
            _d("c", "low", 99),
            _d("b", "medium", 1),
            _d("a", "high", 1),
        ])
        assert [d.kind for d in ranked] == ["a", "b", "c"]

    def test_within_tier_higher_count_first(self) -> None:
        ranked = rank_decisions([
            _d("small", "high", 2),
            _d("big", "high", 20),
        ])
        assert [d.kind for d in ranked] == ["big", "small"]

    def test_stable_within_same_severity_and_count(self) -> None:
        ranked = rank_decisions([
            _d("first", "medium", 3),
            _d("second", "medium", 3),
        ])
        assert [d.kind for d in ranked] == ["first", "second"]

    def test_empty(self) -> None:
        assert rank_decisions([]) == []

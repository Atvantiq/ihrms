"""Golden tests for interview scorecard aggregation."""

from app.contexts.recruitment.service import aggregate_scorecard


def test_empty_scorecard() -> None:
    agg = aggregate_scorecard([])
    assert agg.criteria == []
    assert agg.overall == 0.0
    assert agg.total_scores == 0


def test_per_criterion_average_and_overall() -> None:
    scores = [
        ("Technical", 4),
        ("Technical", 5),
        ("Communication", 3),
        ("Culture", 4),
    ]
    agg = aggregate_scorecard(scores)
    by = {c.criterion: c for c in agg.criteria}
    assert by["Technical"].average == 4.5
    assert by["Technical"].count == 2
    assert by["Communication"].average == 3.0
    # overall = (4+5+3+4)/4 = 4.0
    assert agg.overall == 4.0
    assert agg.total_scores == 4
    # criteria are sorted alphabetically
    assert [c.criterion for c in agg.criteria] == ["Communication", "Culture", "Technical"]


def test_rounding_to_one_decimal() -> None:
    # (5+4+4)/3 = 4.333 -> 4.3
    agg = aggregate_scorecard([("X", 5), ("X", 4), ("X", 4)])
    assert agg.criteria[0].average == 4.3
    assert agg.overall == 4.3

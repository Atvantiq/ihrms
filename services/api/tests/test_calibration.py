"""Golden tests for the forced-distribution calibration helper."""

from decimal import Decimal

from app.contexts.performance.service import FORCED_CURVE, calibrate


def test_empty_cohort_all_zero() -> None:
    buckets = calibrate([])
    assert [b.rating for b in buckets] == [5, 4, 3, 2, 1]
    assert all(b.count == 0 and b.actual_pct == Decimal(0) for b in buckets)
    # delta = 0 − target = −target
    assert buckets[0].delta_pct == -FORCED_CURVE[5]


def test_distribution_and_delta() -> None:
    # 10 reviews: 1×5, 2×4, 4×3, 2×2, 1×1 — exactly the default curve
    ratings = [5, 4, 4, 3, 3, 3, 3, 2, 2, 1]
    buckets = {b.rating: b for b in calibrate(ratings)}
    assert buckets[3].count == 4
    assert buckets[3].actual_pct == Decimal("40.0")
    assert buckets[3].target_pct == Decimal("40")
    # matches the curve exactly -> deltas ~0
    assert all(abs(b.delta_pct) <= Decimal("0.1") for b in buckets.values())


def test_top_heavy_cohort_flags_positive_delta() -> None:
    # everyone a 5 -> over-represented at the top, under everywhere else
    buckets = {b.rating: b for b in calibrate([5, 5, 5, 5])}
    assert buckets[5].actual_pct == Decimal("100.0")
    assert buckets[5].delta_pct == Decimal("90.0")   # 100 − 10
    assert buckets[3].delta_pct == Decimal("-40")    # 0 − 40

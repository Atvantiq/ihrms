"""Performance logic — rating bands, 9-box, suggested increment (pure)."""

from dataclasses import dataclass
from decimal import Decimal

from app.core.money import D, round_rupee

# Default forced-distribution target (% of cohort) per rating 5..1 — a mild bell.
FORCED_CURVE: dict[int, Decimal] = {
    5: Decimal("10"),
    4: Decimal("20"),
    3: Decimal("40"),
    2: Decimal("20"),
    1: Decimal("10"),
}

# Suggested annual increment % by final rating (1–5). Guardrailed by HR later.
INCREMENT_PCT_BY_RATING = {
    5: Decimal("15"),
    4: Decimal("10"),
    3: Decimal("6"),
    2: Decimal("3"),
    1: Decimal("0"),
}

RATING_LABEL = {
    5: "Outstanding", 4: "Exceeds", 3: "Meets", 2: "Below", 1: "Unsatisfactory",
}


def band(score: int) -> int:
    """Collapse a 1–5 score into a 3-band axis (1=low, 2=mid, 3=high) for the 9-box."""
    if score <= 2:
        return 1
    if score == 3:
        return 2
    return 3


def nine_box(performance: int, potential: int) -> int:
    """9-box cell 1..9 from performance & potential (1–5 each).
    Cell = (potential_band-1)*3 + performance_band, so 9 = high/high (star)."""
    return (band(potential) - 1) * 3 + band(performance)


def nine_box_label(cell: int) -> str:
    return {
        9: "Star", 8: "High Potential", 7: "Enigma",
        6: "Core Player", 5: "Key Player", 4: "Inconsistent",
        3: "Trusted Professional", 2: "Effective", 1: "Risk",
    }.get(cell, "—")


def suggested_increment_pct(rating: int) -> Decimal:
    return INCREMENT_PCT_BY_RATING.get(rating, D(0))


def apply_increment(current_ctc: Decimal, pct: Decimal) -> Decimal:
    """New CTC after an increment percentage (rounded to the rupee)."""
    return round_rupee(current_ctc * (D(1) + pct / D(100)))


@dataclass(frozen=True)
class CalibrationBucket:
    rating: int
    label: str
    count: int
    actual_pct: Decimal
    target_pct: Decimal
    delta_pct: Decimal  # actual − target; positive = over-represented vs the curve


def calibrate(
    ratings: list[int], target_curve: dict[int, Decimal] | None = None
) -> list[CalibrationBucket]:
    """Compare a cohort's rating spread against a forced-distribution target.

    Returns one bucket per rating 5..1 with the count, the actual share, the
    target share and the delta. `ratings` may be empty (all shares 0).
    """
    curve = target_curve or FORCED_CURVE
    total = len(ratings)
    out: list[CalibrationBucket] = []
    for r in (5, 4, 3, 2, 1):
        count = sum(1 for x in ratings if x == r)
        actual = (
            Decimal(0) if total == 0
            else (Decimal(count) / Decimal(total) * Decimal(100)).quantize(Decimal("0.1"))
        )
        target = curve.get(r, Decimal(0))
        out.append(
            CalibrationBucket(
                rating=r, label=RATING_LABEL[r], count=count,
                actual_pct=actual, target_pct=target, delta_pct=actual - target,
            )
        )
    return out

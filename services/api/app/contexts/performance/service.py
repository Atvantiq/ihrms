"""Performance logic — rating bands, 9-box, suggested increment (pure)."""

from decimal import Decimal

from app.core.money import D, round_rupee

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

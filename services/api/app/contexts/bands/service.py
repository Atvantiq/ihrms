"""Band-fit check (pure)."""

from typing import Literal

from app.core.money import Money

Fit = Literal["within", "below", "above"]


def band_fit(ctc: Money, min_ctc: Money, max_ctc: Money) -> Fit:
    """Where an employee's CTC sits relative to their band range."""
    if ctc < min_ctc:
        return "below"
    if ctc > max_ctc:
        return "above"
    return "within"

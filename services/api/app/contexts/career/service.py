"""Pure career-ladder helpers."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Rung:
    level_id: str
    name: str
    rank: int


def next_rung(rungs: list[Rung], current_rank: int) -> Rung | None:
    """The next rung up from `current_rank` on a track (lowest rank above it),
    or None if already at the top. `rungs` need not be pre-sorted."""
    above = [r for r in rungs if r.rank > current_rank]
    return min(above, key=lambda r: r.rank) if above else None

"""Pure succession helpers — bench strength from a candidate set."""

from dataclasses import dataclass

READINESS = ("ready_now", "1_2_years", "3_5_years")


@dataclass(frozen=True)
class Bench:
    ready_now: int
    pipeline: int   # candidates not yet ready (1-2y / 3-5y)
    total: int
    status: str     # covered | developing | at_risk


def bench_strength(readiness: list[str]) -> Bench:
    """Summarise succession coverage for a position.

    'covered' when at least one successor is ready now, 'developing' when the
    bench has people but none ready yet, 'at_risk' when the bench is empty.
    """
    ready_now = sum(1 for r in readiness if r == "ready_now")
    total = len(readiness)
    pipeline = total - ready_now
    if ready_now >= 1:
        status = "covered"
    elif total > 0:
        status = "developing"
    else:
        status = "at_risk"
    return Bench(ready_now=ready_now, pipeline=pipeline, total=total, status=status)

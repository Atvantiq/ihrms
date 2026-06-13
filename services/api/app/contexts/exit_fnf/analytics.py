"""Pure exit-analytics derivations (no DB) — testable under golden tests.

Attrition rate, exits by reason, exits by month and average tenure at exit are
all computed from the case set + the active headcount. Decimal-only for the
percentage so it composes with the rest of the money/rate stack.
"""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

ZERO = Decimal(0)


@dataclass(frozen=True)
class ExitCaseStat:
    reason: str | None
    last_working_day: date
    tenure_days: int


@dataclass(frozen=True)
class ExitAnalytics:
    total_exits: int
    by_reason: dict[str, int] = field(default_factory=dict)
    by_month: dict[str, int] = field(default_factory=dict)
    avg_tenure_days: int = 0
    attrition_rate_pct: Decimal = ZERO


def compute_exit_analytics(
    cases: list[ExitCaseStat], active_headcount: int
) -> ExitAnalytics:
    """Aggregate a set of exit cases into attrition metrics.

    `attrition_rate_pct` is exits / (active headcount + exits) — i.e. exits as a
    share of the population that was at risk, rounded to one decimal place.
    """
    if not cases:
        return ExitAnalytics(total_exits=0)

    by_reason = dict(Counter((c.reason or "unspecified") for c in cases))
    by_month = dict(Counter(c.last_working_day.strftime("%Y-%m") for c in cases))
    avg_tenure = round(sum(c.tenure_days for c in cases) / len(cases))

    base = active_headcount + len(cases)
    rate = ZERO if base == 0 else (
        Decimal(len(cases)) / Decimal(base) * Decimal(100)
    ).quantize(Decimal("0.1"))

    return ExitAnalytics(
        total_exits=len(cases),
        by_reason=dict(sorted(by_reason.items(), key=lambda kv: -kv[1])),
        by_month=dict(sorted(by_month.items())),
        avg_tenure_days=avg_tenure,
        attrition_rate_pct=rate,
    )

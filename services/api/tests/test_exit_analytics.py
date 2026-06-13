"""Golden tests for the pure exit-analytics derivations."""

from datetime import date
from decimal import Decimal

from app.contexts.exit_fnf.analytics import ExitCaseStat, compute_exit_analytics


def _case(reason: str | None, lwd: date, tenure: int) -> ExitCaseStat:
    return ExitCaseStat(reason=reason, last_working_day=lwd, tenure_days=tenure)


def test_empty_set() -> None:
    a = compute_exit_analytics([], 100)
    assert a.total_exits == 0
    assert a.attrition_rate_pct == Decimal(0)
    assert a.by_reason == {} and a.by_month == {}


def test_aggregates_and_rate() -> None:
    cases = [
        _case("Better opportunity", date(2026, 1, 31), 730),
        _case("Better opportunity", date(2026, 2, 28), 365),
        _case("Relocation", date(2026, 2, 15), 1095),
    ]
    a = compute_exit_analytics(cases, 97)
    assert a.total_exits == 3
    # reasons sorted by frequency desc
    assert list(a.by_reason.items())[0] == ("Better opportunity", 2)
    assert a.by_reason["Relocation"] == 1
    # months sorted ascending
    assert list(a.by_month.keys()) == ["2026-01", "2026-02"]
    assert a.by_month["2026-02"] == 2
    # avg tenure = round((730+365+1095)/3) = 730
    assert a.avg_tenure_days == 730
    # attrition = 3 / (97 + 3) = 3.0%
    assert a.attrition_rate_pct == Decimal("3.0")


def test_unspecified_reason_bucket() -> None:
    a = compute_exit_analytics([_case(None, date(2026, 3, 1), 200)], 0)
    assert a.by_reason == {"unspecified": 1}
    # base = 0 + 1 -> 100%
    assert a.attrition_rate_pct == Decimal("100.0")

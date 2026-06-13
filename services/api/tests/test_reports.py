"""Golden tests for report helpers."""

from decimal import Decimal

from app.contexts.reports.service import attrition_rate, to_csv


def test_to_csv_header_and_rows() -> None:
    csv = to_csv(
        ["dept", "count"],
        [{"dept": "IT", "count": 5}, {"dept": "HR", "count": 2}],
    )
    lines = csv.strip().splitlines()
    assert lines[0] == "dept,count"
    assert lines[1] == "IT,5"
    assert lines[2] == "HR,2"


def test_to_csv_handles_none_and_missing() -> None:
    csv = to_csv(["a", "b"], [{"a": None}])
    assert csv.strip().splitlines()[1] == ","


def test_to_csv_quotes_commas() -> None:
    csv = to_csv(["name"], [{"name": "Doe, John"}])
    assert '"Doe, John"' in csv


def test_attrition_rate() -> None:
    assert attrition_rate(5, 100) == Decimal("5.0")
    assert attrition_rate(3, 40) == Decimal("7.5")


def test_attrition_rate_zero_headcount() -> None:
    assert attrition_rate(0, 0) == Decimal(0)

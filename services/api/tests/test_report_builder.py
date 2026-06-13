"""Golden tests for the whitelist-driven custom report builder."""

import pytest

from app.contexts.reports.builder import DATASETS, MAX_LIMIT, build_query


def test_default_columns_when_none_given() -> None:
    sql, params, cols = build_query("employees", [], [], 50)
    assert cols == list(DATASETS["employees"].columns)
    assert params == {}
    assert sql.startswith("select ")
    assert "from ihrms.v_employee" in sql
    assert sql.rstrip().endswith("limit 50")


def test_selected_columns_and_filter_bind_value() -> None:
    sql, params, cols = build_query(
        "employees", ["name", "department"],
        [{"field": "department", "op": "eq", "value": "Engineering"}], 100,
    )
    assert cols == ["name", "department"]
    # value is a bound parameter, never inlined
    assert params == {"p0": "Engineering"}
    assert "e.department_c = :p0" in sql
    assert "Engineering" not in sql


def test_contains_wraps_value_with_wildcards() -> None:
    _, params, _ = build_query(
        "employees", ["name"],
        [{"field": "designation", "op": "contains", "value": "eng"}],
    )
    assert params == {"p0": "%eng%"}


def test_unknown_dataset_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown dataset"):
        build_query("secrets", [], [])


def test_unknown_column_rejected() -> None:
    # a SQL-injection-shaped column name is just an unknown key
    with pytest.raises(ValueError, match="Unknown column"):
        build_query("employees", ["name; drop table employees"], [])


def test_unknown_filter_field_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown filter field"):
        build_query("employees", [], [{"field": "salary", "op": "eq", "value": "1"}])


def test_disallowed_operator_rejected() -> None:
    # 'contains' is not allowed on the date_of_joining filter
    with pytest.raises(ValueError, match="not allowed"):
        build_query(
            "employees", [], [{"field": "date_of_joining", "op": "contains", "value": "x"}]
        )


def test_limit_is_clamped() -> None:
    sql, _, _ = build_query("employees", [], [], 999999)
    assert sql.rstrip().endswith(f"limit {MAX_LIMIT}")


def test_base_with_static_where_uses_and() -> None:
    # payslips_latest already has a WHERE; an extra filter must AND onto it
    sql, params, _ = build_query(
        "payslips_latest", ["name", "net_pay"],
        [{"field": "net_pay", "op": "gte", "value": "50000"}],
    )
    assert " and p.net_pay >= :p0" in sql
    assert params == {"p0": "50000"}

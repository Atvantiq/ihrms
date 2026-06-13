"""Golden tests for the salary-component resolver."""

from app.contexts.salary_config.service import Component, resolve_earnings
from app.core.money import D

STANDARD = [
    Component("BASIC", "Basic", "earning", "pct_ctc", D(40)),
    Component("HRA", "HRA", "earning", "pct_basic", D(50)),
    Component("SPECIAL", "Special Allowance", "earning", "balancing", D(0)),
]


def test_matches_builtin_split() -> None:
    # 12L CTC -> 100000/mo; employer PF on basic 40000 (capped 15000) = 1800
    # basic 40000, hra 20000, special = 100000-1800-60000 = 38200, gross 98200
    lines, gross = resolve_earnings(D(100000), STANDARD, employer_pf=D(1800))
    by = {line.code: line.amount for line in lines}
    assert by["BASIC"] == D(40000)
    assert by["HRA"] == D(20000)
    assert by["SPECIAL"] == D(38200)
    assert gross == D(98200)


def test_fixed_component() -> None:
    comps = [
        Component("BASIC", "Basic", "earning", "pct_ctc", D(50)),
        Component("LTA", "LTA", "earning", "fixed", D(5000)),
        Component("SPECIAL", "Special", "earning", "balancing", D(0)),
    ]
    lines, gross = resolve_earnings(D(100000), comps, employer_pf=D(0))
    by = {line.code: line.amount for line in lines}
    assert by["BASIC"] == D(50000)
    assert by["LTA"] == D(5000)
    assert by["SPECIAL"] == D(45000)  # 100000 - 50000 - 5000
    assert gross == D(100000)


def test_balancing_never_negative() -> None:
    comps = [
        Component("BASIC", "Basic", "earning", "pct_ctc", D(90)),
        Component("BONUS", "Bonus", "earning", "fixed", D(50000)),
        Component("SPECIAL", "Special", "earning", "balancing", D(0)),
    ]
    lines, _ = resolve_earnings(D(100000), comps)
    by = {line.code: line.amount for line in lines}
    assert by["SPECIAL"] == D(0)  # 100000 - 90000 - 50000 < 0 -> floored

"""Golden tests for payroll outputs — statutory totals + GL journal balance."""

from app.contexts.payroll.outputs import gl_journal, statutory_totals
from app.core.money import D


def _slip(gross: str, net: str, ded: dict, empr: dict) -> dict:
    return {
        "gross": D(gross),
        "net_pay": D(net),
        "earnings": {},
        "deductions": {k: D(v) for k, v in ded.items()},
        "employer_contributions": {k: D(v) for k, v in empr.items()},
    }


PAYSLIPS = [
    _slip("148200", "134008",
          {"pf_employee": "1800", "pt": "200", "tds": "12192"},
          {"pf_employer": "1800"}),
    _slip("20000", "18050",  # 20000 - (1800 pf + 150 esi) = 18050
          {"pf_employee": "1800", "pt": "0", "esi_employee": "150"},
          {"pf_employer": "1800", "esi_employer": "650"}),
]


def test_statutory_totals() -> None:
    s = statutory_totals(PAYSLIPS)
    assert s.pf_employee == D(3600)
    assert s.pf_employer == D(3600)
    assert s.pf_total == D(7200)
    assert s.esi_employee == D(150)
    assert s.esi_employer == D(650)
    assert s.tds == D(12192)


def test_gl_journal_balances() -> None:
    j = gl_journal(PAYSLIPS)
    assert j.balanced
    # debits = gross (168200) + employer PF (3600) + employer ESI (650)
    assert j.total_debit == D(172450)
    assert j.total_credit == D(172450)


def test_gl_has_liability_lines() -> None:
    j = gl_journal(PAYSLIPS)
    accounts = {line.account for line in j.lines}
    assert "Net pay payable (employees)" in accounts
    assert "PF payable" in accounts
    assert "TDS payable" in accounts
    assert "ESI payable" in accounts

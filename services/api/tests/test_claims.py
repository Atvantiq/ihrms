"""Golden test: payslip reimbursement earning is post-statutory."""

from app.contexts.payroll.salary import compute_payslip, derive_structure
from app.core.money import D


def test_reimbursement_adds_to_gross_and_net() -> None:
    s = derive_structure(D(1200000))
    base = compute_payslip(s)
    with_r = compute_payslip(s, reimbursements=D(3500))
    assert with_r.earnings["reimbursements"] == D(3500)
    assert with_r.gross == base.gross + D(3500)
    assert with_r.net_pay == base.net_pay + D(3500)
    assert with_r.total_deductions == base.total_deductions  # statutory unchanged


def test_no_reimbursement_key_when_zero() -> None:
    s = derive_structure(D(1200000))
    assert "reimbursements" not in compute_payslip(s).earnings

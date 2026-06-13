"""Golden tests for advance/loan recovery math + payslip integration."""

from app.contexts.advances.service import emi_for_month, remaining_after
from app.contexts.payroll.salary import compute_payslip, derive_structure
from app.core.money import D


class TestEmiForMonth:
    def test_full_emi_when_plenty_outstanding(self) -> None:
        assert emi_for_month(D(5000), D(20000)) == D(5000)

    def test_final_instalment_clears_remainder(self) -> None:
        # only 3000 left but EMI is 5000 -> recover just 3000
        assert emi_for_month(D(5000), D(3000)) == D(3000)

    def test_zero_when_nothing_outstanding(self) -> None:
        assert emi_for_month(D(5000), D(0)) == D(0)

    def test_zero_emi_recovers_nothing(self) -> None:
        assert emi_for_month(D(0), D(10000)) == D(0)


class TestRemainingAfter:
    def test_subtracts(self) -> None:
        assert remaining_after(D(20000), D(5000)) == D(15000)

    def test_never_negative(self) -> None:
        assert remaining_after(D(3000), D(5000)) == D(0)


class TestPayslipLoanRecovery:
    def test_loan_recovery_reduces_net(self) -> None:
        s = derive_structure(D(1200000))
        base = compute_payslip(s)
        with_loan = compute_payslip(s, loan_recovery=D(5000))
        assert with_loan.deductions["loan_recovery"] == D(5000)
        assert with_loan.net_pay == base.net_pay - D(5000)

    def test_no_recovery_key_when_zero(self) -> None:
        s = derive_structure(D(1200000))
        slip = compute_payslip(s)
        assert "loan_recovery" not in slip.deductions

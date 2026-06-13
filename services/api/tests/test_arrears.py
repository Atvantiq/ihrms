"""Golden tests for arrear math + payslip arrears earning."""

from datetime import date

from app.contexts.payroll.arrears import arrear_amount, retro_months
from app.contexts.payroll.salary import compute_payslip, derive_structure
from app.core.money import D


class TestRetroMonths:
    def test_two_months_back(self) -> None:
        assert retro_months(date(2026, 4, 1), date(2026, 6, 13)) == 2

    def test_same_month_is_zero(self) -> None:
        assert retro_months(date(2026, 6, 1), date(2026, 6, 13)) == 0

    def test_future_is_zero(self) -> None:
        assert retro_months(date(2026, 8, 1), date(2026, 6, 13)) == 0

    def test_crosses_year(self) -> None:
        assert retro_months(date(2025, 11, 1), date(2026, 2, 1)) == 3


class TestArrearAmount:
    def test_positive_raise(self) -> None:
        # +5000/mo for 3 months = 15000
        assert arrear_amount(D(50000), D(55000), 3) == D(15000)

    def test_negative_is_recovery(self) -> None:
        assert arrear_amount(D(55000), D(50000), 2) == D(-10000)

    def test_zero_months(self) -> None:
        assert arrear_amount(D(50000), D(60000), 0) == D(0)


class TestPayslipArrears:
    def test_arrears_add_to_gross_and_net(self) -> None:
        s = derive_structure(D(1200000))
        base = compute_payslip(s)
        with_arr = compute_payslip(s, arrears=D(20000))
        assert with_arr.earnings["arrears"] == D(20000)
        assert with_arr.gross == base.gross + D(20000)
        assert with_arr.net_pay == base.net_pay + D(20000)

    def test_arrears_do_not_change_statutory(self) -> None:
        s = derive_structure(D(1200000))
        base = compute_payslip(s)
        with_arr = compute_payslip(s, arrears=D(20000))
        # PF/PT/ESI unchanged — they were withheld in the original months
        assert with_arr.total_deductions == base.total_deductions

    def test_no_arrears_key_when_zero(self) -> None:
        s = derive_structure(D(1200000))
        assert "arrears" not in compute_payslip(s).earnings

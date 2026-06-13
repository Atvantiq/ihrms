"""Golden tests for overtime pay math + payslip overtime earning."""

from decimal import Decimal

from app.contexts.overtime.service import hourly_rate, ot_pay
from app.contexts.payroll.salary import compute_payslip, derive_structure
from app.core.money import D


class TestHourlyRate:
    def test_gross_over_standard_hours(self) -> None:
        # 96000 gross / (30 days x 8h) = 400/h
        assert hourly_rate(D(96000), 30) == D(400)

    def test_zero_working_days(self) -> None:
        assert hourly_rate(D(96000), 0) == D(0)


class TestOtPay:
    def test_double_rate(self) -> None:
        # 5h x 2.0 x 400 = 4000
        assert ot_pay(D(5), Decimal("2.0"), D(400)) == D(4000)

    def test_one_and_half_rate(self) -> None:
        assert ot_pay(D(4), Decimal("1.5"), D(400)) == D(2400)

    def test_zero_hours(self) -> None:
        assert ot_pay(D(0), Decimal("2.0"), D(400)) == D(0)


class TestPayslipOvertime:
    def test_overtime_adds_to_gross_and_net(self) -> None:
        s = derive_structure(D(1200000))
        base = compute_payslip(s)
        with_ot = compute_payslip(s, overtime=D(4000))
        assert with_ot.earnings["overtime"] == D(4000)
        assert with_ot.gross == base.gross + D(4000)
        assert with_ot.net_pay == base.net_pay + D(4000)

    def test_no_overtime_key_when_zero(self) -> None:
        s = derive_structure(D(1200000))
        assert "overtime" not in compute_payslip(s).earnings

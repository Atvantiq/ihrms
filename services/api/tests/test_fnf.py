"""Golden tests for the Full-and-Final settlement engine."""

from datetime import date

from app.contexts.exit_fnf.fnf import (
    completed_years,
    compute_fnf,
    gratuity,
    leave_encashment,
    notice_recovery,
)
from app.core.money import D


class TestCompletedYears:
    def test_exact_years(self) -> None:
        assert completed_years(date(2018, 1, 1), date(2026, 1, 1)) == 8

    def test_rounds_up_above_6_months(self) -> None:
        # 5 years 7 months -> 6
        assert completed_years(date(2020, 1, 1), date(2025, 8, 1)) == 6

    def test_rounds_down_below_6_months(self) -> None:
        # 5 years 4 months -> 5
        assert completed_years(date(2020, 1, 1), date(2025, 5, 1)) == 5


class TestGratuity:
    def test_below_5_years_is_zero(self) -> None:
        assert gratuity(D(50000), date(2023, 1, 1), date(2026, 1, 1)) == D(0)

    def test_standard_formula(self) -> None:
        # 8 years, last basic 50000: 15*50000*8/26 = 230,769.23 -> 230769 (whole rupee)
        assert gratuity(D(50000), date(2018, 1, 1), date(2026, 1, 1)) == D(230769)

    def test_under_cap(self) -> None:
        # 6 years, basic 30000: 15*30000*6/26 = 103,846.15 -> 103846
        assert gratuity(D(30000), date(2020, 1, 1), date(2026, 1, 1)) == D(103846)

    def test_cap_applies(self) -> None:
        # 12 years, basic 300000: 15*300000*12/26 = 2,076,923 -> capped at 20L
        assert gratuity(D(300000), date(2014, 1, 1), date(2026, 1, 1)) == D(2000000)


class TestLeaveEncashment:
    def test_encashment(self) -> None:
        # 20 days, basic 52000: 20 * (52000/26) = 40000
        assert leave_encashment(D(20), D(52000)) == D(40000)

    def test_zero_when_no_balance(self) -> None:
        assert leave_encashment(D(0), D(50000)) == D(0)


class TestNoticeRecovery:
    def test_shortfall_recovered(self) -> None:
        # required 60, served 30 -> 30 days shortfall × (gross 60000/30) = 60000
        assert notice_recovery(60, 30, D(60000)) == D(60000)

    def test_no_recovery_when_served(self) -> None:
        assert notice_recovery(60, 60, D(60000)) == D(0)
        assert notice_recovery(30, 45, D(60000)) == D(0)


class TestComputeFnF:
    def test_full_settlement_balances(self) -> None:
        f = compute_fnf(
            last_basic=D(40000), monthly_gross=D(100000),
            doj=date(2018, 6, 1), lwd=date(2026, 6, 30),
            unused_leave_days=D(12), pending_salary=D(100000),
            notice_required_days=60, notice_served_days=60,
            other_recoveries=D(5000),
        )
        assert f.gratuity > 0  # 8 years
        assert f.leave_encashment == leave_encashment(D(12), D(40000))
        assert f.notice_recovery == D(0)  # served fully
        assert f.net_settlement == f.earnings - f.deductions
        assert f.deductions == D(5000)

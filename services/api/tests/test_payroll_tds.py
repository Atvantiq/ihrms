"""Golden tests for the TDS / income-tax engine (FY2025-26)."""

import pytest

from app.contexts.payroll.tds import compute_annual_tax, monthly_tds
from app.core.money import D


class TestNewRegime:
    def test_below_rebate_limit_is_zero(self) -> None:
        # 12.75L gross - 75k std = 12L taxable -> 87A rebate -> nil
        assert compute_annual_tax(D(1275000), regime="new") == D(0)

    def test_exactly_at_threshold_nil(self) -> None:
        assert compute_annual_tax(D(1200000), regime="new") == D(0)

    def test_15L_gross(self) -> None:
        # taxable 14.25L: 5%*4L + 10%*4L + 15%*2.25L = 20000+40000+33750 = 93750
        # + 4% cess = 97500
        assert compute_annual_tax(D(1500000), regime="new") == D(97500)

    def test_marginal_relief_just_above_threshold(self) -> None:
        # gross 12,85,000 -> taxable 12,10,000; slab tax 61,500 but marginal
        # relief caps tax to (12,10,000 - 12,00,000) = 10,000; +4% cess = 10,400
        assert compute_annual_tax(D(1285000), regime="new") == D(10400)

    def test_high_income_30_pct(self) -> None:
        # taxable 30L - covers all bands incl 30%
        tax = compute_annual_tax(D(3075000), regime="new")  # taxable 30L
        # 0 + 20000 + 40000 + 60000 + 80000 + 100000 + 30%*6L(180000) = 480000
        # +4% cess = 499200
        assert tax == D(499200)


class TestOldRegime:
    def test_10L_no_deductions(self) -> None:
        # taxable 9.5L: 5%*2.5L + 20%*4.5L = 12500 + 90000 = 102500; +4% = 106600
        assert compute_annual_tax(D(1000000), regime="old") == D(106600)

    def test_80c_reduces_tax(self) -> None:
        with_ded = compute_annual_tax(
            D(1000000), regime="old", chapter_via_deductions=D(150000)
        )
        without = compute_annual_tax(D(1000000), regime="old")
        assert with_ded < without

    def test_under_5L_taxable_rebate(self) -> None:
        # gross 5.5L - 50k std = 5L taxable -> 87A rebate -> nil
        assert compute_annual_tax(D(550000), regime="old") == D(0)


class TestMonthlyTDS:
    def test_monthly_is_annual_over_12(self) -> None:
        # monthly gross 125000 -> annual 15L -> annual tax 97500 -> /12 = 8125
        assert monthly_tds(D(125000), regime="new") == D(8125)

    def test_low_earner_no_tds(self) -> None:
        assert monthly_tds(D(50000), regime="new") == D(0)  # 6L annual, nil

    @pytest.mark.parametrize("regime", ["new", "old"])
    def test_never_negative(self, regime: str) -> None:
        assert monthly_tds(D(20000), regime=regime) >= D(0)

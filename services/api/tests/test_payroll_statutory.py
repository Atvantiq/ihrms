"""Golden tests for India statutory payroll math — deterministic, no DB.

These pin the exact rupee outcomes so any change to the rules is deliberate.
"""

from decimal import Decimal

import pytest

from app.contexts.payroll.salary import compute_payslip, derive_structure
from app.contexts.payroll.statutory import compute_esi, compute_pf, compute_pt
from app.core.money import D


class TestPF:
    def test_basic_below_ceiling(self) -> None:
        pf = compute_pf(D(12000))
        assert pf.employee == D(1440)  # 12% of 12000
        assert pf.employer == D(1440)

    def test_basic_above_ceiling_is_capped(self) -> None:
        pf = compute_pf(D(50000))
        assert pf.pf_wage == D(15000)
        assert pf.employee == D(1800)  # 12% of 15000 ceiling
        assert pf.employer == D(1800)

    def test_employer_split_pension_and_pf(self) -> None:
        pf = compute_pf(D(50000))
        # EPS = 8.33% of 15000 = 1250 (rounded), remainder to EPF
        assert pf.employer_pension == D(1250)
        assert pf.employer_pf == pf.employer - pf.employer_pension

    def test_voluntary_full_basic(self) -> None:
        pf = compute_pf(D(50000), voluntary_full_basic=True)
        assert pf.pf_wage == D(50000)
        assert pf.employee == D(6000)


class TestESI:
    def test_applies_within_ceiling(self) -> None:
        esi = compute_esi(D(20000))
        assert esi.applicable is True
        assert esi.employee == D(150)  # ceil(0.75% of 20000 = 150)
        assert esi.employer == D(650)  # ceil(3.25% of 20000 = 650)

    def test_rounds_up_to_next_rupee(self) -> None:
        esi = compute_esi(D(18000))
        assert esi.employee == D(135)  # 0.75% of 18000 = 135 exactly
        esi2 = compute_esi(D(17999))
        assert esi2.employee == Decimal("135")  # ceil(134.9925)

    def test_not_applicable_above_ceiling(self) -> None:
        esi = compute_esi(D(21001))
        assert esi.applicable is False
        assert esi.employee == D(0)

    def test_boundary_exactly_at_ceiling_applies(self) -> None:
        assert compute_esi(D(21000)).applicable is True


class TestPT:
    def test_exempt_at_or_below_threshold(self) -> None:
        assert compute_pt(D(25000)) == D(0)

    def test_charged_above_threshold(self) -> None:
        assert compute_pt(D(25001)) == D(200)


class TestDeriveStructure:
    def test_components_sum_consistent(self) -> None:
        s = derive_structure(D(1200000))  # 12L CTC -> 100000/mo
        assert s.basic == D(40000)  # 40% of 100000
        assert s.hra == D(20000)  # 50% of basic
        # gross = monthly_ctc - employer_pf (1800) = 98200
        assert s.gross == D(98200)


class TestPayslip:
    def test_full_month_no_lop(self) -> None:
        s = derive_structure(D(1200000))
        slip = compute_payslip(s)
        assert slip.gross == D(98200)
        assert slip.deductions["pf_employee"] == D(1800)  # basic 40000 capped
        assert slip.deductions["pt"] == D(200)
        assert "esi_employee" not in slip.deductions  # gross > 21000
        assert slip.total_deductions == D(2000)
        assert slip.net_pay == D(96200)

    def test_lop_prorates_earnings(self) -> None:
        s = derive_structure(D(1200000))
        slip = compute_payslip(s, working_days=30, lop_days=D(3))
        # 27/30 of each component
        assert slip.earnings["basic"] == D(36000)
        assert slip.earnings["hra"] == D(18000)
        assert slip.net_pay < D(96200)  # less than full-month net

    def test_low_earner_gets_esi(self) -> None:
        s = derive_structure(D(240000))  # 20000/mo -> ESI applies
        slip = compute_payslip(s)
        assert "esi_employee" in slip.deductions
        assert slip.deductions["esi_employee"] > 0

    def test_invalid_lop_raises(self) -> None:
        s = derive_structure(D(1200000))
        with pytest.raises(ValueError, match="lop_days"):
            compute_payslip(s, working_days=30, lop_days=D(31))

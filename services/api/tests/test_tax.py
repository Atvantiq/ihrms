"""Golden tests for Chapter VI-A eligible-deduction math + FY label."""

from datetime import date

from app.contexts.tax.api import current_fy
from app.contexts.tax.service import eligible_deduction, section_cap
from app.core.money import D


class TestEligibleDeduction:
    def test_caps_each_section(self) -> None:
        # 80C declared 200k but capped at 150k
        assert eligible_deduction({"80C": D(200000)}) == D(150000)

    def test_under_cap_passes_through(self) -> None:
        assert eligible_deduction({"80C": D(80000)}) == D(80000)

    def test_sums_across_sections(self) -> None:
        items = {"80C": D(150000), "80CCD1B": D(50000), "80D": D(25000)}
        assert eligible_deduction(items) == D(225000)

    def test_uncapped_section_passes_full(self) -> None:
        # 80E has cap 0 = uncapped
        assert section_cap("80E") == D(0)
        assert eligible_deduction({"80E": D(90000)}) == D(90000)

    def test_unknown_section_ignored(self) -> None:
        assert eligible_deduction({"made_up": D(99999)}) == D(0)

    def test_zero_and_negative_ignored(self) -> None:
        assert eligible_deduction({"80C": D(0), "80D": D(-5)}) == D(0)


class TestFinancialYear:
    def test_after_april_is_current_year(self) -> None:
        assert current_fy(date(2026, 6, 13)) == "2026-27"

    def test_before_april_is_previous_year(self) -> None:
        assert current_fy(date(2026, 2, 1)) == "2025-26"

    def test_april_first_boundary(self) -> None:
        assert current_fy(date(2026, 4, 1)) == "2026-27"

"""India income-tax (TDS on salary) engine — FY 2025-26 / AY 2026-27.

Pure, Decimal-only, golden-tested. Computes annual tax for both regimes
(new = default), then the monthly TDS. Implements: slab tax, standard
deduction, §87A rebate, marginal relief (new regime, near ₹12L), and 4%
health & education cess. Chapter VI-A deductions (80C etc.) apply to the
OLD regime only, sourced from the employee's declarations.

NOT tax advice — statutory packs are versioned (blueprint). Real TDS spreads
the projected liability over remaining months and trues up; this module uses
annual_tax / 12 as the monthly figure (a standard, slightly simplified basis).
"""

from decimal import Decimal

from app.core.money import D, round_rupee

CESS_RATE = Decimal("0.04")  # health & education cess on tax

# New regime (Budget 2025, FY2025-26): (upper_bound, rate). None = no ceiling.
SLABS_NEW: list[tuple[Decimal | None, Decimal]] = [
    (D(400000), Decimal("0.00")),
    (D(800000), Decimal("0.05")),
    (D(1200000), Decimal("0.10")),
    (D(1600000), Decimal("0.15")),
    (D(2000000), Decimal("0.20")),
    (D(2400000), Decimal("0.25")),
    (None, Decimal("0.30")),
]
STD_DEDUCTION_NEW = D(75000)
REBATE_87A_NEW_LIMIT = D(1200000)  # taxable <= this → tax nil (then marginal relief)

# Old regime (unchanged): slabs, ₹50k std deduction, §87A up to ₹5L.
SLABS_OLD: list[tuple[Decimal | None, Decimal]] = [
    (D(250000), Decimal("0.00")),
    (D(500000), Decimal("0.05")),
    (D(1000000), Decimal("0.20")),
    (None, Decimal("0.30")),
]
STD_DEDUCTION_OLD = D(50000)
REBATE_87A_OLD_LIMIT = D(500000)


def _slab_tax(taxable: Decimal, slabs: list[tuple[Decimal | None, Decimal]]) -> Decimal:
    tax = D(0)
    lower = D(0)
    for upper, rate in slabs:
        if upper is None or taxable <= upper:
            tax += (taxable - lower) * rate
            break
        tax += (upper - lower) * rate
        lower = upper
    return tax


def compute_annual_tax(
    annual_gross: Decimal,
    *,
    regime: str = "new",
    chapter_via_deductions: Decimal | None = None,
) -> Decimal:
    """Annual income tax incl. cess. `chapter_via_deductions` (80C etc.)
    applies to the OLD regime only."""
    if regime == "new":
        taxable = annual_gross - STD_DEDUCTION_NEW
        taxable = max(taxable, D(0))
        tax = _slab_tax(taxable, SLABS_NEW)
        # §87A: full rebate up to the limit; just above it, marginal relief
        # caps tax to the income exceeding the limit.
        tax = (
            D(0)
            if taxable <= REBATE_87A_NEW_LIMIT
            else min(tax, taxable - REBATE_87A_NEW_LIMIT)
        )
    else:
        deductions = chapter_via_deductions or D(0)
        taxable = annual_gross - STD_DEDUCTION_OLD - deductions
        taxable = max(taxable, D(0))
        tax = _slab_tax(taxable, SLABS_OLD)
        if taxable <= REBATE_87A_OLD_LIMIT:
            tax = D(0)  # §87A rebate

    total = tax * (D(1) + CESS_RATE)
    return round_rupee(total)


def monthly_tds(
    monthly_gross: Decimal,
    *,
    regime: str = "new",
    chapter_via_deductions: Decimal | None = None,
) -> Decimal:
    """Projected monthly TDS = annual tax (on annualised gross) / 12."""
    annual_tax = compute_annual_tax(
        monthly_gross * 12, regime=regime, chapter_via_deductions=chapter_via_deductions
    )
    return round_rupee(annual_tax / 12)

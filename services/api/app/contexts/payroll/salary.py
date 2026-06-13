"""Salary structuring + payslip computation (pure, Decimal-only)."""

from dataclasses import dataclass, field
from decimal import Decimal

from app.contexts.payroll.statutory import (
    DEFAULT_RATES,
    StatutoryRates,
    compute_esi,
    compute_pf,
    compute_pt,
)
from app.core.money import D, Money, round_money

# Default structuring ratios (overridable per employee by HR)
BASIC_OF_CTC = Decimal("0.40")  # basic = 40% of monthly CTC
HRA_OF_BASIC = Decimal("0.50")  # HRA = 50% of basic (non-metro default)
ZERO = D(0)


@dataclass(frozen=True)
class SalaryStructure:
    ctc_annual: Money
    basic: Money
    hra: Money
    special_allowance: Money

    @property
    def gross(self) -> Money:
        return self.basic + self.hra + self.special_allowance


def derive_structure(ctc_annual: Money) -> SalaryStructure:
    """Suggest a monthly component split from annual CTC. CTC ≈ gross +
    employer PF (gratuity/ESI omitted from the default split). HR can override."""
    monthly_ctc = round_money(ctc_annual / 12)
    basic = round_money(monthly_ctc * BASIC_OF_CTC)
    hra = round_money(basic * HRA_OF_BASIC)
    employer_pf = compute_pf(basic).employer
    special = round_money(monthly_ctc - employer_pf - basic - hra)
    if special < 0:
        special = D(0)
    return SalaryStructure(ctc_annual, basic, hra, special)


@dataclass(frozen=True)
class Payslip:
    working_days: int
    lop_days: Decimal
    earnings: dict[str, Money] = field(default_factory=dict)
    deductions: dict[str, Money] = field(default_factory=dict)
    employer_contributions: dict[str, Money] = field(default_factory=dict)
    gross: Money = D(0)
    total_deductions: Money = D(0)
    net_pay: Money = D(0)


def compute_payslip(
    s: SalaryStructure,
    *,
    working_days: int = 30,
    lop_days: Decimal = ZERO,
    declared_tds: Money = ZERO,
    rates: StatutoryRates = DEFAULT_RATES,
) -> Payslip:
    """Compute one month's payslip from a structure, with loss-of-pay
    proration. PF is on (prorated) basic; ESI/PT on prorated gross. Rates
    come from the tenant's active statutory pack (defaults to FY25-26)."""
    if lop_days < 0 or lop_days > working_days:
        raise ValueError("lop_days must be between 0 and working_days")

    paid_ratio = (Decimal(working_days) - lop_days) / Decimal(working_days)
    basic = round_money(s.basic * paid_ratio)
    hra = round_money(s.hra * paid_ratio)
    special = round_money(s.special_allowance * paid_ratio)
    gross = basic + hra + special

    pf = compute_pf(basic, rates=rates)
    esi = compute_esi(gross, rates=rates)
    pt = compute_pt(gross, rates=rates)

    deductions: dict[str, Money] = {"pf_employee": pf.employee, "pt": pt}
    if esi.applicable:
        deductions["esi_employee"] = esi.employee
    if declared_tds > 0:
        deductions["tds"] = declared_tds

    total_deductions = sum(deductions.values(), D(0))
    net_pay = gross - total_deductions

    employer = {"pf_employer": pf.employer}
    if esi.applicable:
        employer["esi_employer"] = esi.employer

    return Payslip(
        working_days=working_days,
        lop_days=lop_days,
        earnings={"basic": basic, "hra": hra, "special_allowance": special},
        deductions=deductions,
        employer_contributions=employer,
        gross=gross,
        total_deductions=total_deductions,
        net_pay=net_pay,
    )

"""India statutory payroll math — pure, Decimal-only, table-driven.

All amounts are `decimal.Decimal` (see core/money.py). Constants reflect
common FY2025-26 rules; they are deliberately explicit and unit-tested
(golden tests) so changes are deliberate and reviewable. This is NOT tax
advice — statutory packs are versioned per the blueprint.

Scope of this module:
- EPF (Provident Fund): employee + employer
- ESI: employee + employer, applicability threshold
- Professional Tax (PT): a simple monthly slab (Karnataka-style default)
TDS is handled separately (declared amount for now — full annual projection
with regimes/declarations is a later module).
"""

from dataclasses import dataclass
from decimal import Decimal

from app.core.money import D, round_rupee

# --- EPF ---------------------------------------------------------------
PF_RATE = Decimal("0.12")  # 12% employee and employer
PF_WAGE_CEILING = D(15000)  # statutory PF wage ceiling (basic+DA)
EPS_RATE = Decimal("0.0833")  # employer share to pension (within the 12%)
EPS_WAGE_CEILING = D(15000)

# --- ESI ---------------------------------------------------------------
ESI_EMPLOYEE_RATE = Decimal("0.0075")  # 0.75%
ESI_EMPLOYER_RATE = Decimal("0.0325")  # 3.25%
ESI_GROSS_CEILING = D(21000)  # ESI applies when monthly gross <= this

# --- Professional Tax (Karnataka-style default) ------------------------
PT_EXEMPT_BELOW = D(25000)  # no PT at or below this monthly gross
PT_AMOUNT = D(200)  # flat monthly PT above the threshold


@dataclass(frozen=True)
class PFResult:
    employee: Decimal
    employer: Decimal
    employer_pension: Decimal  # EPS portion of employer share
    employer_pf: Decimal       # remainder of employer share to EPF
    pf_wage: Decimal


def compute_pf(basic: Decimal, *, voluntary_full_basic: bool = False) -> PFResult:
    """EPF on basic (proxy for basic+DA). Capped at the statutory ceiling
    unless the employer contributes on full basic (voluntary)."""
    pf_wage = basic if voluntary_full_basic else min(basic, PF_WAGE_CEILING)
    employee = round_rupee(pf_wage * PF_RATE)
    employer = round_rupee(pf_wage * PF_RATE)
    eps_wage = min(pf_wage, EPS_WAGE_CEILING)
    employer_pension = round_rupee(eps_wage * EPS_RATE)
    employer_pf = employer - employer_pension
    return PFResult(employee, employer, employer_pension, employer_pf, pf_wage)


@dataclass(frozen=True)
class ESIResult:
    applicable: bool
    employee: Decimal
    employer: Decimal


def compute_esi(gross: Decimal) -> ESIResult:
    """ESI applies only when monthly gross is within the ceiling. Both shares
    are rounded UP to the next rupee per ESIC rules."""
    if gross > ESI_GROSS_CEILING:
        return ESIResult(False, D(0), D(0))
    employee = (gross * ESI_EMPLOYEE_RATE).to_integral_value(rounding="ROUND_CEILING")
    employer = (gross * ESI_EMPLOYER_RATE).to_integral_value(rounding="ROUND_CEILING")
    return ESIResult(True, employee, employer)


def compute_pt(gross: Decimal) -> Decimal:
    """Professional tax (state levy). Default Karnataka-style flat slab."""
    return D(0) if gross <= PT_EXEMPT_BELOW else PT_AMOUNT

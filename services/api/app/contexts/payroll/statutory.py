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
class StatutoryRates:
    """The rate parameters payroll consumes. The DEFAULT mirrors the FY2025-26
    constants; a tenant's payroll loads these from the active statutory pack
    published by the control plane (TB2 → M3 gate)."""

    pf_rate: Decimal = PF_RATE
    pf_ceiling: Decimal = PF_WAGE_CEILING
    esi_employee: Decimal = ESI_EMPLOYEE_RATE
    esi_employer: Decimal = ESI_EMPLOYER_RATE
    esi_gross_ceiling: Decimal = ESI_GROSS_CEILING
    pt_amount: Decimal = PT_AMOUNT
    pt_exempt_below: Decimal = PT_EXEMPT_BELOW
    cess: Decimal = Decimal("0.04")


DEFAULT_RATES = StatutoryRates()


def rates_from_pack(pack: dict[str, object]) -> StatutoryRates:
    """Build StatutoryRates from a statutory_pack `rates` JSON, falling back to
    the defaults for any missing key."""
    d = DEFAULT_RATES

    def g(key: str, default: Decimal) -> Decimal:
        v = pack.get(key)
        return Decimal(str(v)) if v is not None else default

    return StatutoryRates(
        pf_rate=g("pf_rate", d.pf_rate),
        pf_ceiling=g("pf_ceiling", d.pf_ceiling),
        esi_employee=g("esi_employee", d.esi_employee),
        esi_employer=g("esi_employer", d.esi_employer),
        esi_gross_ceiling=g("esi_gross_ceiling", d.esi_gross_ceiling),
        pt_amount=g("pt_amount", d.pt_amount),
        pt_exempt_below=g("pt_exempt_below", d.pt_exempt_below),
        cess=g("cess", d.cess),
    )


@dataclass(frozen=True)
class PFResult:
    employee: Decimal
    employer: Decimal
    employer_pension: Decimal  # EPS portion of employer share
    employer_pf: Decimal       # remainder of employer share to EPF
    pf_wage: Decimal


def compute_pf(
    basic: Decimal, *, voluntary_full_basic: bool = False, rates: StatutoryRates = DEFAULT_RATES
) -> PFResult:
    """EPF on basic (proxy for basic+DA). Capped at the statutory ceiling
    unless the employer contributes on full basic (voluntary)."""
    pf_wage = basic if voluntary_full_basic else min(basic, rates.pf_ceiling)
    employee = round_rupee(pf_wage * rates.pf_rate)
    employer = round_rupee(pf_wage * rates.pf_rate)
    eps_wage = min(pf_wage, EPS_WAGE_CEILING)
    employer_pension = round_rupee(eps_wage * EPS_RATE)
    employer_pf = employer - employer_pension
    return PFResult(employee, employer, employer_pension, employer_pf, pf_wage)


@dataclass(frozen=True)
class ESIResult:
    applicable: bool
    employee: Decimal
    employer: Decimal


def compute_esi(gross: Decimal, *, rates: StatutoryRates = DEFAULT_RATES) -> ESIResult:
    """ESI applies only when monthly gross is within the ceiling. Both shares
    are rounded UP to the next rupee per ESIC rules."""
    if gross > rates.esi_gross_ceiling:
        return ESIResult(False, D(0), D(0))
    employee = (gross * rates.esi_employee).to_integral_value(rounding="ROUND_CEILING")
    employer = (gross * rates.esi_employer).to_integral_value(rounding="ROUND_CEILING")
    return ESIResult(True, employee, employer)


def compute_pt(gross: Decimal, *, rates: StatutoryRates = DEFAULT_RATES) -> Decimal:
    """Professional tax (state levy). Default Karnataka-style flat slab."""
    return D(0) if gross <= rates.pt_exempt_below else rates.pt_amount

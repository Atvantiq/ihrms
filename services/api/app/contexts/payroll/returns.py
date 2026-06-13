"""Statutory return-file generators — PF ECR, ESI, PT (pure, Decimal-only).

These produce the upload files HR submits to the portals. Each is built from a
payroll run's payslips plus the employee's statutory identifiers. Golden-tested
so the formats can't drift silently.
"""

from dataclasses import dataclass
from decimal import Decimal

from app.contexts.payroll.statutory import (
    DEFAULT_RATES,
    StatutoryRates,
    compute_esi,
    compute_pf,
)
from app.core.money import D, Money

ECR_SEP = "#~#"  # EPFO ECR field delimiter


@dataclass(frozen=True)
class Member:
    employee_code: str
    name: str
    uan: str | None
    esic_ip: str | None
    pt_state: str
    gross: Money
    basic: Money
    working_days: int
    lop_days: Decimal


def _i(v: Decimal) -> str:
    """Whole-rupee integer string (EPFO/ESIC files carry no paise)."""
    return str(int(v.to_integral_value()))


def ecr_line(m: Member, *, rates: StatutoryRates = DEFAULT_RATES) -> str:
    """One EPFO ECR v2.0 member line (11 `#~#`-delimited fields)."""
    pf = compute_pf(m.basic, rates=rates)
    fields = [
        m.uan or "",
        m.name,
        _i(m.gross),            # gross wages
        _i(pf.pf_wage),         # EPF wages
        _i(pf.pf_wage),         # EPS wages
        _i(pf.pf_wage),         # EDLI wages
        _i(pf.employee),        # EPF employee contribution
        _i(pf.employer_pension),  # EPS contribution
        _i(pf.employer_pf),     # EPF employer share (ER total − EPS)
        str(int(m.lop_days)),   # NCP (non-contributing period) days
        "0",                    # refund of advances
    ]
    return ECR_SEP.join(fields)


def ecr_file(members: list[Member], *, rates: StatutoryRates = DEFAULT_RATES) -> str:
    """The full ECR text (members only contribute if they have PF wages)."""
    lines = [ecr_line(m, rates=rates) for m in members if m.basic > 0]
    return "\n".join(lines) + ("\n" if lines else "")


def esi_file(members: list[Member], *, rates: StatutoryRates = DEFAULT_RATES) -> str:
    """ESIC contribution CSV — only IPs whose gross is within the ESI ceiling."""
    out = ["IPNumber,IPName,NoOfDays,TotalWages,IPContribution,ReasonCode"]
    for m in members:
        esi = compute_esi(m.gross, rates=rates)
        if not esi.applicable:
            continue
        paid_days = max(m.working_days - int(m.lop_days), 0)
        reason = "2" if paid_days == 0 else "0"  # 2 = on leave / zero days
        out.append(
            f"{m.esic_ip or 'NOT_SET'},{m.name},{paid_days},"
            f"{_i(m.gross)},{_i(esi.employee)},{reason}"
        )
    return "\n".join(out) + "\n"


def pt_file(members: list[Member], *, rates: StatutoryRates = DEFAULT_RATES) -> str:
    """Professional-tax statement CSV (grouped by state in practice)."""
    from app.contexts.payroll.statutory import compute_pt

    out = ["State,EmployeeCode,Name,GrossWages,PT"]
    for m in members:
        pt = compute_pt(m.gross, rates=rates)
        if pt <= 0:
            continue
        out.append(f"{m.pt_state},{m.employee_code},{m.name},{_i(m.gross)},{_i(pt)}")
    return "\n".join(out) + "\n"


def totals(members: list[Member], *, rates: StatutoryRates = DEFAULT_RATES) -> dict[str, Money]:
    """Sanity totals for the UI summary."""
    pf_ee = pf_er = esi_total = pt_total = D(0)
    for m in members:
        if m.basic > 0:
            pf = compute_pf(m.basic, rates=rates)
            pf_ee += pf.employee
            pf_er += pf.employer
        esi = compute_esi(m.gross, rates=rates)
        if esi.applicable:
            esi_total += esi.employee + esi.employer
        from app.contexts.payroll.statutory import compute_pt
        pt_total += compute_pt(m.gross, rates=rates)
    return {"pf_employee": pf_ee, "pf_employer": pf_er, "esi": esi_total, "pt": pt_total}

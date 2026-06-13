"""Payroll API — salary structures + monthly runs (HR), payslips (self/HR)."""

import json
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.contexts.payroll.salary import SalaryStructure, compute_payslip, derive_structure
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.money import D

router = APIRouter(prefix="/payroll", tags=["payroll"])


# ---------------------------------------------------------------- schemas

class StructureIn(BaseModel):
    ctc_annual: Decimal = Field(gt=0)
    # optional explicit overrides; if omitted, derived from CTC
    basic: Decimal | None = None
    hra: Decimal | None = None
    special_allowance: Decimal | None = None
    effective_from: date


class StructureOut(BaseModel):
    employee_id: int
    ctc_annual: Decimal
    basic: Decimal
    hra: Decimal
    special_allowance: Decimal
    gross_monthly: Decimal
    effective_from: date


class PreviewOut(BaseModel):
    ctc_annual: Decimal
    basic: Decimal
    hra: Decimal
    special_allowance: Decimal
    gross_monthly: Decimal


class RunOut(BaseModel):
    id: str
    period_year: int
    period_month: int
    working_days: int
    status: str
    employee_count: int
    total_gross: Decimal
    total_net: Decimal


class PayslipOut(BaseModel):
    employee_id: int
    employee_name: str
    period_year: int
    period_month: int
    lop_days: Decimal
    earnings: dict[str, Decimal]
    deductions: dict[str, Decimal]
    employer_contributions: dict[str, Decimal]
    gross: Decimal
    total_deductions: Decimal
    net_pay: Decimal


# ---------------------------------------------------------------- structures

@router.get("/preview", response_model=PreviewOut)
async def preview_structure(
    ctc_annual: Decimal,
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> PreviewOut:
    s = derive_structure(ctc_annual)
    return PreviewOut(
        ctc_annual=s.ctc_annual, basic=s.basic, hra=s.hra,
        special_allowance=s.special_allowance, gross_monthly=s.gross,
    )


@router.put("/structures/{employee_id}", response_model=StructureOut)
async def set_structure(
    employee_id: int,
    payload: StructureIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> StructureOut:
    emp = (
        await session.execute(
            text("select 1 from public.employees where employee_id = :id"),
            {"id": employee_id},
        )
    ).scalar()
    if emp is None:
        raise HTTPException(404, "Employee not found")

    if payload.basic and payload.hra and payload.special_allowance is not None:
        s = SalaryStructure(payload.ctc_annual, payload.basic, payload.hra,
                            payload.special_allowance)
    else:
        s = derive_structure(payload.ctc_annual)

    await session.execute(
        text("""update ihrms.salary_structure set is_active = false
                where employee_id = :emp and is_active"""),
        {"emp": employee_id},
    )
    await session.execute(
        text("""insert into ihrms.salary_structure
                (employee_id, ctc_annual, basic, hra, special_allowance, effective_from)
                values (:emp, :ctc, :basic, :hra, :special, :eff)"""),
        {"emp": employee_id, "ctc": s.ctc_annual, "basic": s.basic, "hra": s.hra,
         "special": s.special_allowance, "eff": payload.effective_from},
    )
    await record_audit(
        session, principal, "salary.set", "employee", str(employee_id),
        summary=f"Set CTC ₹{s.ctc_annual}", changes={"ctc_annual": str(s.ctc_annual)},
    )
    out = StructureOut(
        employee_id=employee_id, ctc_annual=s.ctc_annual, basic=s.basic, hra=s.hra,
        special_allowance=s.special_allowance, gross_monthly=s.gross,
        effective_from=payload.effective_from,
    )
    await session.commit()
    return out


@router.get("/structures/{employee_id}", response_model=StructureOut)
async def get_structure(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> StructureOut:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own salary")
    row = (
        await session.execute(
            text("""select ctc_annual, basic, hra, special_allowance, effective_from
                    from ihrms.salary_structure
                    where employee_id = :emp and is_active"""),
            {"emp": employee_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "No salary structure set")
    return StructureOut(
        employee_id=employee_id, ctc_annual=row["ctc_annual"], basic=row["basic"],
        hra=row["hra"], special_allowance=row["special_allowance"],
        gross_monthly=row["basic"] + row["hra"] + row["special_allowance"],
        effective_from=row["effective_from"],
    )


# ---------------------------------------------------------------- runs

class RunIn(BaseModel):
    period_year: int = Field(ge=2020, le=2100)
    period_month: int = Field(ge=1, le=12)
    working_days: int = Field(default=30, ge=28, le=31)


@router.get("/runs", response_model=list[RunOut])
async def list_runs(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> list[RunOut]:
    rows = (
        await session.execute(
            text("""select id::text, period_year, period_month, working_days, status,
                       employee_count, total_gross, total_net
                    from ihrms.payroll_run order by period_year desc, period_month desc""")
        )
    ).mappings().all()
    return [RunOut(**dict(r)) for r in rows]


@router.post("/runs", response_model=RunOut, status_code=201)
async def create_run(
    payload: RunIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> RunOut:
    dup = (
        await session.execute(
            text("""select 1 from ihrms.payroll_run
                    where period_year = :y and period_month = :m"""),
            {"y": payload.period_year, "m": payload.period_month},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "A run already exists for that month")

    run_id = (
        await session.execute(
            text("""insert into ihrms.payroll_run
                    (period_year, period_month, working_days, created_by)
                    values (:y, :m, :wd, :by) returning id::text"""),
            {"y": payload.period_year, "m": payload.period_month,
             "wd": payload.working_days, "by": principal.employee_id},
        )
    ).scalar_one()

    structures = (
        await session.execute(
            text("""select employee_id, ctc_annual, basic, hra, special_allowance
                    from ihrms.salary_structure where is_active""")
        )
    ).mappings().all()

    total_gross = D(0)
    total_net = D(0)
    for st in structures:
        s = SalaryStructure(st["ctc_annual"], st["basic"], st["hra"],
                            st["special_allowance"])
        slip = compute_payslip(s, working_days=payload.working_days)
        await session.execute(
            text("""insert into ihrms.payslip
                    (run_id, employee_id, lop_days, earnings, deductions,
                     employer_contributions, gross, total_deductions, net_pay)
                    values (:run, :emp, :lop, cast(:earn as jsonb), cast(:ded as jsonb),
                            cast(:empr as jsonb), :gross, :totded, :net)"""),
            {"run": run_id, "emp": st["employee_id"], "lop": slip.lop_days,
             "earn": json.dumps({k: str(v) for k, v in slip.earnings.items()}),
             "ded": json.dumps({k: str(v) for k, v in slip.deductions.items()}),
             "empr": json.dumps({k: str(v) for k, v in slip.employer_contributions.items()}),
             "gross": slip.gross, "totded": slip.total_deductions, "net": slip.net_pay},
        )
        total_gross += slip.gross
        total_net += slip.net_pay

    await session.execute(
        text("""update ihrms.payroll_run set employee_count = :n,
                total_gross = :g, total_net = :net where id = :id"""),
        {"n": len(structures), "g": total_gross, "net": total_net, "id": run_id},
    )
    await record_audit(
        session, principal, "payroll.run", "payroll_run", run_id,
        summary=f"Ran payroll {payload.period_month}/{payload.period_year} "
        f"· {len(structures)} employees · net ₹{total_net}",
    )
    out = RunOut(
        id=run_id, period_year=payload.period_year, period_month=payload.period_month,
        working_days=payload.working_days, status="draft",
        employee_count=len(structures), total_gross=total_gross, total_net=total_net,
    )
    await session.commit()
    return out


@router.post("/runs/{run_id}/finalize", response_model=RunOut)
async def finalize_run(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> RunOut:
    row = (
        await session.execute(
            text("""update ihrms.payroll_run set status = 'finalized', finalized_at = now()
                    where id = :id and status = 'draft'
                    returning id::text, period_year, period_month, working_days, status,
                              employee_count, total_gross, total_net"""),
            {"id": run_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(409, "Run not found or already finalized")
    await record_audit(
        session, principal, "payroll.finalize", "payroll_run", run_id,
        summary="Finalized payroll run",
    )
    out = RunOut(**dict(row))
    await session.commit()
    return out


@router.get("/runs/{run_id}/register", response_model=list[PayslipOut])
async def run_register(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> list[PayslipOut]:
    return await _payslips(session, "p.run_id = :run", {"run": run_id})


@router.get("/payslips/{employee_id}", response_model=list[PayslipOut])
async def employee_payslips(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[PayslipOut]:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own payslips")
    return await _payslips(session, "p.employee_id = :emp", {"emp": employee_id})


async def _payslips(
    session: AsyncSession, where: str, params: dict[str, Any]
) -> list[PayslipOut]:
    rows = (
        await session.execute(
            text(f"""select p.employee_id, r.period_year, r.period_month, p.lop_days,
                        p.earnings, p.deductions, p.employer_contributions,
                        p.gross, p.total_deductions, p.net_pay,
                        trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                     from ihrms.payslip p
                     join ihrms.payroll_run r on r.id = p.run_id
                     left join public.employees e on e.employee_id = p.employee_id
                     where {where}
                     order by r.period_year desc, r.period_month desc, nm"""),
            params,
        )
    ).mappings().all()

    def dec(m: dict[str, Any]) -> dict[str, Decimal]:
        return {k: Decimal(str(v)) for k, v in m.items()}

    return [
        PayslipOut(
            employee_id=r["employee_id"], employee_name=r["nm"] or str(r["employee_id"]),
            period_year=r["period_year"], period_month=r["period_month"],
            lop_days=r["lop_days"], earnings=dec(r["earnings"]),
            deductions=dec(r["deductions"]),
            employer_contributions=dec(r["employer_contributions"]),
            gross=r["gross"], total_deductions=r["total_deductions"], net_pay=r["net_pay"],
        )
        for r in rows
    ]

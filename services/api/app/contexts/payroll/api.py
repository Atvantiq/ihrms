"""Payroll API — salary structures + monthly runs (HR), payslips (self/HR)."""

import calendar
import json
from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.advances.service import emi_for_month
from app.contexts.attendance.repo import month_summary
from app.contexts.history.recorder import record_changes
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.contexts.payroll.arrears import arrear_amount, retro_months
from app.contexts.payroll.outputs import gl_journal, statutory_totals
from app.contexts.payroll.pdf import payslip_pdf
from app.contexts.payroll.returns import Member, ecr_file, esi_file, pt_file
from app.contexts.payroll.salary import SalaryStructure, compute_payslip, derive_structure
from app.contexts.payroll.statutory import DEFAULT_RATES, StatutoryRates, rates_from_pack
from app.contexts.payroll.tds import monthly_tds
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.money import D
from app.core.validators import validate_ifsc, validate_uan

router = APIRouter(prefix="/payroll", tags=["payroll"])


# ---------------------------------------------------------------- schemas

class StructureIn(BaseModel):
    ctc_annual: Decimal = Field(gt=0)
    # optional explicit overrides; if omitted, derived from CTC
    basic: Decimal | None = None
    hra: Decimal | None = None
    special_allowance: Decimal | None = None
    effective_from: date
    tax_regime: Literal["new", "old"] = "new"
    chapter_via_deductions: Decimal = D(0)  # 80C etc. (old regime only)


class StructureOut(BaseModel):
    employee_id: int
    ctc_annual: Decimal
    basic: Decimal
    hra: Decimal
    special_allowance: Decimal
    gross_monthly: Decimal
    effective_from: date
    tax_regime: str = "new"
    chapter_via_deductions: Decimal = D(0)
    monthly_tds: Decimal = D(0)


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

    prev = (
        await session.execute(
            text("""select ctc_annual, basic + hra + special_allowance as gross
                    from ihrms.salary_structure
                    where employee_id = :emp and is_active"""),
            {"emp": employee_id},
        )
    ).mappings().first()
    prev_ctc = prev["ctc_annual"] if prev else None
    await session.execute(
        text("""update ihrms.salary_structure set is_active = false
                where employee_id = :emp and is_active"""),
        {"emp": employee_id},
    )
    await session.execute(
        text("""insert into ihrms.salary_structure
                (employee_id, ctc_annual, basic, hra, special_allowance, effective_from,
                 tax_regime, chapter_via_deductions)
                values (:emp, :ctc, :basic, :hra, :special, :eff, :regime, :ded)"""),
        {"emp": employee_id, "ctc": s.ctc_annual, "basic": s.basic, "hra": s.hra,
         "special": s.special_allowance, "eff": payload.effective_from,
         "regime": payload.tax_regime, "ded": payload.chapter_via_deductions},
    )
    await record_audit(
        session, principal, "salary.set", "employee", str(employee_id),
        summary=f"Set CTC ₹{s.ctc_annual} ({payload.tax_regime} regime)",
        changes={"ctc_annual": str(s.ctc_annual), "tax_regime": payload.tax_regime},
    )
    await record_changes(
        session, employee_id=employee_id, category="compensation",
        changes=[("ctc_annual", prev_ctc, s.ctc_annual)],
        changed_by=principal.employee_id, effective_date=payload.effective_from,
    )
    # a back-dated change owes arrears for the months already paid at the old rate
    if prev is not None:
        months = retro_months(payload.effective_from, date.today())
        arr = arrear_amount(Decimal(str(prev["gross"])), s.gross, months)
        if arr != 0:
            await session.execute(
                text("""insert into ihrms.arrear
                        (employee_id, amount, months, reason, effective_from, created_by)
                        values (:e, :amt, :m, :reason, :eff, :by)"""),
                {"e": employee_id, "amt": arr, "m": months,
                 "reason": f"Salary revision effective {payload.effective_from}",
                 "eff": payload.effective_from, "by": principal.employee_id},
            )
    tds = monthly_tds(
        s.gross, regime=payload.tax_regime,
        chapter_via_deductions=payload.chapter_via_deductions,
    )
    out = StructureOut(
        employee_id=employee_id, ctc_annual=s.ctc_annual, basic=s.basic, hra=s.hra,
        special_allowance=s.special_allowance, gross_monthly=s.gross,
        effective_from=payload.effective_from, tax_regime=payload.tax_regime,
        chapter_via_deductions=payload.chapter_via_deductions, monthly_tds=tds,
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
            text("""select ctc_annual, basic, hra, special_allowance, effective_from,
                       tax_regime, chapter_via_deductions
                    from ihrms.salary_structure
                    where employee_id = :emp and is_active"""),
            {"emp": employee_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "No salary structure set")
    gross = row["basic"] + row["hra"] + row["special_allowance"]
    return StructureOut(
        employee_id=employee_id, ctc_annual=row["ctc_annual"], basic=row["basic"],
        hra=row["hra"], special_allowance=row["special_allowance"],
        gross_monthly=gross, effective_from=row["effective_from"],
        tax_regime=row["tax_regime"],
        chapter_via_deductions=row["chapter_via_deductions"],
        monthly_tds=monthly_tds(
            gross, regime=row["tax_regime"],
            chapter_via_deductions=row["chapter_via_deductions"],
        ),
    )


# ---------------------------------------------------------------- runs

async def _active_rates(session: AsyncSession) -> StatutoryRates:
    """Load the control plane's active statutory pack; fall back to the
    built-in FY25-26 defaults if none is published."""
    pack = (
        await session.execute(
            text("""select rates from ihrms.statutory_pack where is_active
                    order by effective_from desc limit 1""")
        )
    ).scalar()
    return rates_from_pack(pack) if pack else DEFAULT_RATES


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
            text("""select employee_id, ctc_annual, basic, hra, special_allowance,
                       tax_regime, chapter_via_deductions
                    from ihrms.salary_structure where is_active""")
        )
    ).mappings().all()

    # end-of-period date so attendance LOP reflects the whole month
    period_end = date(payload.period_year, payload.period_month,
                      calendar.monthrange(payload.period_year, payload.period_month)[1])
    # statutory rates from the control plane's active pack (TB2 -> M3 gate)
    rates = await _active_rates(session)

    total_gross = D(0)
    total_net = D(0)
    for st in structures:
        s = SalaryStructure(st["ctc_annual"], st["basic"], st["hra"],
                            st["special_allowance"])
        tds = monthly_tds(
            s.gross, regime=st["tax_regime"],
            chapter_via_deductions=st["chapter_via_deductions"],
        )
        att = await month_summary(
            session, st["employee_id"], payload.period_year, payload.period_month,
            period_end,
        )
        # Payroll docks ONLY explicitly-marked absences. Unmarked days are
        # treated as present (paid) — never withhold pay merely because
        # attendance wasn't recorded. att.lop (which includes unmarked days)
        # is for the attendance view's "needs attention", not for pay.
        #
        # Recover this month's EMI on the employee's active advance/loan (the
        # final instalment clears the remainder). One recovery row per run.
        adv = (
            await session.execute(
                text("""select id::text, emi_amount, outstanding from ihrms.advance
                        where employee_id = :emp and status = 'active'
                        order by created_at limit 1"""),
                {"emp": st["employee_id"]},
            )
        ).mappings().first()
        loan_recovery = D(0)
        if adv is not None:
            loan_recovery = emi_for_month(adv["emi_amount"], adv["outstanding"])

        # pay out any pending arrears (back-dated salary revisions) this run
        arrears = (
            await session.execute(
                text("""select coalesce(sum(amount), 0) from ihrms.arrear
                        where employee_id = :emp and status = 'pending'"""),
                {"emp": st["employee_id"]},
            )
        ).scalar()
        arrears = D(str(arrears or 0))

        slip = compute_payslip(
            s, working_days=payload.working_days,
            lop_days=D(att.absent), declared_tds=tds, loan_recovery=loan_recovery,
            arrears=arrears, rates=rates,
        )
        if arrears != 0:
            await session.execute(
                text("""update ihrms.arrear set status='paid', run_id=cast(:run as uuid)
                        where employee_id=:emp and status='pending'"""),
                {"emp": st["employee_id"], "run": run_id},
            )
        if adv is not None and loan_recovery > 0:
            await session.execute(
                text("""insert into ihrms.advance_recovery
                        (advance_id, amount, source, run_id)
                        values (:a, :amt, 'payroll', cast(:run as uuid))
                        on conflict (advance_id, run_id)
                          where run_id is not null do nothing"""),
                {"a": adv["id"], "amt": loan_recovery, "run": run_id},
            )
            new_outstanding = adv["outstanding"] - loan_recovery
            new_status = "closed" if new_outstanding <= 0 else "active"
            await session.execute(
                text("""update ihrms.advance
                        set outstanding = cast(:rem as numeric), status = :st,
                            updated_at = now()
                        where id = :id"""),
                {"rem": new_outstanding, "st": new_status, "id": adv["id"]},
            )
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


# ---------------------------------------------------------------- outputs (M3)

async def _raw_payslips(session: AsyncSession, run_id: str) -> list[dict[str, Any]]:
    rows = (
        await session.execute(
            text("""select employee_id, lop_days, earnings, deductions,
                       employer_contributions, gross, total_deductions, net_pay
                    from ihrms.payslip where run_id = :run"""),
            {"run": run_id},
        )
    ).mappings().all()

    def dec(m: dict[str, Any]) -> dict[str, Decimal]:
        return {k: Decimal(str(v)) for k, v in m.items()}

    return [
        {**dict(r), "earnings": dec(r["earnings"]), "deductions": dec(r["deductions"]),
         "employer_contributions": dec(r["employer_contributions"])}
        for r in rows
    ]


class StatutoryOut(BaseModel):
    pf_employee: Decimal
    pf_employer: Decimal
    esi_employee: Decimal
    esi_employer: Decimal
    pt: Decimal
    tds: Decimal


@router.get("/runs/{run_id}/statutory", response_model=StatutoryOut)
async def run_statutory(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> StatutoryOut:
    s = statutory_totals(await _raw_payslips(session, run_id))
    return StatutoryOut(
        pf_employee=s.pf_employee, pf_employer=s.pf_employer,
        esi_employee=s.esi_employee, esi_employer=s.esi_employer, pt=s.pt, tds=s.tds,
    )


class JournalLineOut(BaseModel):
    account: str
    debit: Decimal
    credit: Decimal


class GLOut(BaseModel):
    lines: list[JournalLineOut]
    total_debit: Decimal
    total_credit: Decimal
    balanced: bool


@router.get("/runs/{run_id}/gl", response_model=GLOut)
async def run_gl(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> GLOut:
    j = gl_journal(await _raw_payslips(session, run_id))
    return GLOut(
        lines=[JournalLineOut(account=ln.account, debit=ln.debit, credit=ln.credit)
               for ln in j.lines],
        total_debit=j.total_debit, total_credit=j.total_credit, balanced=j.balanced,
    )


@router.get("/runs/{run_id}/bankfile")
async def run_bankfile(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> Response:
    rows = (
        await session.execute(
            text("""select e.employee_code,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm,
                       b.account_number, b.ifsc, b.bank_name, p.net_pay
                    from ihrms.payslip p
                    left join public.employees e on e.employee_id = p.employee_id
                    left join ihrms.employee_bank b
                           on b.employee_id = p.employee_id and b.is_active
                    where p.run_id = :run order by nm"""),
            {"run": run_id},
        )
    ).mappings().all()
    out = ["EmployeeCode,Name,AccountNumber,IFSC,Bank,Amount,Mode"]
    for r in rows:
        out.append(
            f"{r['employee_code']},{r['nm']},{r['account_number'] or 'NOT_SET'},"
            f"{r['ifsc'] or 'NOT_SET'},{r['bank_name'] or ''},{r['net_pay']},NEFT"
        )
    return Response(
        content="\n".join(out) + "\n", media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="bankfile_{run_id[:8]}.csv"'},
    )


# ---------------------------------------------------------------- statutory IDs

class StatutoryIdsIn(BaseModel):
    uan: str | None = None
    pf_number: str | None = None
    esic_ip: str | None = None
    pt_state: str = "KA"

    @field_validator("uan")
    @classmethod
    def _uan(cls, v: str | None) -> str | None:
        return None if not (v and v.strip()) else validate_uan(v)


class StatutoryIdsOut(StatutoryIdsIn):
    employee_id: int


@router.get("/statutory/{employee_id}", response_model=StatutoryIdsOut)
async def get_statutory(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> StatutoryIdsOut:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own statutory IDs")
    row = (
        await session.execute(
            text("""select uan, pf_number, esic_ip, pt_state
                    from ihrms.employee_statutory where employee_id = :e"""),
            {"e": employee_id},
        )
    ).mappings().first()
    if row is None:
        return StatutoryIdsOut(employee_id=employee_id)
    return StatutoryIdsOut(employee_id=employee_id, **dict(row))


@router.put("/statutory/{employee_id}", response_model=StatutoryIdsOut)
async def set_statutory(
    employee_id: int,
    payload: StatutoryIdsIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> StatutoryIdsOut:
    await session.execute(
        text("""insert into ihrms.employee_statutory
                (employee_id, uan, pf_number, esic_ip, pt_state, updated_by)
                values (:e, :u, :pf, :ip, :st, :by)
                on conflict (tenant_id, employee_id) do update set
                  uan=:u, pf_number=:pf, esic_ip=:ip, pt_state=:st,
                  updated_by=:by, updated_at=now()"""),
        {"e": employee_id, "u": payload.uan, "pf": payload.pf_number,
         "ip": payload.esic_ip, "st": payload.pt_state, "by": principal.employee_id},
    )
    await record_audit(
        session, principal, "statutory.set", "employee", str(employee_id),
        summary="Updated statutory identifiers",
    )
    await session.commit()
    return StatutoryIdsOut(employee_id=employee_id, **payload.model_dump())


# ---------------------------------------------------------------- arrears

class ArrearOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    amount: Decimal
    months: int
    reason: str | None = None
    effective_from: date
    status: str


@router.get("/arrears", response_model=list[ArrearOut])
async def list_arrears(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> list[ArrearOut]:
    if principal.is_hr:
        where, params = "", {}
        if employee_id is not None:
            where, params = "where a.employee_id = :e", {"e": employee_id}
    else:
        where, params = "where a.employee_id = :e", {"e": principal.employee_id}
    rows = (
        await session.execute(
            text(f"""select a.id::text, a.employee_id, a.amount, a.months, a.reason,
                       a.effective_from, a.status,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.arrear a
                    left join public.employees e on e.employee_id = a.employee_id
                    {where} order by a.created_at desc"""),
            params,
        )
    ).mappings().all()
    return [
        ArrearOut(
            id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
            amount=r["amount"], months=r["months"], reason=r["reason"],
            effective_from=r["effective_from"], status=r["status"],
        )
        for r in rows
    ]


# ---------------------------------------------------------------- return files

async def _run_members(session: AsyncSession, run_id: str) -> list[Member]:
    rows = (
        await session.execute(
            text("""select p.employee_id, e.employee_code,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm,
                       p.earnings, p.gross, p.lop_days,
                       r.working_days, s.uan, s.esic_ip,
                       coalesce(s.pt_state, 'KA') as pt_state
                    from ihrms.payslip p
                    join ihrms.payroll_run r on r.id = p.run_id
                    left join public.employees e on e.employee_id = p.employee_id
                    left join ihrms.employee_statutory s on s.employee_id = p.employee_id
                    where p.run_id = :run order by nm"""),
            {"run": run_id},
        )
    ).mappings().all()
    members: list[Member] = []
    for r in rows:
        earnings = r["earnings"] if isinstance(r["earnings"], dict) else json.loads(r["earnings"])
        members.append(
            Member(
                employee_code=r["employee_code"] or str(r["employee_id"]),
                name=r["nm"] or "—", uan=r["uan"], esic_ip=r["esic_ip"],
                pt_state=r["pt_state"], gross=Decimal(str(r["gross"])),
                basic=Decimal(str(earnings.get("basic", 0))),
                working_days=int(r["working_days"]), lop_days=Decimal(str(r["lop_days"])),
            )
        )
    return members


def _file_response(content: str, name: str, media: str) -> Response:
    return Response(
        content=content, media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/runs/{run_id}/ecr")
async def run_ecr(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> Response:
    members = await _run_members(session, run_id)
    rates = await _active_rates(session)
    return _file_response(ecr_file(members, rates=rates), f"ecr_{run_id[:8]}.txt", "text/plain")


@router.get("/runs/{run_id}/esi")
async def run_esi(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> Response:
    members = await _run_members(session, run_id)
    rates = await _active_rates(session)
    return _file_response(esi_file(members, rates=rates), f"esi_{run_id[:8]}.csv", "text/csv")


@router.get("/runs/{run_id}/pt")
async def run_pt(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> Response:
    members = await _run_members(session, run_id)
    rates = await _active_rates(session)
    return _file_response(pt_file(members, rates=rates), f"pt_{run_id[:8]}.csv", "text/csv")


@router.post("/runs/{run_id}/mark-paid", response_model=RunOut)
async def mark_paid(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> RunOut:
    row = (
        await session.execute(
            text("""update ihrms.payroll_run set status = 'paid', paid_at = now()
                    where id = :id and status = 'finalized'
                    returning id::text, period_year, period_month, working_days, status,
                              employee_count, total_gross, total_net"""),
            {"id": run_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(409, "Run must be finalized before marking paid")
    await record_audit(
        session, principal, "payroll.paid", "payroll_run", run_id,
        summary="Marked payroll run as paid",
    )
    out = RunOut(**dict(row))
    await session.commit()
    return out


class PayslipPdfMeta(BaseModel):
    employee_id: int


@router.get("/payslips/{employee_id}/pdf/{run_id}")
async def payslip_pdf_download(
    employee_id: int,
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Response:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only download your own payslip")
    row = (
        await session.execute(
            text("""select r.period_year, r.period_month, p.lop_days, p.earnings,
                       p.deductions, p.gross, p.total_deductions, p.net_pay,
                       e.employee_code,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.payslip p
                    join ihrms.payroll_run r on r.id = p.run_id
                    left join public.employees e on e.employee_id = p.employee_id
                    where p.run_id = :run and p.employee_id = :emp"""),
            {"run": run_id, "emp": employee_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Payslip not found")
    pdf = payslip_pdf(
        employee_name=row["nm"] or str(employee_id),
        employee_code=row["employee_code"] or "",
        payslip={
            "lop_days": row["lop_days"], "earnings": dict(row["earnings"]),
            "deductions": dict(row["deductions"]), "gross": row["gross"],
            "total_deductions": row["total_deductions"], "net_pay": row["net_pay"],
        },
        year=row["period_year"], month=row["period_month"],
    )
    return Response(
        content=pdf, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="payslip_{run_id[:8]}.pdf"'},
    )


class BankIn(BaseModel):
    account_number: str = Field(min_length=4, max_length=30)
    ifsc: str = Field(min_length=4, max_length=15)
    bank_name: str | None = None

    @field_validator("account_number")
    @classmethod
    def _account(cls, v: str) -> str:
        acc = v.strip()
        if not acc.isdigit():
            raise ValueError("Account number must be digits only")
        return acc

    @field_validator("ifsc")
    @classmethod
    def _ifsc(cls, v: str) -> str:
        return validate_ifsc(v)


@router.put("/bank/{employee_id}", status_code=204)
async def set_bank(
    employee_id: int,
    payload: BankIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> None:
    await session.execute(
        text("""update ihrms.employee_bank set is_active = false
                where employee_id = :emp and is_active"""),
        {"emp": employee_id},
    )
    await session.execute(
        text("""insert into ihrms.employee_bank (employee_id, account_number, ifsc, bank_name)
                values (:emp, :acc, :ifsc, :bank)"""),
        {"emp": employee_id, "acc": payload.account_number, "ifsc": payload.ifsc,
         "bank": payload.bank_name},
    )
    await record_audit(
        session, principal, "bank.set", "employee", str(employee_id),
        summary="Updated bank details",
    )
    await session.commit()

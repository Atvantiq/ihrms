"""Exit & F&F API (HR) — resignation → clearance → compute → approve → pay."""

import calendar
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.exit_fnf.fnf import compute_fnf
from app.contexts.identity.principal import ROLE_HR_ADMIN, Principal, require_roles
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.money import D

router = APIRouter(prefix="/exit", tags=["exit"])
HR = require_roles(ROLE_HR_ADMIN)

DEFAULT_CLEARANCE = ["IT Assets", "Finance / Advances", "Knowledge Transfer", "HR & Access"]


class ExitIn(BaseModel):
    employee_id: int
    resignation_date: date
    last_working_day: date
    reason: str | None = None
    notice_required_days: int = Field(default=60, ge=0, le=180)


class ClearanceOut(BaseModel):
    id: str
    item: str
    status: str
    note: str | None = None


class FnFOut(BaseModel):
    pending_salary: Decimal
    gratuity: Decimal
    leave_encashment: Decimal
    notice_recovery: Decimal
    other_recoveries: Decimal
    net_settlement: Decimal
    status: str


class ExitOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str
    resignation_date: date
    last_working_day: date
    reason: str | None = None
    notice_required_days: int
    status: str
    clearance: list[ClearanceOut] = []
    fnf: FnFOut | None = None


async def _case(session: AsyncSession, case_id: str) -> ExitOut:
    row = (
        await session.execute(
            text("""select c.id::text, c.employee_id, c.resignation_date,
                       c.last_working_day, c.reason, c.notice_required_days, c.status,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.exit_case c
                    left join public.employees e on e.employee_id = c.employee_id
                    where c.id = :id"""),
            {"id": case_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Exit case not found")
    clearance = [
        ClearanceOut(id=r["id"], item=r["item"], status=r["status"], note=r["note"])
        for r in (
            await session.execute(
                text("""select id::text, item, status, note from ihrms.clearance_item
                        where exit_case_id = :id order by item"""),
                {"id": case_id},
            )
        ).mappings().all()
    ]
    fnf_row = (
        await session.execute(
            text("""select pending_salary, gratuity, leave_encashment, notice_recovery,
                       other_recoveries, net_settlement, status
                    from ihrms.fnf_settlement where exit_case_id = :id"""),
            {"id": case_id},
        )
    ).mappings().first()
    fnf = FnFOut(**dict(fnf_row)) if fnf_row else None
    return ExitOut(
        id=row["id"], employee_id=row["employee_id"], employee_name=row["nm"] or "—",
        resignation_date=row["resignation_date"], last_working_day=row["last_working_day"],
        reason=row["reason"], notice_required_days=row["notice_required_days"],
        status=row["status"], clearance=clearance, fnf=fnf,
    )


@router.get("/cases", response_model=list[ExitOut])
async def list_cases(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[ExitOut]:
    ids = (
        await session.execute(
            text("select id::text from ihrms.exit_case order by created_at desc")
        )
    ).scalars().all()
    return [await _case(session, i) for i in ids]


@router.post("/cases", response_model=ExitOut, status_code=201)
async def initiate(
    payload: ExitIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ExitOut:
    emp = (
        await session.execute(
            text("select 1 from public.employees where employee_id=:id and is_active=1"),
            {"id": payload.employee_id},
        )
    ).scalar()
    if emp is None:
        raise HTTPException(404, "Active employee not found")
    if payload.last_working_day < payload.resignation_date:
        raise HTTPException(409, "Last working day cannot precede resignation date")

    case_id = (
        await session.execute(
            text("""insert into ihrms.exit_case
                    (employee_id, resignation_date, last_working_day, reason,
                     notice_required_days, created_by)
                    values (:emp, :rd, :lwd, :reason, :notice, :by) returning id::text"""),
            {"emp": payload.employee_id, "rd": payload.resignation_date,
             "lwd": payload.last_working_day, "reason": payload.reason,
             "notice": payload.notice_required_days, "by": principal.employee_id},
        )
    ).scalar_one()
    for item in DEFAULT_CLEARANCE:
        await session.execute(
            text("insert into ihrms.clearance_item (exit_case_id, item) values (:c, :i)"),
            {"c": case_id, "i": item},
        )
    await session.execute(
        text("update ihrms.exit_case set status='clearance' where id=:id"),
        {"id": case_id},
    )
    await record_audit(
        session, principal, "exit.initiate", "employee", str(payload.employee_id),
        summary=f"Resignation · LWD {payload.last_working_day}",
    )
    result = await _case(session, case_id)
    await session.commit()
    return result


@router.post("/cases/{case_id}/clearance/{item_id}", response_model=ExitOut)
async def clear_item(
    case_id: str,
    item_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ExitOut:
    await session.execute(
        text("""update ihrms.clearance_item set status='cleared', updated_at=now()
                where id=:id and exit_case_id=:c"""),
        {"id": item_id, "c": case_id},
    )
    result = await _case(session, case_id)
    await session.commit()
    return result


@router.post("/cases/{case_id}/compute-fnf", response_model=ExitOut)
async def compute(
    case_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ExitOut:
    case = await _case(session, case_id)
    sal = (
        await session.execute(
            text("""select basic, hra, special_allowance from ihrms.salary_structure
                    where employee_id=:emp and is_active"""),
            {"emp": case.employee_id},
        )
    ).mappings().first()
    if sal is None:
        raise HTTPException(409, "Employee has no salary structure")
    basic = Decimal(str(sal["basic"]))
    gross = basic + Decimal(str(sal["hra"])) + Decimal(str(sal["special_allowance"]))

    doj = (
        await session.execute(
            text("""select date_of_joining from public.job_details
                    where employee_id=:emp and is_active=1 limit 1"""),
            {"emp": case.employee_id},
        )
    ).scalar()
    if doj is None:
        raise HTTPException(409, "Employee has no joining date")

    # unused encashable leave = available across consuming leave types, this year
    unused = (
        await session.execute(
            text("""select coalesce(sum(accrued + carried_forward - used), 0)
                    from ihrms.leave_balance where employee_id=:emp
                      and period_year = extract(year from cast(:lwd as date))::int"""),
            {"emp": case.employee_id, "lwd": case.last_working_day},
        )
    ).scalar()
    unused_days = max(Decimal(str(unused or 0)), D(0))

    # pending salary = gross prorated for the worked part of the final month
    dim = calendar.monthrange(case.last_working_day.year, case.last_working_day.month)[1]
    pending = gross * Decimal(case.last_working_day.day) / Decimal(dim)

    notice_served = (case.last_working_day - case.resignation_date).days

    # outstanding advances/loans are recovered in full at settlement
    advances_due = (
        await session.execute(
            text("""select coalesce(sum(outstanding), 0) from ihrms.advance
                    where employee_id = :emp and status = 'active'"""),
            {"emp": case.employee_id},
        )
    ).scalar()
    other_recoveries = max(Decimal(str(advances_due or 0)), D(0))

    f = compute_fnf(
        last_basic=basic, monthly_gross=gross, doj=doj, lwd=case.last_working_day,
        unused_leave_days=unused_days, pending_salary=pending,
        notice_required_days=case.notice_required_days, notice_served_days=notice_served,
        other_recoveries=other_recoveries,
    )
    await session.execute(
        text("""insert into ihrms.fnf_settlement
                (exit_case_id, pending_salary, gratuity, leave_encashment,
                 notice_recovery, other_recoveries, net_settlement)
                values (:c, :ps, :g, :le, :nr, :orr, :net)
                on conflict (tenant_id, exit_case_id) do update set
                  pending_salary=:ps, gratuity=:g, leave_encashment=:le,
                  notice_recovery=:nr, other_recoveries=:orr, net_settlement=:net,
                  status='computed', updated_at=now()"""),
        {"c": case_id, "ps": f.pending_salary, "g": f.gratuity, "le": f.leave_encashment,
         "nr": f.notice_recovery, "orr": f.other_recoveries, "net": f.net_settlement},
    )
    await session.execute(
        text("update ihrms.exit_case set status='fnf_computed', updated_at=now() where id=:id"),
        {"id": case_id},
    )
    await record_audit(
        session, principal, "exit.fnf_compute", "employee", str(case.employee_id),
        summary=f"F&F net ₹{f.net_settlement}",
    )
    result = await _case(session, case_id)
    await session.commit()
    return result


@router.post("/cases/{case_id}/fnf/approve", response_model=ExitOut)
async def approve_fnf(
    case_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ExitOut:
    case = await _case(session, case_id)
    if case.status != "fnf_computed":
        raise HTTPException(409, "F&F must be computed first")
    if any(c.status != "cleared" for c in case.clearance):
        raise HTTPException(409, "All clearance items must be cleared before approval")
    await session.execute(
        text("""update ihrms.fnf_settlement set status='approved', approved_by=:by
                where exit_case_id=:c"""),
        {"by": principal.employee_id, "c": case_id},
    )
    await session.execute(
        text("update ihrms.exit_case set status='approved', updated_at=now() where id=:id"),
        {"id": case_id},
    )
    result = await _case(session, case_id)
    await session.commit()
    return result


@router.post("/cases/{case_id}/fnf/pay", response_model=ExitOut)
async def pay_fnf(
    case_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ExitOut:
    """Mark F&F paid and REVOKE ACCESS — deactivate the employee + job record
    in the shared master (offboarding) and the salary structure."""
    case = await _case(session, case_id)
    if case.status != "approved":
        raise HTTPException(409, "F&F must be approved before payment")
    await session.execute(
        text("""update ihrms.fnf_settlement set status='paid', updated_at=now()
                where exit_case_id=:c"""),
        {"c": case_id},
    )
    await session.execute(
        text("update ihrms.exit_case set status='paid', updated_at=now() where id=:id"),
        {"id": case_id},
    )
    # access revocation in the shared tables
    await session.execute(
        text("update public.employees set is_active=0, updated_at=now() where employee_id=:emp"),
        {"emp": case.employee_id},
    )
    await session.execute(
        text("""update public.job_details set date_of_leaving=:lwd, is_active=0,
                updated_at=now() where employee_id=:emp"""),
        {"emp": case.employee_id, "lwd": case.last_working_day},
    )
    await session.execute(
        text("update ihrms.salary_structure set is_active=false where employee_id=:emp"),
        {"emp": case.employee_id},
    )
    # settle any outstanding advances in full (recovered via the F&F)
    open_advances = (
        await session.execute(
            text("""select id::text, outstanding from ihrms.advance
                    where employee_id=:emp and status='active' and outstanding > 0"""),
            {"emp": case.employee_id},
        )
    ).mappings().all()
    for adv in open_advances:
        await session.execute(
            text("""insert into ihrms.advance_recovery (advance_id, amount, source)
                    values (:a, :amt, 'fnf')"""),
            {"a": adv["id"], "amt": adv["outstanding"]},
        )
        await session.execute(
            text("""update ihrms.advance set outstanding=0, status='closed',
                    updated_at=now() where id=:id"""),
            {"id": adv["id"]},
        )
    await record_audit(
        session, principal, "exit.paid", "employee", str(case.employee_id),
        summary="F&F paid · access revoked · employee deactivated",
    )
    result = await _case(session, case_id)
    await session.commit()
    return result


@router.get("/cases/{case_id}/relieving-letter")
async def relieving_letter(
    case_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Response:
    from fpdf import FPDF

    case = await _case(session, case_id)
    if case.status != "paid":
        raise HTTPException(409, "Relieving letter is issued after F&F payment")
    pdf = FPDF(format="A4")
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 15)
    pdf.cell(0, 10, "Atvantiq People", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Relieving & Experience Letter", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "", 11)
    body = (
        f"This is to certify that {case.employee_name} was employed with Atvantiq "
        f"and has been relieved of duties with effect from "
        f"{case.last_working_day:%d %B %Y}.\n\n"
        f"Their full and final settlement has been completed. We wish them success "
        f"in their future endeavours.\n\n"
        f"Issued on behalf of Human Resources, Atvantiq People."
    )
    pdf.multi_cell(0, 7, body)
    return Response(
        content=bytes(pdf.output()), media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="relieving_{case_id[:8]}.pdf"'},
    )

"""Exit & F&F API (HR) — resignation → clearance → compute → approve → pay."""

import calendar
from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.exit_fnf.analytics import (
    ExitAnalytics,
    ExitCaseStat,
    compute_exit_analytics,
)
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


# ====================================================================== KT

DEFAULT_KT = [
    "Document active projects & status",
    "Hand over credentials & access",
    "Brief successor / backup owner",
    "Transfer pending tasks & tickets",
    "Update runbooks & shared docs",
]


class KtItemOut(BaseModel):
    id: str
    task: str
    assignee: str | None = None
    status: str
    note: str | None = None


class KtItemIn(BaseModel):
    task: str = Field(min_length=1, max_length=200)
    assignee: str | None = None


async def _ensure_case(session: AsyncSession, case_id: str) -> None:
    ok = (
        await session.execute(
            text("select 1 from ihrms.exit_case where id = cast(:id as uuid)"),
            {"id": case_id},
        )
    ).scalar()
    if ok is None:
        raise HTTPException(404, "Exit case not found")


async def _kt_list(session: AsyncSession, case_id: str) -> list[KtItemOut]:
    rows = (
        await session.execute(
            text("""select id::text, task, assignee, status, note
                    from ihrms.exit_kt_item where exit_case_id = cast(:id as uuid)
                    order by created_at"""),
            {"id": case_id},
        )
    ).mappings().all()
    return [KtItemOut(**dict(r)) for r in rows]


@router.get("/cases/{case_id}/kt", response_model=list[KtItemOut])
async def list_kt(
    case_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[KtItemOut]:
    await _ensure_case(session, case_id)
    return await _kt_list(session, case_id)


@router.post("/cases/{case_id}/kt", response_model=list[KtItemOut], status_code=201)
async def add_kt(
    case_id: str,
    payload: KtItemIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[KtItemOut]:
    await _ensure_case(session, case_id)
    await session.execute(
        text("""insert into ihrms.exit_kt_item (exit_case_id, task, assignee)
                values (cast(:id as uuid), :t, :a)"""),
        {"id": case_id, "t": payload.task, "a": payload.assignee},
    )
    items = await _kt_list(session, case_id)  # read before commit (RLS tenant context)
    await session.commit()
    return items


@router.post("/cases/{case_id}/kt/seed-defaults", response_model=list[KtItemOut], status_code=201)
async def seed_kt(
    case_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[KtItemOut]:
    await _ensure_case(session, case_id)
    existing = (
        await session.execute(
            text("select count(*) from ihrms.exit_kt_item where exit_case_id = cast(:id as uuid)"),
            {"id": case_id},
        )
    ).scalar_one()
    if existing == 0:
        for task in DEFAULT_KT:
            await session.execute(
                text("""insert into ihrms.exit_kt_item (exit_case_id, task)
                        values (cast(:id as uuid), :t)"""),
                {"id": case_id, "t": task},
            )
    items = await _kt_list(session, case_id)  # read before commit (RLS tenant context)
    await session.commit()
    return items


@router.post("/cases/{case_id}/kt/{item_id}/toggle", response_model=list[KtItemOut])
async def toggle_kt(
    case_id: str,
    item_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[KtItemOut]:
    await _ensure_case(session, case_id)
    await session.execute(
        text("""update ihrms.exit_kt_item
                set status = case when status = 'done' then 'pending' else 'done' end,
                    updated_at = now()
                where id = cast(:i as uuid) and exit_case_id = cast(:c as uuid)"""),
        {"i": item_id, "c": case_id},
    )
    items = await _kt_list(session, case_id)  # read before commit (RLS tenant context)
    await session.commit()
    return items


# ============================================================== interview

class InterviewOut(BaseModel):
    primary_reason: str | None = None
    would_recommend: bool | None = None
    rating_management: int | None = None
    rating_role: int | None = None
    rating_culture: int | None = None
    feedback: str | None = None
    conducted_on: date | None = None


class InterviewIn(BaseModel):
    primary_reason: str | None = None
    would_recommend: bool | None = None
    rating_management: int | None = Field(default=None, ge=1, le=5)
    rating_role: int | None = Field(default=None, ge=1, le=5)
    rating_culture: int | None = Field(default=None, ge=1, le=5)
    feedback: str | None = None
    conducted_on: date | None = None


@router.get("/cases/{case_id}/interview", response_model=InterviewOut | None)
async def get_interview(
    case_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> InterviewOut | None:
    await _ensure_case(session, case_id)
    row = (
        await session.execute(
            text("""select primary_reason, would_recommend, rating_management,
                       rating_role, rating_culture, feedback, conducted_on
                    from ihrms.exit_interview where exit_case_id = cast(:id as uuid)"""),
            {"id": case_id},
        )
    ).mappings().first()
    return InterviewOut(**dict(row)) if row else None


@router.put("/cases/{case_id}/interview", response_model=InterviewOut)
async def save_interview(
    case_id: str,
    payload: InterviewIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> InterviewOut:
    await _ensure_case(session, case_id)
    await session.execute(
        text("""insert into ihrms.exit_interview
                (exit_case_id, primary_reason, would_recommend, rating_management,
                 rating_role, rating_culture, feedback, conducted_on, conducted_by)
                values (cast(:id as uuid), :pr, :wr, :rm, :rr, :rc, :fb, :on, :by)
                on conflict (exit_case_id) do update set
                  primary_reason = excluded.primary_reason,
                  would_recommend = excluded.would_recommend,
                  rating_management = excluded.rating_management,
                  rating_role = excluded.rating_role,
                  rating_culture = excluded.rating_culture,
                  feedback = excluded.feedback,
                  conducted_on = excluded.conducted_on"""),
        {"id": case_id, "pr": payload.primary_reason, "wr": payload.would_recommend,
         "rm": payload.rating_management, "rr": payload.rating_role,
         "rc": payload.rating_culture, "fb": payload.feedback,
         "on": payload.conducted_on, "by": principal.employee_id},
    )
    await record_audit(session, principal, "exit_interview.save", "exit_case", case_id,
                       summary=f"Exit interview recorded for case {case_id[:8]}")
    await session.commit()
    return InterviewOut(**payload.model_dump())


# ================================================================= alumni

class AlumniOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str
    eligible_for_rehire: bool
    personal_email: str | None = None
    note: str | None = None
    last_working_day: date | None = None


class AlumniIn(BaseModel):
    employee_id: int
    eligible_for_rehire: bool = True
    personal_email: str | None = None
    note: str | None = None


@router.get("/alumni", response_model=list[AlumniOut])
async def list_alumni(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[AlumniOut]:
    rows = (
        await session.execute(
            text("""select a.id::text, a.employee_id, a.eligible_for_rehire,
                       a.personal_email, a.note,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm,
                       c.last_working_day
                    from ihrms.exit_alumni a
                    left join public.employees e on e.employee_id = a.employee_id
                    left join ihrms.exit_case c on c.id = a.exit_case_id
                    order by a.created_at desc""")
        )
    ).mappings().all()
    return [
        AlumniOut(
            id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or "—",
            eligible_for_rehire=r["eligible_for_rehire"], personal_email=r["personal_email"],
            note=r["note"], last_working_day=r["last_working_day"],
        )
        for r in rows
    ]


@router.post("/alumni", response_model=AlumniOut, status_code=201)
async def upsert_alumni(
    payload: AlumniIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AlumniOut:
    case_id = (
        await session.execute(
            text("""select id::text from ihrms.exit_case
                    where employee_id = :e order by created_at desc limit 1"""),
            {"e": payload.employee_id},
        )
    ).scalar()
    await session.execute(
        text("""insert into ihrms.exit_alumni
                (employee_id, exit_case_id, eligible_for_rehire, personal_email, note)
                values (:e, cast(:c as uuid), :r, :pe, :n)
                on conflict (tenant_id, employee_id) do update set
                  eligible_for_rehire = excluded.eligible_for_rehire,
                  personal_email = excluded.personal_email,
                  note = excluded.note,
                  exit_case_id = excluded.exit_case_id"""),
        {"e": payload.employee_id, "c": case_id, "r": payload.eligible_for_rehire,
         "pe": payload.personal_email, "n": payload.note},
    )
    await record_audit(session, principal, "exit_alumni.upsert", "exit_alumni",
                       str(payload.employee_id),
                       summary=f"Alumni / rehire flag for {payload.employee_id}")
    # read back BEFORE commit — the per-request SET LOCAL app.tenant_id only
    # holds inside this transaction, so RLS-guarded reads must precede commit
    row = (
        await session.execute(
            text("""select a.id::text, a.eligible_for_rehire, a.personal_email, a.note,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.exit_alumni a
                    left join public.employees e on e.employee_id = a.employee_id
                    where a.employee_id = :e"""),
            {"e": payload.employee_id},
        )
    ).mappings().one()
    out = AlumniOut(
        id=row["id"], employee_id=payload.employee_id, employee_name=row["nm"] or "—",
        eligible_for_rehire=row["eligible_for_rehire"], personal_email=row["personal_email"],
        note=row["note"], last_working_day=None,
    )
    await session.commit()
    return out


# ============================================================== analytics

@router.get("/analytics", response_model=ExitAnalytics)
async def exit_analytics(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ExitAnalytics:
    rows = (
        await session.execute(
            text("""select c.reason, c.last_working_day,
                       (c.last_working_day - j.date_of_joining) as tenure_days
                    from ihrms.exit_case c
                    left join public.job_details j on j.employee_id = c.employee_id""")
        )
    ).mappings().all()
    headcount = (
        await session.execute(
            text("select count(*) from public.employees where is_active = 1")
        )
    ).scalar_one()
    cases = [
        ExitCaseStat(
            reason=r["reason"],
            last_working_day=r["last_working_day"],
            tenure_days=int(r["tenure_days"]) if r["tenure_days"] is not None else 0,
        )
        for r in rows
    ]
    return compute_exit_analytics(cases, int(headcount))

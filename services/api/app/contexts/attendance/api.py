"""Attendance API — monthly summary (derived) + day marking."""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.attendance.repo import month_summary
from app.contexts.identity.principal import Principal, get_current_principal
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/attendance", tags=["attendance"])

MarkStatus = Literal["present", "absent", "wfh"]


class DayOut(BaseModel):
    day: date
    status: str


class SummaryOut(BaseModel):
    employee_id: int
    year: int
    month: int
    days: list[DayOut]
    present: int
    wfh: int
    leave: int
    holiday: int
    weekend: int
    absent: int
    not_marked: int
    upcoming: int
    lop: int
    payable: int


class MarkIn(BaseModel):
    employee_id: int
    work_date: date
    status: MarkStatus
    note: str | None = None


@router.get("/summary", response_model=SummaryOut)
async def summary(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    year: int,
    month: int,
    employee_id: int | None = None,
) -> SummaryOut:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own attendance")
    if not (1 <= month <= 12):
        raise HTTPException(422, "Invalid month")

    m = await month_summary(session, target, year, month, date.today())
    return SummaryOut(
        employee_id=target, year=year, month=month,
        days=[DayOut(day=d.day, status=d.status) for d in m.days],
        present=m.present, wfh=m.wfh, leave=m.leave, holiday=m.holiday,
        weekend=m.weekend, absent=m.absent, not_marked=m.not_marked,
        upcoming=m.upcoming, lop=m.lop, payable=m.payable,
    )


@router.post("", response_model=SummaryOut, status_code=201)
async def mark(
    payload: MarkIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> SummaryOut:
    # employees may mark their own day; HR may mark anyone
    if payload.employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only mark your own attendance")
    if payload.work_date > date.today():
        raise HTTPException(409, "Cannot mark a future date")

    await session.execute(
        text("""insert into ihrms.attendance_record
                (employee_id, work_date, status, note, marked_by)
                values (:emp, :d, :st, :note, :by)
                on conflict (tenant_id, employee_id, work_date)
                do update set status = excluded.status, note = excluded.note,
                              marked_by = excluded.marked_by, updated_at = now()"""),
        {"emp": payload.employee_id, "d": payload.work_date, "st": payload.status,
         "note": payload.note, "by": principal.employee_id},
    )
    await record_audit(
        session, principal, "attendance.mark", "employee", str(payload.employee_id),
        summary=f"Marked {payload.work_date} as {payload.status}",
    )
    result = await summary(
        session, principal, payload.work_date.year, payload.work_date.month,
        payload.employee_id,
    )
    await session.commit()
    return result


# ---------------------------------------------------------------- regularization

RegStatus = Literal["present", "wfh"]


class RegularizationIn(BaseModel):
    work_date: date
    requested_status: RegStatus
    reason: str = Field(min_length=1, max_length=300)
    employee_id: int | None = None  # HR may file on behalf of an employee


class RegularizationOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    work_date: date
    requested_status: str
    reason: str
    status: str
    decision_note: str | None = None


_REG_SELECT = """
    select r.id::text, r.employee_id, r.work_date, r.requested_status, r.reason,
           r.status, r.decision_note,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as employee_name
    from ihrms.attendance_regularization r
    left join public.employees e on e.employee_id = r.employee_id
"""


def _reg_out(r: dict[str, Any]) -> RegularizationOut:
    return RegularizationOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["employee_name"] or None,
        work_date=r["work_date"], requested_status=r["requested_status"],
        reason=r["reason"], status=r["status"], decision_note=r["decision_note"],
    )


@router.post("/regularizations", response_model=RegularizationOut, status_code=201)
async def request_regularization(
    payload: RegularizationIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> RegularizationOut:
    target = payload.employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only regularize your own attendance")
    if payload.work_date > date.today():
        raise HTTPException(409, "Cannot regularize a future date")
    dup = (
        await session.execute(
            text("""select 1 from ihrms.attendance_regularization
                    where employee_id=:e and work_date=:d and status='pending'"""),
            {"e": target, "d": payload.work_date},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "A pending request already exists for that day")
    row = (
        await session.execute(
            text("""insert into ihrms.attendance_regularization
                    (employee_id, work_date, requested_status, reason)
                    values (:e, :d, :st, :reason) returning id::text"""),
            {"e": target, "d": payload.work_date, "st": payload.requested_status,
             "reason": payload.reason},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "attendance.regularize", "employee", str(target),
        summary=f"Requested {payload.requested_status} for {payload.work_date}",
    )
    out = (await session.execute(text(_REG_SELECT + " where r.id = :id"),
                                 {"id": row["id"]})).mappings().one()
    result = _reg_out(dict(out))
    await session.commit()
    return result


@router.get("/regularizations", response_model=list[RegularizationOut])
async def list_regularizations(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "mine",  # mine | pending
) -> list[RegularizationOut]:
    if scope == "mine":
        where, params = "where r.employee_id = :me", {"me": principal.employee_id}
    elif scope == "pending":
        if principal.is_hr:
            where, params = "where r.status = 'pending'", {}
        else:
            where = """where r.status = 'pending' and r.employee_id in (
                         select employee_id from public.job_details
                         where reporting_manager = :me and is_active = 1)"""
            params = {"me": principal.employee_id}
    else:
        raise HTTPException(422, "Invalid scope")
    rows = (
        await session.execute(text(_REG_SELECT + " " + where + " order by r.created_at desc"),
                              params)
    ).mappings().all()
    return [_reg_out(dict(r)) for r in rows]


async def _decide_regularization(
    session: AsyncSession, principal: Principal, reg_id: str, outcome: str, note: str | None
) -> RegularizationOut:
    reg = (
        await session.execute(
            text("""select employee_id, work_date, requested_status, status
                    from ihrms.attendance_regularization where id = :id"""),
            {"id": reg_id},
        )
    ).mappings().first()
    if reg is None:
        raise HTTPException(404, "Request not found")
    if reg["status"] != "pending":
        raise HTTPException(409, "Request is not pending")
    # an employee cannot decide their own; HR or the reporting manager may
    if not principal.is_hr:
        is_manager = (
            await session.execute(
                text("""select 1 from public.job_details
                        where employee_id = :emp and reporting_manager = :me
                          and is_active = 1"""),
                {"emp": reg["employee_id"], "me": principal.employee_id},
            )
        ).scalar()
        if not is_manager or reg["employee_id"] == principal.employee_id:
            raise HTTPException(403, "You cannot decide this request")

    await session.execute(
        text("""update ihrms.attendance_regularization
                set status=:st, decided_by=:by, decision_note=:note, decided_at=now()
                where id=:id"""),
        {"st": outcome, "by": principal.employee_id, "note": note, "id": reg_id},
    )
    if outcome == "approved":
        # write the actual attendance record
        await session.execute(
            text("""insert into ihrms.attendance_record
                    (employee_id, work_date, status, note, marked_by)
                    values (:emp, :d, :st, :note, :by)
                    on conflict (tenant_id, employee_id, work_date)
                    do update set status = excluded.status, note = excluded.note,
                                  marked_by = excluded.marked_by, updated_at = now()"""),
            {"emp": reg["employee_id"], "d": reg["work_date"],
             "st": reg["requested_status"], "note": "regularized", "by": principal.employee_id},
        )
    await record_audit(
        session, principal, f"attendance.regularize_{outcome[:6]}", "employee",
        str(reg["employee_id"]),
        summary=f"{outcome.capitalize()} regularization for {reg['work_date']}",
    )
    out = (await session.execute(text(_REG_SELECT + " where r.id = :id"),
                                 {"id": reg_id})).mappings().one()
    result = _reg_out(dict(out))
    await session.commit()
    return result


class RegDecision(BaseModel):
    note: str | None = None


@router.post("/regularizations/{reg_id}/approve", response_model=RegularizationOut)
async def approve_regularization(
    reg_id: str,
    payload: RegDecision,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> RegularizationOut:
    return await _decide_regularization(session, principal, reg_id, "approved", payload.note)


@router.post("/regularizations/{reg_id}/reject", response_model=RegularizationOut)
async def reject_regularization(
    reg_id: str,
    payload: RegDecision,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> RegularizationOut:
    return await _decide_regularization(session, principal, reg_id, "rejected", payload.note)

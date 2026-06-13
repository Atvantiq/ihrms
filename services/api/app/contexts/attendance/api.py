"""Attendance API — monthly summary (derived) + day marking."""

import calendar
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.attendance.service import derive_month
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

    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])

    marks = {
        r["work_date"]: r["status"]
        for r in (
            await session.execute(
                text("""select work_date, status from ihrms.attendance_record
                        where employee_id = :emp and work_date between :s and :e"""),
                {"emp": target, "s": start, "e": end},
            )
        ).mappings().all()
    }

    # approved leave dates expanded across each request's range
    leave_dates: set[date] = set()
    for r in (
        await session.execute(
            text("""select start_date, end_date from ihrms.leave_request
                    where employee_id = :emp and status = 'approved'
                      and start_date <= :e and end_date >= :s"""),
            {"emp": target, "s": start, "e": end},
        )
    ).mappings().all():
        d = max(r["start_date"], start)
        while d <= min(r["end_date"], end):
            leave_dates.add(d)
            d = date.fromordinal(d.toordinal() + 1)

    holiday_dates = {
        r["holiday_date"]
        for r in (
            await session.execute(
                text("""select holiday_date from ihrms.holiday
                        where is_active and holiday_date between :s and :e"""),
                {"s": start, "e": end},
            )
        ).mappings().all()
    }

    m = derive_month(year, month, date.today(), marks, leave_dates, holiday_dates)
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

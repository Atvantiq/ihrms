"""Duty (OOD/WFH) API — request, approve (auto-marks attendance), reject.

An employee requests WFH or on-duty for a date range; a manager/HR approves,
which writes the attendance for each day in the range. Tenant-scoped; audited.
"""

from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.duty.service import attendance_status_for, date_range
from app.contexts.identity.principal import Principal, get_current_principal
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/duty", tags=["duty"])

MAX_RANGE_DAYS = 31


class DutyOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    duty_type: str
    start_date: date
    end_date: date
    reason: str
    status: str
    decided_at: datetime | None = None


class DutyIn(BaseModel):
    duty_type: Literal["wfh", "on_duty"]
    start_date: date
    end_date: date
    reason: str = Field(min_length=1, max_length=300)
    employee_id: int | None = None

    @model_validator(mode="after")
    def _range(self) -> "DutyIn":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


_SELECT = """
    select d.id::text, d.employee_id, d.duty_type, d.start_date, d.end_date,
           d.reason, d.status, d.decided_at,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
    from ihrms.duty_request d
    left join public.employees e on e.employee_id = d.employee_id
"""


def _out(r: dict[str, Any]) -> DutyOut:
    return DutyOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
        duty_type=r["duty_type"], start_date=r["start_date"], end_date=r["end_date"],
        reason=r["reason"], status=r["status"], decided_at=r["decided_at"],
    )


@router.post("", response_model=DutyOut, status_code=201)
async def request_duty(
    payload: DutyIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DutyOut:
    target = payload.employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only request your own duty")
    if (payload.end_date - payload.start_date).days > MAX_RANGE_DAYS:
        raise HTTPException(422, f"Range cannot exceed {MAX_RANGE_DAYS} days")
    row = (
        await session.execute(
            text("""insert into ihrms.duty_request
                    (employee_id, duty_type, start_date, end_date, reason)
                    values (:e, :t, :s, :en, :r) returning id::text"""),
            {"e": target, "t": payload.duty_type, "s": payload.start_date,
             "en": payload.end_date, "r": payload.reason},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "duty.request", "employee", str(target),
        summary=f"Requested {payload.duty_type} {payload.start_date}–{payload.end_date}",
    )
    out = (await session.execute(text(_SELECT + " where d.id=:id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.get("", response_model=list[DutyOut])
async def list_duty(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "mine",  # mine | pending
) -> list[DutyOut]:
    if scope == "mine":
        where, params = "where d.employee_id = :me", {"me": principal.employee_id}
    elif scope == "pending":
        if principal.is_hr:
            where, params = "where d.status = 'pending'", {}
        else:
            where = """where d.status='pending' and d.employee_id in (
                         select employee_id from public.job_details
                         where reporting_manager = :me and is_active = 1)"""
            params = {"me": principal.employee_id}
    else:
        raise HTTPException(422, "Invalid scope")
    rows = (
        await session.execute(text(_SELECT + " " + where + " order by d.start_date desc"), params)
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


async def _decide(
    session: AsyncSession, principal: Principal, duty_id: str, outcome: str
) -> DutyOut:
    d = (
        await session.execute(
            text("""select employee_id, duty_type, start_date, end_date, status
                    from ihrms.duty_request where id=:id"""),
            {"id": duty_id},
        )
    ).mappings().first()
    if d is None:
        raise HTTPException(404, "Duty request not found")
    if d["status"] != "pending":
        raise HTTPException(409, "Duty request is not pending")
    if not principal.is_hr:
        is_mgr = (
            await session.execute(
                text("""select 1 from public.job_details
                        where employee_id=:e and reporting_manager=:me and is_active=1"""),
                {"e": d["employee_id"], "me": principal.employee_id},
            )
        ).scalar()
        if not is_mgr or d["employee_id"] == principal.employee_id:
            raise HTTPException(403, "You cannot decide this duty request")
    await session.execute(
        text("""update ihrms.duty_request set status=:st, decided_by=:by, decided_at=now()
                where id=:id"""),
        {"st": outcome, "by": principal.employee_id, "id": duty_id},
    )
    if outcome == "approved":
        status = attendance_status_for(d["duty_type"])
        for day in date_range(d["start_date"], d["end_date"]):
            await session.execute(
                text("""insert into ihrms.attendance_record
                        (employee_id, work_date, status, note, marked_by)
                        values (:e, :d, :st, 'duty', :by)
                        on conflict (tenant_id, employee_id, work_date)
                        do update set status=excluded.status, note=excluded.note,
                                      marked_by=excluded.marked_by, updated_at=now()"""),
                {"e": d["employee_id"], "d": day, "st": status, "by": principal.employee_id},
            )
    await record_audit(
        session, principal, f"duty.{outcome[:6]}", "employee", str(d["employee_id"]),
        summary=f"{outcome.capitalize()} duty request",
    )
    out = (await session.execute(text(_SELECT + " where d.id=:id"),
                                 {"id": duty_id})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.post("/{duty_id}/approve", response_model=DutyOut)
async def approve_duty(
    duty_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DutyOut:
    return await _decide(session, principal, duty_id, "approved")


@router.post("/{duty_id}/reject", response_model=DutyOut)
async def reject_duty(
    duty_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DutyOut:
    return await _decide(session, principal, duty_id, "rejected")

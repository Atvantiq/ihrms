"""Overtime API — log, list, approve/reject. OT pay lands in the payroll run.

An employee logs OT for a day (or HR on their behalf); a manager/HR approves;
approved OT is paid in the next run and marked paid. Tenant-scoped; audited.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import Principal, get_current_principal
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/overtime", tags=["overtime"])


class OvertimeOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    ot_date: date
    hours: Decimal
    rate_multiplier: Decimal
    reason: str
    status: str
    decided_at: datetime | None = None


class OvertimeIn(BaseModel):
    ot_date: date
    hours: Decimal = Field(gt=0, le=24)
    rate_multiplier: Decimal = Field(default=Decimal("2.0"), ge=1, le=3)
    reason: str = Field(min_length=1, max_length=300)
    employee_id: int | None = None  # HR may log on behalf


_SELECT = """
    select o.id::text, o.employee_id, o.ot_date, o.hours, o.rate_multiplier,
           o.reason, o.status, o.decided_at,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
    from ihrms.overtime o
    left join public.employees e on e.employee_id = o.employee_id
"""


def _out(r: dict[str, Any]) -> OvertimeOut:
    return OvertimeOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
        ot_date=r["ot_date"], hours=r["hours"], rate_multiplier=r["rate_multiplier"],
        reason=r["reason"], status=r["status"], decided_at=r["decided_at"],
    )


@router.post("", response_model=OvertimeOut, status_code=201)
async def log_overtime(
    payload: OvertimeIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> OvertimeOut:
    target = payload.employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only log your own overtime")
    if payload.ot_date > date.today():
        raise HTTPException(409, "Cannot log overtime for a future date")
    dup = (
        await session.execute(
            text("select 1 from ihrms.overtime where employee_id=:e and ot_date=:d"),
            {"e": target, "d": payload.ot_date},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Overtime already logged for that day")
    row = (
        await session.execute(
            text("""insert into ihrms.overtime
                    (employee_id, ot_date, hours, rate_multiplier, reason)
                    values (:e, :d, :h, :m, :reason) returning id::text"""),
            {"e": target, "d": payload.ot_date, "h": payload.hours,
             "m": payload.rate_multiplier, "reason": payload.reason},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "overtime.log", "employee", str(target),
        summary=f"Logged {payload.hours}h OT for {payload.ot_date}",
    )
    out = (await session.execute(text(_SELECT + " where o.id=:id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.get("", response_model=list[OvertimeOut])
async def list_overtime(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "mine",  # mine | pending
) -> list[OvertimeOut]:
    if scope == "mine":
        where, params = "where o.employee_id = :me", {"me": principal.employee_id}
    elif scope == "pending":
        if principal.is_hr:
            where, params = "where o.status = 'pending'", {}
        else:
            where = """where o.status = 'pending' and o.employee_id in (
                         select employee_id from public.job_details
                         where reporting_manager = :me and is_active = 1)"""
            params = {"me": principal.employee_id}
    else:
        raise HTTPException(422, "Invalid scope")
    rows = (
        await session.execute(text(_SELECT + " " + where + " order by o.ot_date desc"), params)
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


async def _decide(
    session: AsyncSession, principal: Principal, ot_id: str, outcome: str
) -> OvertimeOut:
    ot = (
        await session.execute(
            text("select employee_id, status from ihrms.overtime where id=:id"), {"id": ot_id}
        )
    ).mappings().first()
    if ot is None:
        raise HTTPException(404, "Overtime not found")
    if ot["status"] != "pending":
        raise HTTPException(409, "Overtime is not pending")
    if not principal.is_hr:
        is_mgr = (
            await session.execute(
                text("""select 1 from public.job_details
                        where employee_id=:emp and reporting_manager=:me and is_active=1"""),
                {"emp": ot["employee_id"], "me": principal.employee_id},
            )
        ).scalar()
        if not is_mgr or ot["employee_id"] == principal.employee_id:
            raise HTTPException(403, "You cannot decide this overtime")
    await session.execute(
        text("""update ihrms.overtime set status=:st, decided_by=:by, decided_at=now()
                where id=:id"""),
        {"st": outcome, "by": principal.employee_id, "id": ot_id},
    )
    await record_audit(
        session, principal, f"overtime.{outcome[:6]}", "employee", str(ot["employee_id"]),
        summary=f"{outcome.capitalize()} overtime",
    )
    out = (await session.execute(text(_SELECT + " where o.id=:id"),
                                 {"id": ot_id})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.post("/{ot_id}/approve", response_model=OvertimeOut)
async def approve_overtime(
    ot_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> OvertimeOut:
    return await _decide(session, principal, ot_id, "approved")


@router.post("/{ot_id}/reject", response_model=OvertimeOut)
async def reject_overtime(
    ot_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> OvertimeOut:
    return await _decide(session, principal, ot_id, "rejected")

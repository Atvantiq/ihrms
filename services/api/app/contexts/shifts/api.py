"""Shifts API — shift master, assignments, roster.

HR defines shifts and assigns them (effective-dated); an employee can see their
own current shift. The roster resolves each active employee's shift on a date.
Writes audited; tenant-scoped.
"""

from datetime import date, time
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
from app.contexts.shifts.service import crosses_midnight, shift_hours
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/shifts", tags=["shifts"])
HR = require_roles(ROLE_HR_ADMIN)


class ShiftOut(BaseModel):
    id: str
    code: str
    name: str
    start_time: time
    end_time: time
    break_minutes: int
    is_night: bool
    hours: Decimal


class ShiftIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    start_time: time
    end_time: time
    break_minutes: int = Field(default=0, ge=0, le=480)


def _shift_out(r: dict[str, Any]) -> ShiftOut:
    return ShiftOut(
        id=r["id"], code=r["code"], name=r["name"], start_time=r["start_time"],
        end_time=r["end_time"], break_minutes=r["break_minutes"], is_night=r["is_night"],
        hours=shift_hours(r["start_time"], r["end_time"], r["break_minutes"]),
    )


@router.get("", response_model=list[ShiftOut])
async def list_shifts(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[ShiftOut]:
    rows = (
        await session.execute(
            text("""select id::text, code, name, start_time, end_time,
                       break_minutes, is_night from ihrms.shift
                    where is_active order by start_time""")
        )
    ).mappings().all()
    return [_shift_out(dict(r)) for r in rows]


@router.post("", response_model=ShiftOut, status_code=201)
async def create_shift(
    payload: ShiftIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ShiftOut:
    dup = (
        await session.execute(
            text("select 1 from ihrms.shift where code = :c"), {"c": payload.code}
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Shift code already exists")
    night = crosses_midnight(payload.start_time, payload.end_time)
    row = (
        await session.execute(
            text("""insert into ihrms.shift
                    (code, name, start_time, end_time, break_minutes, is_night)
                    values (:c, :n, :st, :et, :br, :night)
                    returning id::text, code, name, start_time, end_time,
                              break_minutes, is_night"""),
            {"c": payload.code, "n": payload.name, "st": payload.start_time,
             "et": payload.end_time, "br": payload.break_minutes, "night": night},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "shift.create", "shift", row["id"],
        summary=f"Created shift {payload.code} ({payload.name})",
    )
    out = _shift_out(dict(row))
    await session.commit()
    return out


@router.delete("/{shift_id}", status_code=204)
async def deactivate_shift(
    shift_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> None:
    await session.execute(
        text("update ihrms.shift set is_active=false, updated_at=now() where id=:id"),
        {"id": shift_id},
    )
    await session.commit()


class AssignIn(BaseModel):
    employee_id: int
    shift_id: str
    effective_from: date | None = None
    effective_to: date | None = None


@router.post("/assign", status_code=201)
async def assign_shift(
    payload: AssignIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> dict[str, str]:
    shift = (
        await session.execute(
            text("select 1 from ihrms.shift where id=:id and is_active"),
            {"id": payload.shift_id},
        )
    ).scalar()
    if shift is None:
        raise HTTPException(404, "Shift not found")
    eff = payload.effective_from or date.today()
    # close any currently-open assignment the day before the new one starts
    await session.execute(
        text("""update ihrms.shift_assignment
                set effective_to = (cast(:eff as date) - 1)
                where employee_id = :e and effective_to is null"""),
        {"e": payload.employee_id, "eff": eff},
    )
    await session.execute(
        text("""insert into ihrms.shift_assignment
                (employee_id, shift_id, effective_from, effective_to, created_by)
                values (:e, cast(:s as uuid), :ef, :et, :by)"""),
        {"e": payload.employee_id, "s": payload.shift_id, "ef": eff,
         "et": payload.effective_to, "by": principal.employee_id},
    )
    await record_audit(
        session, principal, "shift.assign", "employee", str(payload.employee_id),
        summary=f"Assigned shift effective {eff}",
    )
    await session.commit()
    return {"status": "assigned"}


class RosterRow(BaseModel):
    employee_id: int
    employee_name: str
    shift_code: str | None = None
    shift_name: str | None = None


@router.get("/roster", response_model=list[RosterRow])
async def roster(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
    on: date | None = None,
) -> list[RosterRow]:
    """Each active employee's effective shift on a date (defaults to today)."""
    day = on or date.today()
    rows = (
        await session.execute(
            text("""select v.employee_id,
                       trim(concat(v.first_name,' ',coalesce(v.last_name,''))) as nm,
                       s.code, s.name
                    from ihrms.v_employee v
                    left join lateral (
                      select shift_id from ihrms.shift_assignment a
                      where a.employee_id = v.employee_id
                        and a.effective_from <= :d
                        and (a.effective_to is null or a.effective_to >= :d)
                      order by a.effective_from desc limit 1
                    ) cur on true
                    left join ihrms.shift s on s.id = cur.shift_id
                    where v.is_active
                    order by nm"""),
            {"d": day},
        )
    ).mappings().all()
    return [
        RosterRow(
            employee_id=r["employee_id"], employee_name=r["nm"] or "—",
            shift_code=r["code"], shift_name=r["name"],
        )
        for r in rows
    ]


@router.get("/my", response_model=RosterRow | None)
async def my_shift(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> RosterRow | None:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own shift")
    today = date.today()
    row = (
        await session.execute(
            text("""select s.code, s.name,
                       trim(concat(v.first_name,' ',coalesce(v.last_name,''))) as nm
                    from ihrms.shift_assignment a
                    join ihrms.shift s on s.id = a.shift_id
                    left join ihrms.v_employee v on v.employee_id = a.employee_id
                    where a.employee_id = :e and a.effective_from <= :d
                      and (a.effective_to is null or a.effective_to >= :d)
                    order by a.effective_from desc limit 1"""),
            {"e": target, "d": today},
        )
    ).mappings().first()
    if row is None:
        return None
    return RosterRow(
        employee_id=target, employee_name=row["nm"] or "—",
        shift_code=row["code"], shift_name=row["name"],
    )

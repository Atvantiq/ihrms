"""Comp-off API — earn a credit, approve, avail.

An employee logs a worked off-day; a manager/HR approves (setting an expiry);
the employee later avails the credit as a day off. Tenant-scoped; audited.
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.comp_off.service import expiry_for, is_expired
from app.contexts.identity.principal import Principal, get_current_principal
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/comp-off", tags=["comp-off"])


class CompOffOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    earned_date: date
    reason: str
    status: str
    expiry_date: date | None = None
    availed_on: date | None = None


class CompOffIn(BaseModel):
    earned_date: date
    reason: str = Field(min_length=1, max_length=300)
    employee_id: int | None = None


_SELECT = """
    select c.id::text, c.employee_id, c.earned_date, c.reason, c.status,
           c.expiry_date, c.availed_on,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
    from ihrms.comp_off c
    left join public.employees e on e.employee_id = c.employee_id
"""


def _out(r: dict[str, Any]) -> CompOffOut:
    return CompOffOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
        earned_date=r["earned_date"], reason=r["reason"], status=r["status"],
        expiry_date=r["expiry_date"], availed_on=r["availed_on"],
    )


@router.post("", response_model=CompOffOut, status_code=201)
async def earn_comp_off(
    payload: CompOffIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> CompOffOut:
    target = payload.employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only log your own comp-off")
    if payload.earned_date > date.today():
        raise HTTPException(409, "Cannot earn comp-off for a future date")
    dup = (
        await session.execute(
            text("select 1 from ihrms.comp_off where employee_id=:e and earned_date=:d"),
            {"e": target, "d": payload.earned_date},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Comp-off already logged for that day")
    row = (
        await session.execute(
            text("""insert into ihrms.comp_off (employee_id, earned_date, reason)
                    values (:e, :d, :r) returning id::text"""),
            {"e": target, "d": payload.earned_date, "r": payload.reason},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "comp_off.earn", "employee", str(target),
        summary=f"Logged comp-off for {payload.earned_date}",
    )
    out = (await session.execute(text(_SELECT + " where c.id=:id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.get("", response_model=list[CompOffOut])
async def list_comp_off(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "mine",  # mine | pending | available
) -> list[CompOffOut]:
    if scope == "mine":
        where, params = "where c.employee_id = :me", {"me": principal.employee_id}
    elif scope == "available":
        where = """where c.employee_id = :me and c.status='approved'
                   and (c.expiry_date is null or c.expiry_date >= current_date)"""
        params = {"me": principal.employee_id}
    elif scope == "pending":
        if principal.is_hr:
            where, params = "where c.status = 'pending'", {}
        else:
            where = """where c.status='pending' and c.employee_id in (
                         select employee_id from public.job_details
                         where reporting_manager = :me and is_active = 1)"""
            params = {"me": principal.employee_id}
    else:
        raise HTTPException(422, "Invalid scope")
    rows = (
        await session.execute(text(_SELECT + " " + where + " order by c.earned_date desc"), params)
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


async def _decide(
    session: AsyncSession, principal: Principal, cid: str, outcome: str
) -> CompOffOut:
    c = (
        await session.execute(
            text("select employee_id, earned_date, status from ihrms.comp_off where id=:id"),
            {"id": cid},
        )
    ).mappings().first()
    if c is None:
        raise HTTPException(404, "Comp-off not found")
    if c["status"] != "pending":
        raise HTTPException(409, "Comp-off is not pending")
    if not principal.is_hr:
        is_mgr = (
            await session.execute(
                text("""select 1 from public.job_details
                        where employee_id=:emp and reporting_manager=:me and is_active=1"""),
                {"emp": c["employee_id"], "me": principal.employee_id},
            )
        ).scalar()
        if not is_mgr or c["employee_id"] == principal.employee_id:
            raise HTTPException(403, "You cannot decide this comp-off")
    expiry = expiry_for(c["earned_date"]) if outcome == "approved" else None
    await session.execute(
        text("""update ihrms.comp_off set status=:st, expiry_date=:exp,
                decided_by=:by, decided_at=now() where id=:id"""),
        {"st": outcome, "exp": expiry, "by": principal.employee_id, "id": cid},
    )
    await record_audit(
        session, principal, f"comp_off.{outcome[:6]}", "employee", str(c["employee_id"]),
        summary=f"{outcome.capitalize()} comp-off",
    )
    out = (await session.execute(text(_SELECT + " where c.id=:id"),
                                 {"id": cid})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.post("/{cid}/approve", response_model=CompOffOut)
async def approve_comp_off(
    cid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> CompOffOut:
    return await _decide(session, principal, cid, "approved")


@router.post("/{cid}/reject", response_model=CompOffOut)
async def reject_comp_off(
    cid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> CompOffOut:
    return await _decide(session, principal, cid, "rejected")


class AvailIn(BaseModel):
    avail_date: date


@router.post("/{cid}/avail", response_model=CompOffOut)
async def avail_comp_off(
    cid: str,
    payload: AvailIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> CompOffOut:
    c = (
        await session.execute(
            text("""select employee_id, status, expiry_date
                    from ihrms.comp_off where id=:id"""),
            {"id": cid},
        )
    ).mappings().first()
    if c is None:
        raise HTTPException(404, "Comp-off not found")
    if c["employee_id"] != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only avail your own comp-off")
    if c["status"] != "approved":
        raise HTTPException(409, "Comp-off is not available to avail")
    if is_expired(c["expiry_date"], date.today()):
        raise HTTPException(409, "Comp-off credit has expired")
    await session.execute(
        text("""update ihrms.comp_off set status='availed', availed_on=:d
                where id=:id"""),
        {"d": payload.avail_date, "id": cid},
    )
    await record_audit(
        session, principal, "comp_off.avail", "employee", str(c["employee_id"]),
        summary=f"Availed comp-off on {payload.avail_date}",
    )
    out = (await session.execute(text(_SELECT + " where c.id=:id"),
                                 {"id": cid})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result

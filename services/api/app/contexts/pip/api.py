"""PIP API — open a plan, record checkpoints, close with an outcome.

HR (or a reporting manager) opens a PIP for an employee, logs periodic
checkpoints, and closes it. The employee can read their own PIP. Audited;
tenant-scoped.
"""

from datetime import date, datetime
from typing import Annotated, Literal

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
from app.contexts.pip.service import checkpoint_dates, is_open, is_valid_outcome
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/pip", tags=["pip"])
HR = require_roles(ROLE_HR_ADMIN)


class Checkpoint(BaseModel):
    id: str
    checkpoint_date: date
    rating: str
    note: str | None = None
    created_at: datetime


class PipOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    manager_id: int | None = None
    reason: str
    objectives: str
    start_date: date
    end_date: date
    status: str
    suggested_checkpoints: list[date] = []
    checkpoints: list[Checkpoint] = []


class PipIn(BaseModel):
    employee_id: int
    reason: str = Field(min_length=1, max_length=500)
    objectives: str = Field(min_length=1, max_length=2000)
    start_date: date
    end_date: date


async def _detail(session: AsyncSession, pip_id: str) -> PipOut:
    p = (
        await session.execute(
            text("""select p.id::text, p.employee_id, p.manager_id, p.reason, p.objectives,
                       p.start_date, p.end_date, p.status,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.pip p
                    left join public.employees e on e.employee_id = p.employee_id
                    where p.id = cast(:id as uuid)"""),
            {"id": pip_id},
        )
    ).mappings().first()
    if p is None:
        raise HTTPException(404, "PIP not found")
    cps = (
        await session.execute(
            text("""select id::text, checkpoint_date, rating, note, created_at
                    from ihrms.pip_checkpoint where pip_id = cast(:id as uuid)
                    order by checkpoint_date"""),
            {"id": pip_id},
        )
    ).mappings().all()
    return PipOut(
        id=p["id"], employee_id=p["employee_id"], employee_name=p["nm"] or None,
        manager_id=p["manager_id"], reason=p["reason"], objectives=p["objectives"],
        start_date=p["start_date"], end_date=p["end_date"], status=p["status"],
        suggested_checkpoints=checkpoint_dates(p["start_date"]),
        checkpoints=[Checkpoint(**dict(c)) for c in cps],
    )


@router.post("", response_model=PipOut, status_code=201)
async def open_pip(
    payload: PipIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> PipOut:
    if payload.end_date <= payload.start_date:
        raise HTTPException(422, "end_date must be after start_date")
    mgr = (
        await session.execute(
            text("""select reporting_manager from public.job_details
                    where employee_id=:e and is_active=1"""),
            {"e": payload.employee_id},
        )
    ).scalar()
    row = (
        await session.execute(
            text("""insert into ihrms.pip
                    (employee_id, manager_id, reason, objectives, start_date, end_date, created_by)
                    values (:e, :m, :r, :o, :s, :en, :by) returning id::text"""),
            {"e": payload.employee_id, "m": mgr, "r": payload.reason,
             "o": payload.objectives, "s": payload.start_date, "en": payload.end_date,
             "by": principal.employee_id},
        )
    ).scalar_one()
    await record_audit(
        session, principal, "pip.open", "employee", str(payload.employee_id),
        summary="Opened a performance improvement plan",
    )
    result = await _detail(session, row)
    await session.commit()
    return result


@router.get("", response_model=list[PipOut])
async def list_pips(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "managed",  # managed | mine
) -> list[PipOut]:
    if scope == "mine":
        where, params = "where p.employee_id = :me", {"me": principal.employee_id}
    elif scope == "managed":
        if principal.is_hr:
            where, params = "", {}
        else:
            where = """where p.employee_id in (
                         select employee_id from public.job_details
                         where reporting_manager = :me and is_active = 1)"""
            params = {"me": principal.employee_id}
    else:
        raise HTTPException(422, "Invalid scope")
    ids = (
        await session.execute(
            text(f"select id::text from ihrms.pip p {where} order by p.created_at desc"), params
        )
    ).scalars().all()
    return [await _detail(session, i) for i in ids]


class CheckpointIn(BaseModel):
    rating: Literal["on_track", "at_risk", "off_track"]
    note: str | None = Field(default=None, max_length=1000)


async def _assert_manages(session: AsyncSession, principal: Principal, employee_id: int) -> None:
    if principal.is_hr:
        return
    is_mgr = (
        await session.execute(
            text("""select 1 from public.job_details
                    where employee_id=:e and reporting_manager=:me and is_active=1"""),
            {"e": employee_id, "me": principal.employee_id},
        )
    ).scalar()
    if not is_mgr:
        raise HTTPException(403, "You do not manage this employee")


@router.post("/{pip_id}/checkpoint", response_model=PipOut)
async def add_checkpoint(
    pip_id: str,
    payload: CheckpointIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PipOut:
    p = (
        await session.execute(
            text("select employee_id, status from ihrms.pip where id=cast(:id as uuid)"),
            {"id": pip_id},
        )
    ).mappings().first()
    if p is None:
        raise HTTPException(404, "PIP not found")
    await _assert_manages(session, principal, p["employee_id"])
    if not is_open(p["status"]):
        raise HTTPException(409, "PIP is not active")
    await session.execute(
        text("""insert into ihrms.pip_checkpoint (pip_id, rating, note, created_by)
                values (cast(:id as uuid), :r, :n, :by)"""),
        {"id": pip_id, "r": payload.rating, "n": payload.note, "by": principal.employee_id},
    )
    await record_audit(
        session, principal, "pip.checkpoint", "employee", str(p["employee_id"]),
        summary=f"PIP checkpoint: {payload.rating}",
    )
    result = await _detail(session, pip_id)
    await session.commit()
    return result


class CloseIn(BaseModel):
    outcome: Literal["improved", "extended", "terminated", "closed"]


@router.post("/{pip_id}/close", response_model=PipOut)
async def close_pip(
    pip_id: str,
    payload: CloseIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> PipOut:
    if not is_valid_outcome(payload.outcome):
        raise HTTPException(422, "Invalid outcome")
    p = (
        await session.execute(
            text("select status from ihrms.pip where id=cast(:id as uuid)"), {"id": pip_id}
        )
    ).mappings().first()
    if p is None:
        raise HTTPException(404, "PIP not found")
    if not is_open(p["status"]):
        raise HTTPException(409, "PIP is already closed")
    await session.execute(
        text("update ihrms.pip set status=:s, updated_at=now() where id=cast(:id as uuid)"),
        {"s": payload.outcome, "id": pip_id},
    )
    await record_audit(
        session, principal, "pip.close", "pip", pip_id,
        summary=f"Closed PIP as {payload.outcome}",
    )
    result = await _detail(session, pip_id)
    await session.commit()
    return result

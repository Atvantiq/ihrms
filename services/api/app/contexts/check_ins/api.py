"""Check-ins API — log a self-reflection; managers read their team's.

An employee logs highlights/challenges/mood; their reporting manager (or HR)
can read their reports' check-ins. Tenant-scoped.
"""

from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.check_ins.service import mood_label
from app.contexts.identity.principal import Principal, get_current_principal
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/check-ins", tags=["check-ins"])


class CheckInOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    check_in_date: date
    highlights: str
    challenges: str | None = None
    mood: int
    mood_label: str
    created_at: datetime


class CheckInIn(BaseModel):
    check_in_date: date | None = None
    highlights: str = Field(min_length=1, max_length=1000)
    challenges: str | None = Field(default=None, max_length=1000)
    mood: int = Field(ge=1, le=5)


_SELECT = """
    select c.id::text, c.employee_id, c.check_in_date, c.highlights, c.challenges,
           c.mood, c.created_at,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
    from ihrms.check_in c
    left join public.employees e on e.employee_id = c.employee_id
"""


def _out(r: dict[str, Any]) -> CheckInOut:
    return CheckInOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
        check_in_date=r["check_in_date"], highlights=r["highlights"],
        challenges=r["challenges"], mood=r["mood"], mood_label=mood_label(r["mood"]),
        created_at=r["created_at"],
    )


@router.post("", response_model=CheckInOut, status_code=201)
async def log_check_in(
    payload: CheckInIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> CheckInOut:
    row = (
        await session.execute(
            text("""insert into ihrms.check_in
                    (employee_id, check_in_date, highlights, challenges, mood)
                    values (:e, :d, :h, :c, :m) returning id::text"""),
            {"e": principal.employee_id, "d": payload.check_in_date or date.today(),
             "h": payload.highlights, "c": payload.challenges, "m": payload.mood},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "check_in.log", "employee", str(principal.employee_id),
        summary="Logged a check-in",
    )
    out = (await session.execute(text(_SELECT + " where c.id=:id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.get("/mine", response_model=list[CheckInOut])
async def my_check_ins(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[CheckInOut]:
    rows = (
        await session.execute(
            text(_SELECT + " where c.employee_id=:e order by c.check_in_date desc limit 50"),
            {"e": principal.employee_id},
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


@router.get("/team", response_model=list[CheckInOut])
async def team_check_ins(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[CheckInOut]:
    """My reports' check-ins (HR sees everyone's)."""
    if principal.is_hr:
        where, params = "", {}
    else:
        where = """where c.employee_id in (
                     select employee_id from public.job_details
                     where reporting_manager = :me and is_active = 1)"""
        params = {"me": principal.employee_id}
    rows = (
        await session.execute(
            text(_SELECT + " " + where + " order by c.check_in_date desc limit 100"), params
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]

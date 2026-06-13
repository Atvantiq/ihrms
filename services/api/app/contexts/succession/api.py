"""Succession API — key positions + successor bench (HR).

Key positions carry their incumbent and a vacancy risk; each has a bench of
successor candidates with a readiness horizon. The list returns a derived
bench-strength status per position. Tenant-scoped; HR-only; reads kept before
commit (RLS tenant context).
"""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import ROLE_HR_ADMIN, Principal, require_roles
from app.contexts.succession.service import bench_strength
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/succession", tags=["succession"])
HR = require_roles(ROLE_HR_ADMIN)


class Candidate(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    readiness: str
    note: str | None = None


class Position(BaseModel):
    id: str
    title: str
    incumbent_id: int | None = None
    incumbent_name: str | None = None
    risk_level: str
    notes: str | None = None
    candidates: list[Candidate] = []
    bench_status: str
    ready_now: int


class PositionIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    incumbent_id: int | None = None
    risk_level: Literal["low", "medium", "high"] = "medium"
    notes: str | None = None


class CandidateIn(BaseModel):
    employee_id: int
    readiness: Literal["ready_now", "1_2_years", "3_5_years"] = "1_2_years"
    note: str | None = None


async def _candidates(session: AsyncSession, position_id: str) -> list[Candidate]:
    rows = (
        await session.execute(
            text("""select c.id::text, c.employee_id, c.readiness, c.note,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.succession_candidate c
                    left join public.employees e on e.employee_id = c.employee_id
                    where c.position_id = cast(:p as uuid)
                    order by case c.readiness when 'ready_now' then 0
                                              when '1_2_years' then 1 else 2 end"""),
            {"p": position_id},
        )
    ).mappings().all()
    return [
        Candidate(id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
                  readiness=r["readiness"], note=r["note"])
        for r in rows
    ]


def _position(row: dict[str, Any], candidates: list[Candidate]) -> Position:
    bench = bench_strength([c.readiness for c in candidates])
    return Position(
        id=row["id"], title=row["title"], incumbent_id=row["incumbent_id"],
        incumbent_name=row["incumbent_name"] or None, risk_level=row["risk_level"],
        notes=row["notes"], candidates=candidates,
        bench_status=bench.status, ready_now=bench.ready_now,
    )


_POS_SELECT = """
    select p.id::text, p.title, p.incumbent_id, p.risk_level, p.notes,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as incumbent_name
    from ihrms.key_position p
    left join public.employees e on e.employee_id = p.incumbent_id
"""


@router.get("/positions", response_model=list[Position])
async def list_positions(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[Position]:
    rows = (
        await session.execute(text(_POS_SELECT + " order by p.risk_level desc, p.title"))
    ).mappings().all()
    out: list[Position] = []
    for r in rows:
        out.append(_position(dict(r), await _candidates(session, r["id"])))
    return out


@router.post("/positions", response_model=Position, status_code=201)
async def add_position(
    payload: PositionIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Position:
    pid = (
        await session.execute(
            text("""insert into ihrms.key_position (title, incumbent_id, risk_level, notes)
                    values (:t, :i, :r, :n) returning id::text"""),
            {"t": payload.title, "i": payload.incumbent_id, "r": payload.risk_level,
             "n": payload.notes},
        )
    ).scalar_one()
    row = (
        await session.execute(text(_POS_SELECT + " where p.id = cast(:id as uuid)"),
                              {"id": pid})
    ).mappings().one()
    out = _position(dict(row), [])
    await session.commit()
    return out


@router.post("/positions/{position_id}/candidates", response_model=Position, status_code=201)
async def add_candidate(
    position_id: str,
    payload: CandidateIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Position:
    pos = (
        await session.execute(text(_POS_SELECT + " where p.id = cast(:id as uuid)"),
                              {"id": position_id})
    ).mappings().first()
    if pos is None:
        raise HTTPException(404, "Position not found")
    dup = (
        await session.execute(
            text("""select 1 from ihrms.succession_candidate
                    where position_id = cast(:p as uuid) and employee_id = :e"""),
            {"p": position_id, "e": payload.employee_id},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Already a successor for this position")
    await session.execute(
        text("""insert into ihrms.succession_candidate
                (position_id, employee_id, readiness, note)
                values (cast(:p as uuid), :e, :r, :n)"""),
        {"p": position_id, "e": payload.employee_id, "r": payload.readiness,
         "n": payload.note},
    )
    await record_audit(session, principal, "succession.add_candidate", "key_position",
                       position_id, summary=f"Successor {payload.employee_id} added")
    out = _position(dict(pos), await _candidates(session, position_id))
    await session.commit()
    return out


@router.delete("/positions/{position_id}/candidates/{candidate_id}", status_code=204)
async def remove_candidate(
    position_id: str,
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> None:
    await session.execute(
        text("""delete from ihrms.succession_candidate
                where id = cast(:c as uuid) and position_id = cast(:p as uuid)"""),
        {"c": candidate_id, "p": position_id},
    )
    await session.commit()

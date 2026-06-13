"""Career API — tracks, ranked levels, competency framework, placement.

HR builds the ladder (tracks → levels), the competency framework, and the
per-level expectations. Employees are placed on a level; "my ladder" shows
their level, its competency expectations and the next rung up. Tenant-scoped;
HR-only writes; reads kept before commit (RLS tenant context).
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.career.service import Rung, next_rung
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/career", tags=["career"])
HR = require_roles(ROLE_HR_ADMIN)


# ----------------------------------------------------------------- models

class Level(BaseModel):
    id: str
    name: str
    rank: int
    summary: str | None = None


class Track(BaseModel):
    id: str
    name: str
    description: str | None = None
    levels: list[Level] = []


class TrackIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    description: str | None = None


class LevelIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    rank: int = Field(ge=1, le=20)
    summary: str | None = None


class Competency(BaseModel):
    id: str
    name: str
    category: str | None = None
    description: str | None = None


class CompetencyIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    category: str | None = None
    description: str | None = None


class ExpectationIn(BaseModel):
    competency_id: str
    expectation: str = Field(min_length=1)


class Expectation(BaseModel):
    competency_id: str
    competency_name: str
    expectation: str


class PlacementIn(BaseModel):
    level_id: str


class MyLadder(BaseModel):
    employee_id: int
    track_name: str | None = None
    level: Level | None = None
    expectations: list[Expectation] = []
    next_level: Level | None = None


# ----------------------------------------------------------------- tracks

@router.get("/tracks", response_model=list[Track])
async def list_tracks(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[Track]:
    tracks = (
        await session.execute(
            text("select id::text, name, description from ihrms.career_track order by name")
        )
    ).mappings().all()
    levels = (
        await session.execute(
            text("""select id::text, track_id::text, name, rank, summary
                    from ihrms.career_level order by rank""")
        )
    ).mappings().all()
    by_track: dict[str, list[Level]] = {}
    for lv in levels:
        by_track.setdefault(lv["track_id"], []).append(
            Level(id=lv["id"], name=lv["name"], rank=lv["rank"], summary=lv["summary"])
        )
    return [
        Track(id=t["id"], name=t["name"], description=t["description"],
              levels=by_track.get(t["id"], []))
        for t in tracks
    ]


@router.post("/tracks", response_model=Track, status_code=201)
async def add_track(
    payload: TrackIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Track:
    row = (
        await session.execute(
            text("""insert into ihrms.career_track (name, description)
                    values (:n, :d) returning id::text, name, description"""),
            {"n": payload.name, "d": payload.description},
        )
    ).mappings().one()
    out = Track(id=row["id"], name=row["name"], description=row["description"], levels=[])
    await session.commit()
    return out


@router.post("/tracks/{track_id}/levels", response_model=Level, status_code=201)
async def add_level(
    track_id: str,
    payload: LevelIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Level:
    dup = (
        await session.execute(
            text("""select 1 from ihrms.career_level
                    where track_id = cast(:t as uuid) and rank = :r"""),
            {"t": track_id, "r": payload.rank},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "A level with that rank already exists on this track")
    row = (
        await session.execute(
            text("""insert into ihrms.career_level (track_id, name, rank, summary)
                    values (cast(:t as uuid), :n, :r, :s)
                    returning id::text, name, rank, summary"""),
            {"t": track_id, "n": payload.name, "r": payload.rank, "s": payload.summary},
        )
    ).mappings().one()
    out = Level(**dict(row))
    await session.commit()
    return out


# ----------------------------------------------------------------- competencies

@router.get("/competencies", response_model=list[Competency])
async def list_competencies(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[Competency]:
    rows = (
        await session.execute(
            text("""select id::text, name, category, description
                    from ihrms.competency order by category nulls last, name""")
        )
    ).mappings().all()
    return [Competency(**dict(r)) for r in rows]


@router.post("/competencies", response_model=Competency, status_code=201)
async def add_competency(
    payload: CompetencyIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Competency:
    row = (
        await session.execute(
            text("""insert into ihrms.competency (name, category, description)
                    values (:n, :c, :d) returning id::text, name, category, description"""),
            {"n": payload.name, "c": payload.category, "d": payload.description},
        )
    ).mappings().one()
    out = Competency(**dict(row))
    await session.commit()
    return out


# ----------------------------------------------------------------- expectations

async def _expectations(session: AsyncSession, level_id: str) -> list[Expectation]:
    rows = (
        await session.execute(
            text("""select lc.competency_id::text, c.name as competency_name, lc.expectation
                    from ihrms.level_competency lc
                    join ihrms.competency c on c.id = lc.competency_id
                    where lc.level_id = cast(:l as uuid)
                    order by c.name"""),
            {"l": level_id},
        )
    ).mappings().all()
    return [Expectation(**dict(r)) for r in rows]


@router.get("/levels/{level_id}/expectations", response_model=list[Expectation])
async def get_expectations(
    level_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[Expectation]:
    return await _expectations(session, level_id)


@router.post("/levels/{level_id}/expectations", response_model=list[Expectation], status_code=201)
async def set_expectation(
    level_id: str,
    payload: ExpectationIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[Expectation]:
    await session.execute(
        text("""insert into ihrms.level_competency (level_id, competency_id, expectation)
                values (cast(:l as uuid), cast(:c as uuid), :e)
                on conflict (level_id, competency_id)
                do update set expectation = excluded.expectation"""),
        {"l": level_id, "c": payload.competency_id, "e": payload.expectation},
    )
    out = await _expectations(session, level_id)
    await session.commit()
    return out


# ----------------------------------------------------------------- placement

async def _level(session: AsyncSession, level_id: str) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text("""select l.id::text, l.name, l.rank, l.summary, l.track_id::text,
                       t.name as track_name
                    from ihrms.career_level l
                    join ihrms.career_track t on t.id = l.track_id
                    where l.id = cast(:id as uuid)"""),
            {"id": level_id},
        )
    ).mappings().first()
    return dict(row) if row is not None else None


@router.put("/employees/{employee_id}/placement", response_model=MyLadder)
async def place_employee(
    employee_id: int,
    payload: PlacementIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> MyLadder:
    lvl = await _level(session, payload.level_id)
    if lvl is None:
        raise HTTPException(404, "Level not found")
    await session.execute(
        text("""insert into ihrms.employee_career_level (employee_id, level_id)
                values (:e, cast(:l as uuid))
                on conflict (tenant_id, employee_id)
                do update set level_id = excluded.level_id, placed_on = current_date"""),
        {"e": employee_id, "l": payload.level_id},
    )
    await record_audit(session, principal, "career.place", "employee", str(employee_id),
                       summary=f"Placed on {lvl['name']}")
    out = await _my_ladder(session, employee_id)
    await session.commit()
    return out


async def _my_ladder(session: AsyncSession, employee_id: int) -> MyLadder:
    placement = (
        await session.execute(
            text("""select level_id::text from ihrms.employee_career_level
                    where employee_id = :e"""),
            {"e": employee_id},
        )
    ).scalar()
    if placement is None:
        return MyLadder(employee_id=employee_id)
    lvl = await _level(session, placement)
    assert lvl is not None
    rungs = (
        await session.execute(
            text("""select id::text, name, rank from ihrms.career_level
                    where track_id = cast(:t as uuid)"""),
            {"t": lvl["track_id"]},
        )
    ).mappings().all()
    nxt = next_rung(
        [Rung(level_id=r["id"], name=r["name"], rank=r["rank"]) for r in rungs],
        lvl["rank"],
    )
    next_level = None
    if nxt is not None:
        nrow = await _level(session, nxt.level_id)
        if nrow is not None:
            next_level = Level(id=nrow["id"], name=nrow["name"], rank=nrow["rank"],
                               summary=nrow["summary"])
    return MyLadder(
        employee_id=employee_id, track_name=lvl["track_name"],
        level=Level(id=lvl["id"], name=lvl["name"], rank=lvl["rank"], summary=lvl["summary"]),
        expectations=await _expectations(session, lvl["id"]),
        next_level=next_level,
    )


@router.get("/employees/{employee_id}/ladder", response_model=MyLadder)
async def my_ladder(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> MyLadder:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own ladder")
    return await _my_ladder(session, employee_id)

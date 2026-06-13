"""Growth API — development plans, action items & mentorship.

The growth side of performance. An employee owns their development plans
(focus + objective + target) and a checklist of actions; HR can view anyone's
and manage mentorship pairings. Plans gate read/write to the owner-or-HR; reads
are kept before commit so the per-request RLS tenant context still holds.
"""

from datetime import date
from typing import Annotated, Any, Literal

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
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/growth", tags=["growth"])
HR = require_roles(ROLE_HR_ADMIN)


# ----------------------------------------------------------------- models

class ActionItem(BaseModel):
    id: str
    action: str
    status: str


class DevelopmentPlan(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    focus_area: str
    objective: str
    target_date: date | None = None
    status: str
    actions: list[ActionItem] = []


class PlanIn(BaseModel):
    employee_id: int | None = None  # HR may target another employee; else self
    focus_area: str = Field(min_length=1, max_length=120)
    objective: str = Field(min_length=1)
    target_date: date | None = None


class PlanPatch(BaseModel):
    status: Literal["active", "achieved", "dropped"]


class ActionIn(BaseModel):
    action: str = Field(min_length=1, max_length=300)


class Mentorship(BaseModel):
    id: str
    mentor_id: int
    mentor_name: str | None = None
    mentee_id: int
    mentee_name: str | None = None
    focus: str | None = None
    status: str
    started_on: date


class MentorshipIn(BaseModel):
    mentor_id: int
    mentee_id: int
    focus: str | None = None


# ----------------------------------------------------------------- helpers

async def _actions(session: AsyncSession, plan_id: str) -> list[ActionItem]:
    rows = (
        await session.execute(
            text("""select id::text, action, status from ihrms.development_action
                    where plan_id = cast(:p as uuid) order by created_at"""),
            {"p": plan_id},
        )
    ).mappings().all()
    return [ActionItem(**dict(r)) for r in rows]


async def _plan(session: AsyncSession, plan_id: str) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text("""select p.id::text, p.employee_id, p.focus_area, p.objective,
                       p.target_date, p.status,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.development_plan p
                    left join public.employees e on e.employee_id = p.employee_id
                    where p.id = cast(:id as uuid)"""),
            {"id": plan_id},
        )
    ).mappings().first()
    return dict(row) if row is not None else None


async def _require_plan_access(
    session: AsyncSession, plan_id: str, principal: Principal
) -> dict[str, Any]:
    row = await _plan(session, plan_id)
    if row is None:
        raise HTTPException(404, "Plan not found")
    if row["employee_id"] != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "Not your development plan")
    return dict(row)


async def _plan_out(session: AsyncSession, row: dict[str, Any]) -> DevelopmentPlan:
    return DevelopmentPlan(
        id=row["id"], employee_id=row["employee_id"], employee_name=row["nm"],
        focus_area=row["focus_area"], objective=row["objective"],
        target_date=row["target_date"], status=row["status"],
        actions=await _actions(session, row["id"]),
    )


# ----------------------------------------------------------------- plans

@router.get("/plans", response_model=list[DevelopmentPlan])
async def list_plans(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> list[DevelopmentPlan]:
    target = employee_id if employee_id is not None else principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own plans")
    rows = (
        await session.execute(
            text("""select p.id::text, p.employee_id, p.focus_area, p.objective,
                       p.target_date, p.status,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.development_plan p
                    left join public.employees e on e.employee_id = p.employee_id
                    where p.employee_id = :e order by p.created_at desc"""),
            {"e": target},
        )
    ).mappings().all()
    return [await _plan_out(session, dict(r)) for r in rows]


@router.post("/plans", response_model=DevelopmentPlan, status_code=201)
async def create_plan(
    payload: PlanIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DevelopmentPlan:
    target = payload.employee_id if payload.employee_id is not None else principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "Only HR can create a plan for someone else")
    pid = (
        await session.execute(
            text("""insert into ihrms.development_plan
                    (employee_id, focus_area, objective, target_date, created_by)
                    values (:e, :f, :o, :t, :by) returning id::text"""),
            {"e": target, "f": payload.focus_area, "o": payload.objective,
             "t": payload.target_date, "by": principal.employee_id},
        )
    ).scalar_one()
    row = await _plan(session, pid)
    assert row is not None
    out = await _plan_out(session, dict(row))
    await session.commit()
    return out


@router.patch("/plans/{plan_id}", response_model=DevelopmentPlan)
async def update_plan_status(
    plan_id: str,
    payload: PlanPatch,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DevelopmentPlan:
    await _require_plan_access(session, plan_id, principal)
    await session.execute(
        text("""update ihrms.development_plan set status=:s, updated_at=now()
                where id = cast(:id as uuid)"""),
        {"s": payload.status, "id": plan_id},
    )
    row = await _plan(session, plan_id)
    assert row is not None
    out = await _plan_out(session, dict(row))
    await session.commit()
    return out


@router.post("/plans/{plan_id}/actions", response_model=DevelopmentPlan, status_code=201)
async def add_action(
    plan_id: str,
    payload: ActionIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DevelopmentPlan:
    row = await _require_plan_access(session, plan_id, principal)
    await session.execute(
        text("""insert into ihrms.development_action (plan_id, action)
                values (cast(:p as uuid), :a)"""),
        {"p": plan_id, "a": payload.action},
    )
    out = await _plan_out(session, row)
    await session.commit()
    return out


@router.post("/plans/{plan_id}/actions/{action_id}/toggle", response_model=DevelopmentPlan)
async def toggle_action(
    plan_id: str,
    action_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DevelopmentPlan:
    row = await _require_plan_access(session, plan_id, principal)
    await session.execute(
        text("""update ihrms.development_action
                set status = case when status='done' then 'pending' else 'done' end
                where id = cast(:a as uuid) and plan_id = cast(:p as uuid)"""),
        {"a": action_id, "p": plan_id},
    )
    out = await _plan_out(session, row)
    await session.commit()
    return out


# ----------------------------------------------------------------- mentorship

_MENTOR_SELECT = """
    select m.id::text, m.mentor_id, m.mentee_id, m.focus, m.status, m.started_on,
           trim(concat(mt.first_name,' ',coalesce(mt.last_name,''))) as mentor_name,
           trim(concat(me.first_name,' ',coalesce(me.last_name,''))) as mentee_name
    from ihrms.mentorship m
    left join public.employees mt on mt.employee_id = m.mentor_id
    left join public.employees me on me.employee_id = m.mentee_id
"""


def _mentor_out(r: dict[str, Any]) -> Mentorship:
    return Mentorship(
        id=r["id"], mentor_id=r["mentor_id"], mentor_name=r["mentor_name"] or None,
        mentee_id=r["mentee_id"], mentee_name=r["mentee_name"] or None,
        focus=r["focus"], status=r["status"], started_on=r["started_on"],
    )


@router.get("/mentorships", response_model=list[Mentorship])
async def list_mentorships(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[Mentorship]:
    # employees see pairings they are part of; HR sees all
    where, params = "", {}
    if not principal.is_hr:
        where = " where m.mentor_id = :me or m.mentee_id = :me"
        params = {"me": principal.employee_id}
    rows = (
        await session.execute(
            text(_MENTOR_SELECT + where + " order by m.started_on desc"), params
        )
    ).mappings().all()
    return [_mentor_out(dict(r)) for r in rows]


@router.post("/mentorships", response_model=Mentorship, status_code=201)
async def create_mentorship(
    payload: MentorshipIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Mentorship:
    if payload.mentor_id == payload.mentee_id:
        raise HTTPException(422, "Mentor and mentee must differ")
    for eid in (payload.mentor_id, payload.mentee_id):
        ok = (
            await session.execute(
                text("select 1 from public.employees where employee_id = :e"), {"e": eid}
            )
        ).scalar()
        if ok is None:
            raise HTTPException(404, f"Employee {eid} not found")
    mid = (
        await session.execute(
            text("""insert into ihrms.mentorship (mentor_id, mentee_id, focus)
                    values (:mt, :me, :f) returning id::text"""),
            {"mt": payload.mentor_id, "me": payload.mentee_id, "f": payload.focus},
        )
    ).scalar_one()
    await record_audit(session, principal, "mentorship.create", "mentorship", mid,
                       summary=f"Paired {payload.mentor_id} → {payload.mentee_id}")
    row = (
        await session.execute(
            text(_MENTOR_SELECT + " where m.id = cast(:id as uuid)"), {"id": mid}
        )
    ).mappings().one()
    out = _mentor_out(dict(row))
    await session.commit()
    return out


@router.post("/mentorships/{mentorship_id}/close", response_model=Mentorship)
async def close_mentorship(
    mentorship_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Mentorship:
    res = await session.execute(
        text("""update ihrms.mentorship set status='closed'
                where id = cast(:id as uuid) returning id::text"""),
        {"id": mentorship_id},
    )
    if res.scalar() is None:
        raise HTTPException(404, "Mentorship not found")
    row = (
        await session.execute(
            text(_MENTOR_SELECT + " where m.id = cast(:id as uuid)"), {"id": mentorship_id}
        )
    ).mappings().one()
    out = _mentor_out(dict(row))
    await session.commit()
    return out

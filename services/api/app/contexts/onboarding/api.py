"""Onboarding API — template checklist + per-hire task instances.

HR maintains a master onboarding template; instantiating it for a new hire
copies the active template tasks into that employee's checklist. The employee
and their manager/IT/HR work the checklist; an overview lists every in-flight
onboarding with its progress. Tenant-scoped; reads kept before commit (RLS).
"""

from datetime import date
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
from app.contexts.onboarding.service import progress
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/onboarding", tags=["onboarding"])
HR = require_roles(ROLE_HR_ADMIN)

OwnerRole = Literal["hr", "manager", "it", "employee"]


# ----------------------------------------------------------------- template

class TemplateTask(BaseModel):
    id: str
    title: str
    owner_role: str
    sort_order: int


class TemplateTaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    owner_role: OwnerRole = "hr"
    sort_order: int = 100


@router.get("/template", response_model=list[TemplateTask])
async def get_template(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[TemplateTask]:
    rows = (
        await session.execute(
            text("""select id::text, title, owner_role, sort_order
                    from ihrms.onboarding_template_task
                    where is_active order by sort_order, title""")
        )
    ).mappings().all()
    return [TemplateTask(**dict(r)) for r in rows]


@router.post("/template", response_model=TemplateTask, status_code=201)
async def add_template_task(
    payload: TemplateTaskIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> TemplateTask:
    row = (
        await session.execute(
            text("""insert into ihrms.onboarding_template_task (title, owner_role, sort_order)
                    values (:t, :o, :s)
                    returning id::text, title, owner_role, sort_order"""),
            {"t": payload.title, "o": payload.owner_role, "s": payload.sort_order},
        )
    ).mappings().one()
    out = TemplateTask(**dict(row))
    await session.commit()
    return out


@router.delete("/template/{task_id}", status_code=204)
async def remove_template_task(
    task_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> None:
    await session.execute(
        text("""update ihrms.onboarding_template_task set is_active=false
                where id = cast(:id as uuid)"""),
        {"id": task_id},
    )
    await session.commit()


# ----------------------------------------------------------------- per-hire

class OnboardingTask(BaseModel):
    id: str
    title: str
    owner_role: str
    status: str
    completed_on: date | None = None
    sort_order: int


class ChecklistOut(BaseModel):
    employee_id: int
    tasks: list[OnboardingTask]
    done: int
    total: int
    pct: int


async def _checklist(session: AsyncSession, employee_id: int) -> ChecklistOut:
    rows = (
        await session.execute(
            text("""select id::text, title, owner_role, status, completed_on, sort_order
                    from ihrms.onboarding_task where employee_id = :e
                    order by sort_order, title"""),
            {"e": employee_id},
        )
    ).mappings().all()
    tasks = [OnboardingTask(**dict(r)) for r in rows]
    p = progress([t.status for t in tasks])
    return ChecklistOut(
        employee_id=employee_id, tasks=tasks, done=p.done, total=p.total, pct=p.pct,
    )


@router.get("/employees/{employee_id}/tasks", response_model=ChecklistOut)
async def get_checklist(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ChecklistOut:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own onboarding")
    return await _checklist(session, employee_id)


@router.post("/employees/{employee_id}/generate", response_model=ChecklistOut, status_code=201)
async def generate_checklist(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ChecklistOut:
    """Instantiate the active template into this employee's checklist (idempotent)."""
    emp = (
        await session.execute(
            text("select 1 from public.employees where employee_id = :e"),
            {"e": employee_id},
        )
    ).scalar()
    if emp is None:
        raise HTTPException(404, "Employee not found")
    existing = (
        await session.execute(
            text("select count(*) from ihrms.onboarding_task where employee_id = :e"),
            {"e": employee_id},
        )
    ).scalar_one()
    if existing == 0:
        await session.execute(
            text("""insert into ihrms.onboarding_task
                    (employee_id, title, owner_role, sort_order)
                    select :e, title, owner_role, sort_order
                    from ihrms.onboarding_template_task where is_active"""),
            {"e": employee_id},
        )
        await record_audit(
            session, principal, "onboarding.generate", "employee", str(employee_id),
            summary=f"Onboarding checklist generated for {employee_id}",
        )
    out = await _checklist(session, employee_id)
    await session.commit()
    return out


@router.post("/employees/{employee_id}/tasks/{task_id}/toggle", response_model=ChecklistOut)
async def toggle_task(
    employee_id: int,
    task_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ChecklistOut:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only update your own onboarding")
    await session.execute(
        text("""update ihrms.onboarding_task
                set status = case when status='done' then 'pending' else 'done' end,
                    completed_on = case when status='done' then null else current_date end
                where id = cast(:t as uuid) and employee_id = :e"""),
        {"t": task_id, "e": employee_id},
    )
    out = await _checklist(session, employee_id)
    await session.commit()
    return out


class OnboardingSummary(BaseModel):
    employee_id: int
    employee_name: str | None = None
    done: int
    total: int
    pct: int


@router.get("/in-progress", response_model=list[OnboardingSummary])
async def in_progress(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[OnboardingSummary]:
    """Every employee with an onboarding checklist that isn't fully complete."""
    rows = (
        await session.execute(
            text("""select t.employee_id,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm,
                       count(*) filter (where t.status='done') as done,
                       count(*) as total
                    from ihrms.onboarding_task t
                    left join public.employees e on e.employee_id = t.employee_id
                    group by t.employee_id, nm
                    having count(*) filter (where t.status='done') < count(*)
                    order by nm""")
        )
    ).mappings().all()
    return [
        OnboardingSummary(
            employee_id=r["employee_id"], employee_name=r["nm"] or None,
            done=r["done"], total=r["total"],
            pct=round(r["done"] * 100 / r["total"]) if r["total"] else 0,
        )
        for r in rows
    ]

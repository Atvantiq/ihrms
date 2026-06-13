"""Timesheet API — projects (HR), entries + weekly submit (self), approval."""

from datetime import date
from decimal import Decimal
from typing import Annotated

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
from app.contexts.timesheet.service import overtime, week_dates, week_start
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/timesheet", tags=["timesheet"])


# ---------------------------------------------------------------- projects

class ProjectOut(BaseModel):
    id: str
    code: str
    name: str
    client: str | None = None


class ProjectIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    name: str = Field(min_length=1, max_length=120)
    client: str | None = None


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[ProjectOut]:
    rows = (
        await session.execute(
            text("""select id::text, code, name, client from ihrms.project
                    where is_active order by code""")
        )
    ).mappings().all()
    return [ProjectOut(**dict(r)) for r in rows]


@router.post("/projects", response_model=ProjectOut, status_code=201)
async def add_project(
    payload: ProjectIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> ProjectOut:
    dup = (
        await session.execute(
            text("select 1 from ihrms.project where lower(code) = lower(:c) and is_active"),
            {"c": payload.code.strip()},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "A project with this code already exists")
    row = (
        await session.execute(
            text("""insert into ihrms.project (code, name, client)
                    values (:c, :n, :cl) returning id::text, code, name, client"""),
            {"c": payload.code.strip(), "n": payload.name.strip(), "cl": payload.client},
        )
    ).mappings().one()
    out = ProjectOut(**dict(row))
    await session.commit()
    return out


# ---------------------------------------------------------------- week view

class EntryCell(BaseModel):
    project_id: str
    work_date: date
    hours: Decimal


class WeekOut(BaseModel):
    employee_id: int
    week_start: date
    dates: list[date]
    status: str
    entries: list[EntryCell]
    total_hours: Decimal
    overtime: Decimal
    approver_name: str | None = None
    decision_note: str | None = None
    can_decide: bool = False


async def _week(
    session: AsyncSession, employee_id: int, ws: date, principal: Principal
) -> WeekOut:
    dates = week_dates(ws)
    entries = [
        EntryCell(project_id=r["project_id"], work_date=r["work_date"], hours=r["hours"])
        for r in (
            await session.execute(
                text("""select project_id::text, work_date, hours
                        from ihrms.timesheet_entry
                        where employee_id = :emp and work_date between :s and :e"""),
                {"emp": employee_id, "s": dates[0], "e": dates[-1]},
            )
        ).mappings().all()
    ]
    total = sum((e.hours for e in entries), Decimal(0))
    wk = (
        await session.execute(
            text("""select status, approver_id, decision_note from ihrms.timesheet_week
                    where employee_id = :emp and week_start = :ws"""),
            {"emp": employee_id, "ws": ws},
        )
    ).mappings().first()
    status = wk["status"] if wk else "draft"

    approver_name = None
    if wk and wk["approver_id"]:
        approver_name = (
            await session.execute(
                text("""select trim(concat(first_name,' ',coalesce(last_name,'')))
                        from public.employees where employee_id = :id"""),
                {"id": wk["approver_id"]},
            )
        ).scalar()

    mgr = (
        await session.execute(
            text("""select reporting_manager from public.job_details
                    where employee_id = :id and is_active = 1 limit 1"""),
            {"id": employee_id},
        )
    ).scalar()
    can_decide = status == "submitted" and employee_id != principal.employee_id and (
        principal.is_hr or mgr == principal.employee_id
    )

    return WeekOut(
        employee_id=employee_id, week_start=ws, dates=dates, status=status,
        entries=entries, total_hours=total, overtime=overtime(total),
        approver_name=approver_name,
        decision_note=wk["decision_note"] if wk else None,
        can_decide=can_decide,
    )


@router.get("/week", response_model=WeekOut)
async def get_week(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    week_of: date,
    employee_id: int | None = None,
) -> WeekOut:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own timesheet")
    return await _week(session, target, week_start(week_of), principal)


class EntryIn(BaseModel):
    project_id: str
    work_date: date
    hours: Decimal = Field(ge=0, le=24)


@router.post("/entries", response_model=WeekOut)
async def log_entry(
    payload: EntryIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> WeekOut:
    ws = week_start(payload.work_date)
    locked = (
        await session.execute(
            text("""select status from ihrms.timesheet_week
                    where employee_id = :emp and week_start = :ws"""),
            {"emp": principal.employee_id, "ws": ws},
        )
    ).scalar()
    if locked in ("submitted", "approved"):
        raise HTTPException(409, f"This week is {locked} and cannot be edited")

    await session.execute(
        text("""insert into ihrms.timesheet_entry
                (employee_id, work_date, project_id, hours)
                values (:emp, :d, :p, :h)
                on conflict (tenant_id, employee_id, work_date, project_id)
                do update set hours = excluded.hours, updated_at = now()"""),
        {"emp": principal.employee_id, "d": payload.work_date,
         "p": payload.project_id, "h": payload.hours},
    )
    result = await _week(session, principal.employee_id, ws, principal)
    await session.commit()
    return result


@router.post("/week/submit", response_model=WeekOut)
async def submit_week(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    week_of: date,
) -> WeekOut:
    ws = week_start(week_of)
    week = await _week(session, principal.employee_id, ws, principal)
    if week.total_hours <= 0:
        raise HTTPException(409, "Cannot submit an empty timesheet")
    await session.execute(
        text("""insert into ihrms.timesheet_week
                (employee_id, week_start, status, total_hours)
                values (:emp, :ws, 'submitted', :t)
                on conflict (tenant_id, employee_id, week_start)
                do update set status = 'submitted', total_hours = :t, updated_at = now()
                where ihrms.timesheet_week.status in ('draft','rejected')"""),
        {"emp": principal.employee_id, "ws": ws, "t": week.total_hours},
    )
    await record_audit(
        session, principal, "timesheet.submit", "timesheet_week", str(ws),
        summary=f"Submitted week of {ws} · {week.total_hours}h",
    )
    result = await _week(session, principal.employee_id, ws, principal)
    await session.commit()
    return result


class Decision(BaseModel):
    employee_id: int
    week_of: date
    note: str | None = None


@router.post("/week/approve", response_model=WeekOut)
async def approve_week(
    payload: Decision,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> WeekOut:
    return await _decide(session, principal, payload, "approved")


@router.post("/week/reject", response_model=WeekOut)
async def reject_week(
    payload: Decision,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> WeekOut:
    return await _decide(session, principal, payload, "rejected")


async def _decide(
    session: AsyncSession, principal: Principal, payload: Decision, outcome: str
) -> WeekOut:
    ws = week_start(payload.week_of)
    week = await _week(session, payload.employee_id, ws, principal)
    if not week.can_decide:
        raise HTTPException(403, "Not submitted, or you cannot decide this timesheet")
    await session.execute(
        text("""update ihrms.timesheet_week set status = :st, approver_id = :by,
                decision_note = :note, decided_at = now(), updated_at = now()
                where employee_id = :emp and week_start = :ws"""),
        {"st": outcome, "by": principal.employee_id, "note": payload.note,
         "emp": payload.employee_id, "ws": ws},
    )
    await record_audit(
        session, principal, f"timesheet.{outcome[:6]}", "timesheet_week", str(ws),
        summary=f"{outcome.capitalize()} timesheet week of {ws}",
    )
    result = await _week(session, payload.employee_id, ws, principal)
    await session.commit()
    return result

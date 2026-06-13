"""Helpdesk API — raise a ticket, assign, move through its lifecycle.

Any employee raises a ticket; HR assigns it and drives status to resolved/
closed (with a resolution note). Tenant-scoped; audited.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.helpdesk.service import CATEGORIES, can_transition
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/tickets", tags=["helpdesk"])
HR = require_roles(ROLE_HR_ADMIN)


class TicketOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    category: str
    subject: str
    description: str
    priority: str
    status: str
    assignee_id: int | None = None
    assignee_name: str | None = None
    resolution: str | None = None
    created_at: datetime
    resolved_at: datetime | None = None


class TicketIn(BaseModel):
    category: Literal["payroll", "leave", "it", "facilities", "hr_policy", "other"]
    subject: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=2000)
    priority: Literal["low", "medium", "high"] = "medium"


_SELECT = """
    select t.id::text, t.employee_id, t.category, t.subject, t.description,
           t.priority, t.status, t.assignee_id, t.resolution, t.created_at, t.resolved_at,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as emp_name,
           trim(concat(a.first_name,' ',coalesce(a.last_name,''))) as asg_name
    from ihrms.ticket t
    left join public.employees e on e.employee_id = t.employee_id
    left join public.employees a on a.employee_id = t.assignee_id
"""


def _out(r: dict[str, Any]) -> TicketOut:
    return TicketOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["emp_name"] or None,
        category=r["category"], subject=r["subject"], description=r["description"],
        priority=r["priority"], status=r["status"], assignee_id=r["assignee_id"],
        assignee_name=r["asg_name"] or None, resolution=r["resolution"],
        created_at=r["created_at"], resolved_at=r["resolved_at"],
    )


@router.get("/categories", response_model=list[str])
async def list_categories(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[str]:
    return CATEGORIES


@router.post("", response_model=TicketOut, status_code=201)
async def raise_ticket(
    payload: TicketIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> TicketOut:
    row = (
        await session.execute(
            text("""insert into ihrms.ticket
                    (employee_id, category, subject, description, priority)
                    values (:e, :c, :s, :d, :p) returning id::text"""),
            {"e": principal.employee_id, "c": payload.category, "s": payload.subject,
             "d": payload.description, "p": payload.priority},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "ticket.raise", "ticket", row["id"],
        summary=f"Raised {payload.category} ticket: {payload.subject}",
    )
    out = (await session.execute(text(_SELECT + " where t.id=:id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.get("", response_model=list[TicketOut])
async def list_tickets(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "mine",  # mine | assigned | all
) -> list[TicketOut]:
    if scope == "mine":
        where, params = "where t.employee_id = :me", {"me": principal.employee_id}
    elif scope == "assigned":
        where, params = "where t.assignee_id = :me", {"me": principal.employee_id}
    elif scope == "all":
        if not principal.is_hr:
            raise HTTPException(403, "Only HR can view all tickets")
        where, params = "", {}
    else:
        raise HTTPException(422, "Invalid scope")
    rows = (
        await session.execute(
            text(_SELECT + " " + where + " order by "
                 "(t.status in ('open','in_progress')) desc, t.created_at desc"),
            params,
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


class AssignIn(BaseModel):
    assignee_id: int


@router.post("/{ticket_id}/assign", response_model=TicketOut)
async def assign_ticket(
    ticket_id: str,
    payload: AssignIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> TicketOut:
    res = (
        await session.execute(
            text("""update ihrms.ticket set assignee_id=:a,
                    status=case when status='open' then 'in_progress' else status end,
                    updated_at=now() where id=cast(:id as uuid) returning id"""),
            {"a": payload.assignee_id, "id": ticket_id},
        )
    ).scalar()
    if res is None:
        raise HTTPException(404, "Ticket not found")
    await record_audit(
        session, principal, "ticket.assign", "ticket", ticket_id,
        summary=f"Assigned to {payload.assignee_id}",
    )
    out = (await session.execute(text(_SELECT + " where t.id=:id"),
                                 {"id": ticket_id})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


class StatusIn(BaseModel):
    status: Literal["in_progress", "resolved", "closed"]
    resolution: str | None = Field(default=None, max_length=2000)


@router.post("/{ticket_id}/status", response_model=TicketOut)
async def set_status(
    ticket_id: str,
    payload: StatusIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> TicketOut:
    t = (
        await session.execute(
            text("""select employee_id, assignee_id, status from ihrms.ticket
                    where id=cast(:id as uuid)"""),
            {"id": ticket_id},
        )
    ).mappings().first()
    if t is None:
        raise HTTPException(404, "Ticket not found")
    # HR or the assignee may progress a ticket
    if not principal.is_hr and t["assignee_id"] != principal.employee_id:
        raise HTTPException(403, "Only HR or the assignee can update this ticket")
    if not can_transition(t["status"], payload.status):
        raise HTTPException(409, f"Cannot move from {t['status']} to {payload.status}")
    resolved_at = "now()" if payload.status == "resolved" else "resolved_at"
    await session.execute(
        text(f"""update ihrms.ticket set status=:s, resolution=coalesce(:r, resolution),
                resolved_at={resolved_at}, updated_at=now() where id=cast(:id as uuid)"""),
        {"s": payload.status, "r": payload.resolution, "id": ticket_id},
    )
    await record_audit(
        session, principal, "ticket.status", "ticket", ticket_id,
        summary=f"Ticket -> {payload.status}",
    )
    out = (await session.execute(text(_SELECT + " where t.id=:id"),
                                 {"id": ticket_id})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result

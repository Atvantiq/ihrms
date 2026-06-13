"""Feedback & recognition API.

Anyone can give private feedback or public recognition (with a value badge) to a
colleague. You see feedback addressed to you, what you've given, and a company
recognition wall of public kudos. Tenant-scoped.
"""

from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import Principal, get_current_principal
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/feedback", tags=["feedback"])

# Recognition value badges (Atvantiq values).
BADGES = ["teamwork", "ownership", "innovation", "customer-first", "excellence"]


class FeedbackOut(BaseModel):
    id: str
    from_employee_id: int
    from_name: str | None = None
    to_employee_id: int
    to_name: str | None = None
    kind: str
    badge: str | None = None
    visibility: str
    message: str
    created_at: datetime


class FeedbackIn(BaseModel):
    to_employee_id: int
    kind: Literal["feedback", "recognition"] = "feedback"
    badge: str | None = None
    visibility: Literal["private", "public"] = "private"
    message: str = Field(min_length=1, max_length=1000)


_SELECT = """
    select f.id::text, f.from_employee_id, f.to_employee_id, f.kind, f.badge,
           f.visibility, f.message, f.created_at,
           trim(concat(fe.first_name,' ',coalesce(fe.last_name,''))) as from_name,
           trim(concat(te.first_name,' ',coalesce(te.last_name,''))) as to_name
    from ihrms.feedback f
    left join public.employees fe on fe.employee_id = f.from_employee_id
    left join public.employees te on te.employee_id = f.to_employee_id
"""


def _out(r: dict[str, Any]) -> FeedbackOut:
    return FeedbackOut(
        id=r["id"], from_employee_id=r["from_employee_id"], from_name=r["from_name"] or None,
        to_employee_id=r["to_employee_id"], to_name=r["to_name"] or None, kind=r["kind"],
        badge=r["badge"], visibility=r["visibility"], message=r["message"],
        created_at=r["created_at"],
    )


@router.get("/badges", response_model=list[str])
async def list_badges(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[str]:
    return BADGES


@router.post("", response_model=FeedbackOut, status_code=201)
async def give_feedback(
    payload: FeedbackIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> FeedbackOut:
    if payload.to_employee_id == principal.employee_id:
        raise HTTPException(409, "You cannot give feedback to yourself")
    if payload.badge is not None and payload.badge not in BADGES:
        raise HTTPException(404, "Unknown recognition badge")
    target = (
        await session.execute(
            text("select 1 from public.employees where employee_id=:e and is_active=1"),
            {"e": payload.to_employee_id},
        )
    ).scalar()
    if target is None:
        raise HTTPException(404, "Recipient not found")
    row = (
        await session.execute(
            text("""insert into ihrms.feedback
                    (from_employee_id, to_employee_id, kind, badge, visibility, message)
                    values (:fr, :to, :k, :b, :v, :m) returning id::text"""),
            {"fr": principal.employee_id, "to": payload.to_employee_id, "k": payload.kind,
             "b": payload.badge, "v": payload.visibility, "m": payload.message},
        )
    ).mappings().one()
    await record_audit(
        session, principal, f"feedback.{payload.kind}", "employee",
        str(payload.to_employee_id), summary=f"Gave {payload.kind}",
    )
    out = (await session.execute(text(_SELECT + " where f.id=:id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.get("/received", response_model=list[FeedbackOut])
async def received(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> list[FeedbackOut]:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own feedback")
    rows = (
        await session.execute(
            text(_SELECT + " where f.to_employee_id=:e order by f.created_at desc"),
            {"e": target},
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


@router.get("/given", response_model=list[FeedbackOut])
async def given(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[FeedbackOut]:
    rows = (
        await session.execute(
            text(_SELECT + " where f.from_employee_id=:e order by f.created_at desc"),
            {"e": principal.employee_id},
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


@router.get("/wall", response_model=list[FeedbackOut])
async def wall(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[FeedbackOut]:
    """Public recognition feed — visible to everyone."""
    rows = (
        await session.execute(
            text(_SELECT + """ where f.kind='recognition' and f.visibility='public'
                    order by f.created_at desc limit 50""")
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]

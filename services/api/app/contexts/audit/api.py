"""Audit trail read API (HR only). Append-only — no write/delete endpoints."""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import ROLE_HR_ADMIN, Principal, require_roles
from app.core.db import get_session

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEvent(BaseModel):
    id: str
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    summary: str | None = None
    changes: dict[str, Any]
    request_id: str | None = None
    created_at: datetime


@router.get("/events", response_model=list[AuditEvent])
async def list_events(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
    entity_type: str = "",
    entity_id: str = "",
    limit: int = Query(default=50, le=200),
) -> list[AuditEvent]:
    rows = (
        await session.execute(
            text("""select id::text, actor_email, action, entity_type, entity_id,
                       summary, changes, request_id, created_at
                    from ihrms.audit_event
                    where (:etype = '' or entity_type = :etype)
                      and (:eid = '' or entity_id = :eid)
                    order by created_at desc
                    limit :lim"""),
            {"etype": entity_type, "eid": entity_id, "lim": limit},
        )
    ).mappings().all()
    return [AuditEvent(**dict(r)) for r in rows]

"""Audit helper — one call records who did what to which entity.

Usage (inside the same transaction as the write, before commit):
    await record_audit(session, principal, "employee.update", "employee",
                       str(employee_id), summary="Updated job details",
                       changes=payload.model_dump(exclude_unset=True))

`changes` is stored as JSONB; redact secrets/full PII at the call site —
log that a field changed, not necessarily its value.
"""

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import Principal
from app.core.observability import request_id_ctx


async def record_audit(
    session: AsyncSession,
    principal: Principal,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    *,
    summary: str | None = None,
    changes: dict[str, Any] | None = None,
) -> None:
    await session.execute(
        text("""insert into ihrms.audit_event
                (actor_employee_id, actor_email, action, entity_type, entity_id,
                 summary, changes, request_id)
                values (:actor_id, :actor_email, :action, :etype, :eid,
                        :summary, cast(:changes as jsonb), :rid)"""),
        {
            "actor_id": principal.employee_id or None,
            "actor_email": principal.email,
            "action": action,
            "etype": entity_type,
            "eid": entity_id,
            "summary": summary,
            "changes": json.dumps(changes or {}, default=str),
            "rid": request_id_ctx.get(),
        },
    )

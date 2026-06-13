"""Policies API — publish, acknowledge, track compliance.

HR publishes versioned policy documents; every employee acknowledges them; HR
sees acknowledgement compliance vs active headcount. Tenant-scoped; audited.
"""

from datetime import datetime
from typing import Annotated, Any

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

router = APIRouter(prefix="/policies", tags=["policies"])
HR = require_roles(ROLE_HR_ADMIN)


class PolicyOut(BaseModel):
    id: str
    title: str
    category: str
    body: str
    version: int
    published_at: datetime
    acknowledged: bool = False


class PolicyIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str = Field(default="general", max_length=40)
    body: str = Field(min_length=1, max_length=20000)
    version: int = Field(default=1, ge=1)


def _out(r: dict[str, Any]) -> PolicyOut:
    return PolicyOut(
        id=r["id"], title=r["title"], category=r["category"], body=r["body"],
        version=r["version"], published_at=r["published_at"],
        acknowledged=bool(r.get("acknowledged")),
    )


@router.get("", response_model=list[PolicyOut])
async def list_policies(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[PolicyOut]:
    """Active policies, each flagged with whether the caller has acknowledged it."""
    rows = (
        await session.execute(
            text("""select p.id::text, p.title, p.category, p.body, p.version,
                       p.published_at,
                       (a.id is not null) as acknowledged
                    from ihrms.policy p
                    left join ihrms.policy_ack a
                      on a.policy_id = p.id and a.employee_id = :me
                    where p.is_active
                    order by p.published_at desc"""),
            {"me": principal.employee_id},
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


@router.post("", response_model=PolicyOut, status_code=201)
async def publish_policy(
    payload: PolicyIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> PolicyOut:
    row = (
        await session.execute(
            text("""insert into ihrms.policy (title, category, body, version, created_by)
                    values (:t, :c, :b, :v, :by)
                    returning id::text, title, category, body, version, published_at"""),
            {"t": payload.title, "c": payload.category, "b": payload.body,
             "v": payload.version, "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "policy.publish", "policy", row["id"],
        summary=f"Published policy: {payload.title} v{payload.version}",
    )
    out = _out(dict(row))
    await session.commit()
    return out


@router.post("/{policy_id}/ack", response_model=PolicyOut)
async def acknowledge_policy(
    policy_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> PolicyOut:
    pol = (
        await session.execute(
            text("""select id::text, title, category, body, version, published_at
                    from ihrms.policy where id=cast(:id as uuid) and is_active"""),
            {"id": policy_id},
        )
    ).mappings().first()
    if pol is None:
        raise HTTPException(404, "Policy not found")
    await session.execute(
        text("""insert into ihrms.policy_ack (policy_id, employee_id)
                values (cast(:p as uuid), :e)
                on conflict (policy_id, employee_id) do nothing"""),
        {"p": policy_id, "e": principal.employee_id},
    )
    await record_audit(
        session, principal, "policy.ack", "policy", policy_id,
        summary=f"Acknowledged policy {pol['title']}",
    )
    result = _out({**dict(pol), "acknowledged": True})
    await session.commit()
    return result


class PolicyCompliance(BaseModel):
    policy_id: str
    title: str
    acknowledged: int
    headcount: int
    pending: int


@router.get("/{policy_id}/compliance", response_model=PolicyCompliance)
async def compliance(
    policy_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> PolicyCompliance:
    pol = (
        await session.execute(
            text("select title from ihrms.policy where id=cast(:id as uuid)"),
            {"id": policy_id},
        )
    ).mappings().first()
    if pol is None:
        raise HTTPException(404, "Policy not found")
    headcount = int(
        (await session.execute(text("select count(*) from ihrms.v_employee where is_active")))
        .scalar_one()
    )
    acked = int(
        (
            await session.execute(
                text("""select count(*) from ihrms.policy_ack a
                        where a.policy_id = cast(:id as uuid) and exists (
                          select 1 from ihrms.v_employee e
                          where e.employee_id = a.employee_id and e.is_active)"""),
                {"id": policy_id},
            )
        ).scalar_one()
    )
    return PolicyCompliance(
        policy_id=policy_id, title=pol["title"], acknowledged=acked,
        headcount=headcount, pending=max(headcount - acked, 0),
    )

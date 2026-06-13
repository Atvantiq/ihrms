"""Consent API — view and grant/withdraw DPDP consents.

An employee manages their own consents (self-service); HR can view anyone's and
see an org-wide compliance overview. Every grant/withdraw is audited, giving the
DPDP-required consent trail. Tenant-scoped.
"""

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.consent.service import PURPOSE_KEYS, PURPOSES, purpose
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/consent", tags=["consent"])
HR = require_roles(ROLE_HR_ADMIN)


class ConsentLine(BaseModel):
    purpose: str
    label: str
    description: str
    required: bool
    version: int
    status: str  # granted | withdrawn | not_given
    decided_at: datetime | None = None


class ConsentDecision(BaseModel):
    purpose: str
    grant: bool


async def _lines(session: AsyncSession, employee_id: int) -> list[ConsentLine]:
    rows = {
        r["purpose"]: r
        for r in (
            await session.execute(
                text("""select purpose, status, decided_at
                        from ihrms.consent where employee_id = :e"""),
                {"e": employee_id},
            )
        ).mappings().all()
    }
    out: list[ConsentLine] = []
    for p in PURPOSES:
        rec = rows.get(p.key)
        out.append(
            ConsentLine(
                purpose=p.key, label=p.label, description=p.description,
                required=p.required, version=p.version,
                status=rec["status"] if rec else "not_given",
                decided_at=rec["decided_at"] if rec else None,
            )
        )
    return out


@router.get("", response_model=list[ConsentLine])
async def my_consent(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> list[ConsentLine]:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own consent")
    return await _lines(session, target)


@router.post("", response_model=list[ConsentLine])
async def decide_consent(
    payload: ConsentDecision,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> list[ConsentLine]:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only manage your own consent")
    if payload.purpose not in PURPOSE_KEYS:
        raise HTTPException(404, "Unknown consent purpose")
    p = purpose(payload.purpose)
    assert p is not None  # guarded above
    status = "granted" if payload.grant else "withdrawn"
    source = "self" if target == principal.employee_id else "hr"

    await session.execute(
        text("""insert into ihrms.consent
                (employee_id, purpose, status, version, source, decided_by)
                values (:e, :p, :st, :v, :src, :by)
                on conflict (tenant_id, employee_id, purpose) do update set
                  status = excluded.status, version = excluded.version,
                  source = excluded.source, decided_by = excluded.decided_by,
                  decided_at = now()"""),
        {"e": target, "p": payload.purpose, "st": status, "v": p.version,
         "src": source, "by": principal.employee_id},
    )
    await record_audit(
        session, principal, f"consent.{status}", "consent", f"{target}:{payload.purpose}",
        summary=f"{status.capitalize()} consent for '{p.label}'",
    )
    lines = await _lines(session, target)
    await session.commit()
    return lines


class ConsentOverview(BaseModel):
    purpose: str
    label: str
    required: bool
    granted: int
    withdrawn: int
    not_given: int


@router.get("/overview", response_model=list[ConsentOverview])
async def overview(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[ConsentOverview]:
    """Org-wide consent posture — active headcount vs grants per purpose."""
    headcount = int(
        (await session.execute(text("select count(*) from ihrms.v_employee where is_active")))
        .scalar_one()
    )
    counts: dict[str, dict[str, int]] = {}
    rows = (
        await session.execute(
            text("""select purpose, status, count(*) as n from ihrms.consent c
                    where exists (select 1 from ihrms.v_employee e
                                  where e.employee_id = c.employee_id and e.is_active)
                    group by purpose, status""")
        )
    ).mappings().all()
    for r in rows:
        counts.setdefault(r["purpose"], {})[r["status"]] = int(r["n"])

    out: list[ConsentOverview] = []
    for p in PURPOSES:
        c: dict[str, Any] = counts.get(p.key, {})
        granted = c.get("granted", 0)
        withdrawn = c.get("withdrawn", 0)
        out.append(
            ConsentOverview(
                purpose=p.key, label=p.label, required=p.required,
                granted=granted, withdrawn=withdrawn,
                not_given=max(headcount - granted - withdrawn, 0),
            )
        )
    return out

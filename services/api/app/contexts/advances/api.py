"""Advances & loans API — issue, list, cancel.

Recovery itself happens automatically (payroll EMI, or in full at F&F); this
surface is for issuing and tracking. HR manages; an employee can see their own
(feeds Employee 360 and the exit settlement). Writes audited; tenant-scoped.
"""

from datetime import date
from decimal import Decimal
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

router = APIRouter(prefix="/advances", tags=["advances"])
HR = require_roles(ROLE_HR_ADMIN)


class AdvanceOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    kind: str
    principal_amount: Decimal
    emi_amount: Decimal
    outstanding: Decimal
    recovered: Decimal
    reason: str | None = None
    status: str
    disbursed_on: date


class AdvanceIn(BaseModel):
    employee_id: int
    kind: Literal["advance", "loan"] = "advance"
    principal_amount: Decimal = Field(gt=0)
    emi_amount: Decimal = Field(gt=0)
    reason: str | None = None


_SELECT = """
    select a.id::text, a.employee_id, a.kind, a.principal_amount, a.emi_amount,
           a.outstanding, a.reason, a.status, a.disbursed_on,
           (a.principal_amount - a.outstanding) as recovered,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as employee_name
    from ihrms.advance a
    left join public.employees e on e.employee_id = a.employee_id
"""


def _out(r: dict[str, Any]) -> AdvanceOut:
    return AdvanceOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["employee_name"] or None,
        kind=r["kind"], principal_amount=r["principal_amount"], emi_amount=r["emi_amount"],
        outstanding=r["outstanding"], recovered=r["recovered"], reason=r["reason"],
        status=r["status"], disbursed_on=r["disbursed_on"],
    )


@router.get("", response_model=list[AdvanceOut])
async def list_advances(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[AdvanceOut]:
    rows = (
        await session.execute(
            text(_SELECT + " order by (a.status='active') desc, a.created_at desc")
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


@router.get("/employee/{employee_id}", response_model=list[AdvanceOut])
async def advances_of_employee(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[AdvanceOut]:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own advances")
    rows = (
        await session.execute(
            text(_SELECT + " where a.employee_id = :e order by a.created_at desc"),
            {"e": employee_id},
        )
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


@router.post("", response_model=AdvanceOut, status_code=201)
async def issue_advance(
    payload: AdvanceIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AdvanceOut:
    if payload.emi_amount > payload.principal_amount:
        raise HTTPException(422, "EMI cannot exceed the principal")
    emp = (
        await session.execute(
            text("select 1 from public.employees where employee_id = :e and is_active = 1"),
            {"e": payload.employee_id},
        )
    ).scalar()
    if emp is None:
        raise HTTPException(404, "Active employee not found")
    row = (
        await session.execute(
            text("""insert into ihrms.advance
                    (employee_id, kind, principal_amount, emi_amount, outstanding,
                     reason, created_by)
                    values (:e, :k, :p, :emi, :p, :reason, :by)
                    returning id::text"""),
            {"e": payload.employee_id, "k": payload.kind, "p": payload.principal_amount,
             "emi": payload.emi_amount, "reason": payload.reason, "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "advance.issue", "advance", row["id"],
        summary=f"{payload.kind.capitalize()} ₹{payload.principal_amount} "
        f"to employee {payload.employee_id}",
    )
    out = (await session.execute(text(_SELECT + " where a.id = :id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.post("/{advance_id}/cancel", response_model=AdvanceOut)
async def cancel_advance(
    advance_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AdvanceOut:
    row = (
        await session.execute(
            text("""update ihrms.advance set status='cancelled', updated_at=now()
                    where id=:id and status='active' returning id"""),
            {"id": advance_id},
        )
    ).scalar()
    if row is None:
        raise HTTPException(409, "Advance not found or not active")
    await record_audit(
        session, principal, "advance.cancel", "advance", advance_id,
        summary="Advance cancelled",
    )
    out = (await session.execute(text(_SELECT + " where a.id = :id"),
                                 {"id": advance_id})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result

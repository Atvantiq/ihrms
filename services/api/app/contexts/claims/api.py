"""Expense claims API — file, approve, reject. Paid in the next payroll run.

An employee files a claim (or HR on their behalf); a manager/HR approves;
approved claims are reimbursed in the next run and marked paid. Tenant-scoped.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import Principal, get_current_principal
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/claims", tags=["claims"])

CATEGORIES = ["travel", "food", "accommodation", "supplies", "communication", "other"]


class ClaimOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    category: str
    description: str
    claim_date: date
    amount: Decimal
    receipt_ref: str | None = None
    status: str
    decided_at: datetime | None = None


class ClaimIn(BaseModel):
    category: Literal["travel", "food", "accommodation", "supplies", "communication", "other"]
    description: str = Field(min_length=1, max_length=300)
    claim_date: date
    amount: Decimal = Field(gt=0)
    receipt_ref: str | None = None
    employee_id: int | None = None


_SELECT = """
    select c.id::text, c.employee_id, c.category, c.description, c.claim_date,
           c.amount, c.receipt_ref, c.status, c.decided_at,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
    from ihrms.expense_claim c
    left join public.employees e on e.employee_id = c.employee_id
"""


def _out(r: dict[str, Any]) -> ClaimOut:
    return ClaimOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
        category=r["category"], description=r["description"], claim_date=r["claim_date"],
        amount=r["amount"], receipt_ref=r["receipt_ref"], status=r["status"],
        decided_at=r["decided_at"],
    )


@router.get("/categories", response_model=list[str])
async def list_categories(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[str]:
    return CATEGORIES


@router.post("", response_model=ClaimOut, status_code=201)
async def file_claim(
    payload: ClaimIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ClaimOut:
    target = payload.employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only file your own claims")
    if payload.claim_date > date.today():
        raise HTTPException(409, "Cannot claim for a future date")
    row = (
        await session.execute(
            text("""insert into ihrms.expense_claim
                    (employee_id, category, description, claim_date, amount, receipt_ref)
                    values (:e, :c, :d, :dt, :a, :rr) returning id::text"""),
            {"e": target, "c": payload.category, "d": payload.description,
             "dt": payload.claim_date, "a": payload.amount, "rr": payload.receipt_ref},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "claim.file", "employee", str(target),
        summary=f"Filed {payload.category} claim of {payload.amount}",
    )
    out = (await session.execute(text(_SELECT + " where c.id=:id"),
                                 {"id": row["id"]})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.get("", response_model=list[ClaimOut])
async def list_claims(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "mine",  # mine | pending
) -> list[ClaimOut]:
    if scope == "mine":
        where, params = "where c.employee_id = :me", {"me": principal.employee_id}
    elif scope == "pending":
        if principal.is_hr:
            where, params = "where c.status = 'pending'", {}
        else:
            where = """where c.status='pending' and c.employee_id in (
                         select employee_id from public.job_details
                         where reporting_manager = :me and is_active = 1)"""
            params = {"me": principal.employee_id}
    else:
        raise HTTPException(422, "Invalid scope")
    rows = (
        await session.execute(text(_SELECT + " " + where + " order by c.claim_date desc"), params)
    ).mappings().all()
    return [_out(dict(r)) for r in rows]


async def _decide(
    session: AsyncSession, principal: Principal, claim_id: str, outcome: str
) -> ClaimOut:
    c = (
        await session.execute(
            text("select employee_id, status from ihrms.expense_claim where id=:id"),
            {"id": claim_id},
        )
    ).mappings().first()
    if c is None:
        raise HTTPException(404, "Claim not found")
    if c["status"] != "pending":
        raise HTTPException(409, "Claim is not pending")
    if not principal.is_hr:
        is_mgr = (
            await session.execute(
                text("""select 1 from public.job_details
                        where employee_id=:e and reporting_manager=:me and is_active=1"""),
                {"e": c["employee_id"], "me": principal.employee_id},
            )
        ).scalar()
        if not is_mgr or c["employee_id"] == principal.employee_id:
            raise HTTPException(403, "You cannot decide this claim")
    await session.execute(
        text("""update ihrms.expense_claim set status=:st, decided_by=:by, decided_at=now()
                where id=:id"""),
        {"st": outcome, "by": principal.employee_id, "id": claim_id},
    )
    await record_audit(
        session, principal, f"claim.{outcome[:6]}", "employee", str(c["employee_id"]),
        summary=f"{outcome.capitalize()} expense claim",
    )
    out = (await session.execute(text(_SELECT + " where c.id=:id"),
                                 {"id": claim_id})).mappings().one()
    result = _out(dict(out))
    await session.commit()
    return result


@router.post("/{claim_id}/approve", response_model=ClaimOut)
async def approve_claim(
    claim_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ClaimOut:
    return await _decide(session, principal, claim_id, "approved")


@router.post("/{claim_id}/reject", response_model=ClaimOut)
async def reject_claim(
    claim_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ClaimOut:
    return await _decide(session, principal, claim_id, "rejected")

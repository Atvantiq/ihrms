"""Tax declaration API — declare Chapter VI-A investments, submit, approve.

Employees fill and submit a declaration for a financial year; HR approves, which
pushes the capped eligible deduction (and chosen regime) onto the employee's
salary structure so the TDS engine uses it. Tenant-scoped; writes audited.
"""

from datetime import date, datetime
from decimal import Decimal
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
from app.contexts.tax.service import SECTION_KEYS, SECTIONS, eligible_deduction
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.money import D

router = APIRouter(prefix="/tax", tags=["tax"])
HR = require_roles(ROLE_HR_ADMIN)


def current_fy(today: date | None = None) -> str:
    """India financial year label, e.g. '2026-27' (Apr–Mar)."""
    d = today or date.today()
    start = d.year if d.month >= 4 else d.year - 1
    return f"{start}-{str(start + 1)[2:]}"


class SectionOut(BaseModel):
    key: str
    label: str
    cap: Decimal


class DeclItem(BaseModel):
    section: str
    amount: Decimal = Field(ge=0)


class DeclarationOut(BaseModel):
    id: str | None = None
    employee_id: int
    fy: str
    regime: str
    status: str
    items: list[DeclItem]
    declared_total: Decimal
    eligible_deduction: Decimal
    decided_at: datetime | None = None


class DeclarationIn(BaseModel):
    fy: str | None = None
    regime: Literal["old", "new"] = "old"
    items: list[DeclItem] = []


@router.get("/sections", response_model=list[SectionOut])
async def list_sections(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[SectionOut]:
    return [SectionOut(key=s.key, label=s.label, cap=s.cap) for s in SECTIONS]


async def _load(session: AsyncSession, employee_id: int, fy: str) -> DeclarationOut:
    hdr = (
        await session.execute(
            text("""select id::text, regime, status, decided_at
                    from ihrms.tax_declaration where employee_id=:e and fy=:fy"""),
            {"e": employee_id, "fy": fy},
        )
    ).mappings().first()
    items: list[DeclItem] = []
    if hdr:
        rows = (
            await session.execute(
                text("""select section, amount from ihrms.tax_declaration_item
                        where declaration_id = cast(:id as uuid)"""),
                {"id": hdr["id"]},
            )
        ).mappings().all()
        items = [DeclItem(section=r["section"], amount=r["amount"]) for r in rows]
    item_map = {i.section: i.amount for i in items}
    return DeclarationOut(
        id=hdr["id"] if hdr else None,
        employee_id=employee_id, fy=fy,
        regime=hdr["regime"] if hdr else "old",
        status=hdr["status"] if hdr else "draft",
        items=items,
        declared_total=sum(item_map.values(), D(0)),
        eligible_deduction=eligible_deduction(item_map),
        decided_at=hdr["decided_at"] if hdr else None,
    )


@router.get("/declaration", response_model=DeclarationOut)
async def get_declaration(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    fy: str | None = None,
    employee_id: int | None = None,
) -> DeclarationOut:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own declaration")
    return await _load(session, target, fy or current_fy())


@router.put("/declaration", response_model=DeclarationOut)
async def save_declaration(
    payload: DeclarationIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> DeclarationOut:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only edit your own declaration")
    bad = [i.section for i in payload.items if i.section not in SECTION_KEYS]
    if bad:
        raise HTTPException(404, f"Unknown section(s): {', '.join(bad)}")
    fy = payload.fy or current_fy()

    existing = (
        await session.execute(
            text("""select id::text, status from ihrms.tax_declaration
                    where employee_id=:e and fy=:fy"""),
            {"e": target, "fy": fy},
        )
    ).mappings().first()
    if existing and existing["status"] in ("submitted", "approved"):
        raise HTTPException(409, f"Declaration is {existing['status']}, cannot edit")

    if existing:
        decl_id = existing["id"]
        await session.execute(
            text("""update ihrms.tax_declaration set regime=:r, status='draft', updated_at=now()
                    where id=cast(:id as uuid)"""),
            {"r": payload.regime, "id": decl_id},
        )
    else:
        decl_id = (
            await session.execute(
                text("""insert into ihrms.tax_declaration (employee_id, fy, regime)
                        values (:e, :fy, :r) returning id::text"""),
                {"e": target, "fy": fy, "r": payload.regime},
            )
        ).scalar_one()
    await session.execute(
        text("delete from ihrms.tax_declaration_item where declaration_id=cast(:id as uuid)"),
        {"id": decl_id},
    )
    for item in payload.items:
        if item.amount > 0:
            await session.execute(
                text("""insert into ihrms.tax_declaration_item (declaration_id, section, amount)
                        values (cast(:id as uuid), :s, :a)"""),
                {"id": decl_id, "s": item.section, "a": item.amount},
            )
    result = await _load(session, target, fy)
    await session.commit()
    return result


@router.post("/declaration/submit", response_model=DeclarationOut)
async def submit_declaration(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    fy: str | None = None,
) -> DeclarationOut:
    fy = fy or current_fy()
    row = (
        await session.execute(
            text("""update ihrms.tax_declaration set status='submitted', updated_at=now()
                    where employee_id=:e and fy=:fy and status in ('draft','rejected')
                    returning id::text"""),
            {"e": principal.employee_id, "fy": fy},
        )
    ).scalar()
    if row is None:
        raise HTTPException(409, "No editable declaration to submit")
    await record_audit(
        session, principal, "tax.submit", "tax_declaration", row,
        summary=f"Submitted tax declaration for {fy}",
    )
    result = await _load(session, principal.employee_id, fy)
    await session.commit()
    return result


async def _decide(
    session: AsyncSession, principal: Principal, decl_id: str, outcome: str
) -> DeclarationOut:
    hdr = (
        await session.execute(
            text("""select employee_id, fy, regime, status
                    from ihrms.tax_declaration where id=cast(:id as uuid)"""),
            {"id": decl_id},
        )
    ).mappings().first()
    if hdr is None:
        raise HTTPException(404, "Declaration not found")
    if hdr["status"] != "submitted":
        raise HTTPException(409, "Only a submitted declaration can be decided")

    await session.execute(
        text("""update ihrms.tax_declaration set status=:st, decided_by=:by,
                decided_at=now(), updated_at=now() where id=cast(:id as uuid)"""),
        {"st": outcome, "by": principal.employee_id, "id": decl_id},
    )
    if outcome == "approved":
        decl = await _load(session, hdr["employee_id"], hdr["fy"])
        # push the chosen regime + capped deduction onto the active structure so
        # the TDS engine uses it (Chapter VI-A applies to the old regime only)
        ded = decl.eligible_deduction if hdr["regime"] == "old" else D(0)
        await session.execute(
            text("""update ihrms.salary_structure
                    set tax_regime=:r, chapter_via_deductions=:d, updated_at=now()
                    where employee_id=:e and is_active"""),
            {"r": hdr["regime"], "d": ded, "e": hdr["employee_id"]},
        )
    await record_audit(
        session, principal, f"tax.{outcome[:7]}", "tax_declaration", decl_id,
        summary=f"{outcome.capitalize()} tax declaration for employee {hdr['employee_id']}",
    )
    result = await _load(session, hdr["employee_id"], hdr["fy"])
    await session.commit()
    return result


@router.post("/declaration/{decl_id}/approve", response_model=DeclarationOut)
async def approve_declaration(
    decl_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> DeclarationOut:
    return await _decide(session, principal, decl_id, "approved")


@router.post("/declaration/{decl_id}/reject", response_model=DeclarationOut)
async def reject_declaration(
    decl_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> DeclarationOut:
    return await _decide(session, principal, decl_id, "rejected")


class PendingDecl(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    fy: str
    regime: str
    eligible_deduction: Decimal


@router.get("/declarations/pending", response_model=list[PendingDecl])
async def pending_declarations(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[PendingDecl]:
    rows = (
        await session.execute(
            text("""select d.id::text, d.employee_id, d.fy, d.regime,
                       coalesce(sum(i.amount), 0) as declared,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.tax_declaration d
                    left join ihrms.tax_declaration_item i on i.declaration_id = d.id
                    left join public.employees e on e.employee_id = d.employee_id
                    where d.status='submitted'
                    group by d.id, d.employee_id, d.fy, d.regime, nm
                    order by d.updated_at""")
        )
    ).mappings().all()
    out: list[PendingDecl] = []
    for r in rows:
        items = {
            it["section"]: it["amount"]
            for it in (
                await session.execute(
                    text("""select section, amount from ihrms.tax_declaration_item
                            where declaration_id=cast(:id as uuid)"""),
                    {"id": r["id"]},
                )
            ).mappings().all()
        }
        out.append(
            PendingDecl(
                id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
                fy=r["fy"], regime=r["regime"],
                eligible_deduction=eligible_deduction(items),
            )
        )
    return out

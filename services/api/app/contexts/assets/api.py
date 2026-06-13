"""Assets API — register, assign, return, retire.

HR manages the asset register and assignments; any authenticated user can see
the assets currently issued to a given employee (used by Employee 360 and the
exit/F&F clearance). Writes are audited; everything is tenant-scoped via RLS.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.assets.service import book_value, can_assign, can_return
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.money import D

router = APIRouter(prefix="/assets", tags=["assets"])
HR = require_roles(ROLE_HR_ADMIN)

Category = Literal["laptop", "desktop", "phone", "monitor", "peripheral", "furniture", "other"]


class AssetOut(BaseModel):
    id: str
    asset_tag: str
    category: str
    name: str
    serial_no: str | None = None
    purchase_date: date | None = None
    purchase_cost: Decimal | None = None
    status: str
    condition: str
    holder_id: int | None = None
    holder_name: str | None = None
    book_value: Decimal | None = None


class AssetIn(BaseModel):
    asset_tag: str = Field(min_length=1, max_length=40)
    category: Category = "laptop"
    name: str = Field(min_length=1, max_length=160)
    serial_no: str | None = None
    purchase_date: date | None = None
    purchase_cost: Decimal | None = Field(default=None, ge=0)
    condition: Literal["new", "good", "fair", "poor"] = "good"


_SELECT = """
    select a.id::text, a.asset_tag, a.category, a.name, a.serial_no,
           a.purchase_date, a.purchase_cost, a.status, a.condition,
           ag.employee_id as holder_id,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as holder_name
    from ihrms.asset a
    left join ihrms.asset_assignment ag
      on ag.asset_id = a.id and ag.status = 'assigned'
    left join public.employees e on e.employee_id = ag.employee_id
"""


def _to_out(r: dict[str, Any], today: date) -> AssetOut:
    return AssetOut(
        id=r["id"], asset_tag=r["asset_tag"], category=r["category"], name=r["name"],
        serial_no=r["serial_no"], purchase_date=r["purchase_date"],
        purchase_cost=r["purchase_cost"], status=r["status"], condition=r["condition"],
        holder_id=r["holder_id"], holder_name=r["holder_name"] or None,
        book_value=book_value(
            r["purchase_cost"], r["purchase_date"], today, category=r["category"]
        ),
    )


@router.get("", response_model=list[AssetOut])
async def list_assets(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[AssetOut]:
    rows = (
        await session.execute(text(_SELECT + " order by a.asset_tag"))
    ).mappings().all()
    today = date.today()
    return [_to_out(dict(r), today) for r in rows]


class DepreciationLine(BaseModel):
    id: str
    asset_tag: str
    name: str
    category: str
    purchase_cost: Decimal
    book_value: Decimal
    depreciated: Decimal


class DepreciationReport(BaseModel):
    lines: list[DepreciationLine]
    total_cost: Decimal
    total_book_value: Decimal
    total_depreciated: Decimal


@router.get("/depreciation", response_model=DepreciationReport)
async def depreciation_report(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> DepreciationReport:
    """Straight-line written-down value of every costed asset (the drawer's
    Finance & depreciation view, aggregated)."""
    rows = (
        await session.execute(
            text("""select a.id::text, a.asset_tag, a.name, a.category,
                       a.purchase_cost, a.purchase_date
                    from ihrms.asset a
                    where a.status <> 'retired' and a.purchase_cost is not null
                    order by a.purchase_cost desc""")
        )
    ).mappings().all()
    today = date.today()
    lines: list[DepreciationLine] = []
    total_cost = total_bv = D(0)
    for r in rows:
        cost = Decimal(str(r["purchase_cost"]))
        bv = book_value(cost, r["purchase_date"], today, category=r["category"])
        lines.append(
            DepreciationLine(
                id=r["id"], asset_tag=r["asset_tag"], name=r["name"], category=r["category"],
                purchase_cost=cost, book_value=bv, depreciated=cost - bv,
            )
        )
        total_cost += cost
        total_bv += bv
    return DepreciationReport(
        lines=lines, total_cost=total_cost, total_book_value=total_bv,
        total_depreciated=total_cost - total_bv,
    )


@router.get("/employee/{employee_id}", response_model=list[AssetOut])
async def assets_of_employee(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[AssetOut]:
    """Assets currently held by an employee — self or HR (feeds 360 + exit)."""
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own assets")
    rows = (
        await session.execute(
            text(_SELECT + " where ag.employee_id = :emp and a.status = 'assigned'"),
            {"emp": employee_id},
        )
    ).mappings().all()
    today = date.today()
    return [_to_out(dict(r), today) for r in rows]


@router.post("", response_model=AssetOut, status_code=201)
async def create_asset(
    payload: AssetIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AssetOut:
    dup = (
        await session.execute(
            text("select 1 from ihrms.asset where asset_tag = :t"), {"t": payload.asset_tag}
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Asset tag already exists")
    row = (
        await session.execute(
            text("""insert into ihrms.asset
                    (asset_tag, category, name, serial_no, purchase_date,
                     purchase_cost, condition)
                    values (:tag, :cat, :name, :sn, :pd, :pc, :cond)
                    returning id::text"""),
            {"tag": payload.asset_tag, "cat": payload.category, "name": payload.name,
             "sn": payload.serial_no, "pd": payload.purchase_date,
             "pc": payload.purchase_cost, "cond": payload.condition},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "asset.create", "asset", row["id"],
        summary=f"Registered asset {payload.asset_tag} ({payload.name})",
    )
    out = (await session.execute(text(_SELECT + " where a.id = :id"),
                                 {"id": row["id"]})).mappings().one()
    result = _to_out(dict(out), date.today())
    await session.commit()
    return result


class AssignIn(BaseModel):
    employee_id: int
    note: str | None = None


@router.post("/{asset_id}/assign", response_model=AssetOut)
async def assign_asset(
    asset_id: str,
    payload: AssignIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AssetOut:
    asset = (
        await session.execute(
            text("select status from ihrms.asset where id = :id"), {"id": asset_id}
        )
    ).mappings().first()
    if asset is None:
        raise HTTPException(404, "Asset not found")
    if not can_assign(asset["status"]):
        raise HTTPException(409, f"Asset is {asset['status']}, cannot assign")
    emp = (
        await session.execute(
            text("select 1 from public.employees where employee_id = :e"),
            {"e": payload.employee_id},
        )
    ).scalar()
    if emp is None:
        raise HTTPException(404, "Employee not found")

    await session.execute(
        text("""insert into ihrms.asset_assignment (asset_id, employee_id, note)
                values (:a, :e, :n)"""),
        {"a": asset_id, "e": payload.employee_id, "n": payload.note},
    )
    await session.execute(
        text("update ihrms.asset set status='assigned', updated_at=now() where id=:id"),
        {"id": asset_id},
    )
    await record_audit(
        session, principal, "asset.assign", "asset", asset_id,
        summary=f"Assigned to employee {payload.employee_id}",
    )
    out = (await session.execute(text(_SELECT + " where a.id = :id"),
                                 {"id": asset_id})).mappings().one()
    result = _to_out(dict(out), date.today())
    await session.commit()
    return result


class ReturnIn(BaseModel):
    note: str | None = None
    condition: Literal["new", "good", "fair", "poor"] | None = None


@router.post("/{asset_id}/return", response_model=AssetOut)
async def return_asset(
    asset_id: str,
    payload: ReturnIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AssetOut:
    asset = (
        await session.execute(
            text("select status from ihrms.asset where id = :id"), {"id": asset_id}
        )
    ).mappings().first()
    if asset is None:
        raise HTTPException(404, "Asset not found")
    if not can_return(asset["status"]):
        raise HTTPException(409, f"Asset is {asset['status']}, nothing to return")

    await session.execute(
        text("""update ihrms.asset_assignment
                set status='returned', returned_on=current_date,
                    note=coalesce(:n, note)
                where asset_id=:a and status='assigned'"""),
        {"a": asset_id, "n": payload.note},
    )
    await session.execute(
        text("""update ihrms.asset set status='in_stock',
                condition=coalesce(:cond, condition), updated_at=now()
                where id=:id"""),
        {"id": asset_id, "cond": payload.condition},
    )
    await record_audit(
        session, principal, "asset.return", "asset", asset_id,
        summary="Asset returned to stock",
    )
    out = (await session.execute(text(_SELECT + " where a.id = :id"),
                                 {"id": asset_id})).mappings().one()
    result = _to_out(dict(out), date.today())
    await session.commit()
    return result

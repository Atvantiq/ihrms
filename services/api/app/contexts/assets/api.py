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

from app.contexts.assets.service import (
    book_value,
    can_assign,
    can_return,
    license_renewal_status,
)
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


# ============================================================ asset requests

class AssetRequestOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    category: str
    justification: str
    status: str
    allocated_asset_id: str | None = None
    decision_note: str | None = None


class AssetRequestIn(BaseModel):
    category: Category
    justification: str = Field(min_length=1, max_length=500)


class ApproveRequestIn(BaseModel):
    asset_id: str | None = None  # optional: allocate this in-stock asset now
    note: str | None = None


_REQ_SELECT = """
    select r.id::text, r.employee_id, r.category, r.justification, r.status,
           r.allocated_asset_id::text as allocated_asset_id, r.decision_note,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as employee_name
    from ihrms.asset_request r
    left join public.employees e on e.employee_id = r.employee_id
"""


def _req_out(r: dict[str, Any]) -> AssetRequestOut:
    return AssetRequestOut(
        id=r["id"], employee_id=r["employee_id"], employee_name=r["employee_name"] or None,
        category=r["category"], justification=r["justification"], status=r["status"],
        allocated_asset_id=r["allocated_asset_id"], decision_note=r["decision_note"],
    )


@router.get("/requests", response_model=list[AssetRequestOut])
async def list_requests(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: Literal["mine", "pending", "all"] = "mine",
) -> list[AssetRequestOut]:
    if scope != "mine" and not principal.is_hr:
        raise HTTPException(403, "HR only")
    where, params = "", {}
    if scope == "mine":
        where, params = " where r.employee_id = :me", {"me": principal.employee_id}
    elif scope == "pending":
        where = " where r.status = 'pending'"
    rows = (
        await session.execute(
            text(_REQ_SELECT + where + " order by r.created_at desc"), params
        )
    ).mappings().all()
    return [_req_out(dict(r)) for r in rows]


@router.post("/requests", response_model=AssetRequestOut, status_code=201)
async def raise_request(
    payload: AssetRequestIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> AssetRequestOut:
    row = (
        await session.execute(
            text("""insert into ihrms.asset_request (employee_id, category, justification)
                    values (:e, :c, :j) returning id::text"""),
            {"e": principal.employee_id, "c": payload.category, "j": payload.justification},
        )
    ).scalar_one()
    out = _req_out(dict(
        (await session.execute(text(_REQ_SELECT + " where r.id = :id"),
                               {"id": row})).mappings().one()
    ))
    await session.commit()
    return out


@router.post("/requests/{request_id}/approve", response_model=AssetRequestOut)
async def approve_request(
    request_id: str,
    payload: ApproveRequestIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AssetRequestOut:
    req = (
        await session.execute(
            text("""select employee_id, status from ihrms.asset_request
                    where id = cast(:id as uuid)"""),
            {"id": request_id},
        )
    ).mappings().first()
    if req is None:
        raise HTTPException(404, "Request not found")
    if req["status"] != "pending":
        raise HTTPException(409, f"Request already {req['status']}")

    new_status = "approved"
    if payload.asset_id:
        asset = (
            await session.execute(
                text("select status from ihrms.asset where id = cast(:id as uuid)"),
                {"id": payload.asset_id},
            )
        ).mappings().first()
        if asset is None:
            raise HTTPException(404, "Asset to allocate not found")
        if not can_assign(asset["status"]):
            raise HTTPException(409, f"Asset is {asset['status']}, cannot allocate")
        await session.execute(
            text("""insert into ihrms.asset_assignment (asset_id, employee_id, note)
                    values (cast(:a as uuid), :e, 'Allocated via asset request')"""),
            {"a": payload.asset_id, "e": req["employee_id"]},
        )
        await session.execute(
            text("update ihrms.asset set status='assigned', updated_at=now() "
                 "where id=cast(:id as uuid)"),
            {"id": payload.asset_id},
        )
        new_status = "fulfilled"

    await session.execute(
        text("""update ihrms.asset_request
                set status=:s, allocated_asset_id=cast(:a as uuid), decision_note=:n,
                    decided_by=:by, updated_at=now()
                where id = cast(:id as uuid)"""),
        {"s": new_status, "a": payload.asset_id, "n": payload.note,
         "by": principal.employee_id, "id": request_id},
    )
    await record_audit(session, principal, "asset_request.approve", "asset_request",
                       request_id, summary=f"Request {new_status} for {req['employee_id']}")
    out = _req_out(dict(
        (await session.execute(text(_REQ_SELECT + " where r.id = cast(:id as uuid)"),
                               {"id": request_id})).mappings().one()
    ))
    await session.commit()
    return out


@router.post("/requests/{request_id}/reject", response_model=AssetRequestOut)
async def reject_request(
    request_id: str,
    payload: ReturnIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AssetRequestOut:
    res = await session.execute(
        text("""update ihrms.asset_request set status='rejected', decision_note=:n,
                decided_by=:by, updated_at=now()
                where id = cast(:id as uuid) and status='pending'
                returning id::text"""),
        {"n": payload.note, "by": principal.employee_id, "id": request_id},
    )
    if res.scalar() is None:
        raise HTTPException(409, "Request not found or not pending")
    out = _req_out(dict(
        (await session.execute(text(_REQ_SELECT + " where r.id = cast(:id as uuid)"),
                               {"id": request_id})).mappings().one()
    ))
    await session.commit()
    return out


# ========================================================== asset maintenance

class MaintenanceOut(BaseModel):
    id: str
    kind: str
    performed_on: date
    cost: Decimal
    vendor: str | None = None
    note: str | None = None


class MaintenanceIn(BaseModel):
    kind: Literal["service", "repair", "upgrade", "inspection"] = "service"
    performed_on: date
    cost: Decimal = Field(default=D(0), ge=0)
    vendor: str | None = None
    note: str | None = None


@router.get("/{asset_id}/maintenance", response_model=list[MaintenanceOut])
async def list_maintenance(
    asset_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[MaintenanceOut]:
    rows = (
        await session.execute(
            text("""select id::text, kind, performed_on, cost, vendor, note
                    from ihrms.asset_maintenance where asset_id = cast(:id as uuid)
                    order by performed_on desc"""),
            {"id": asset_id},
        )
    ).mappings().all()
    return [MaintenanceOut(**dict(r)) for r in rows]


@router.post("/{asset_id}/maintenance", response_model=MaintenanceOut, status_code=201)
async def add_maintenance(
    asset_id: str,
    payload: MaintenanceIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> MaintenanceOut:
    exists = (
        await session.execute(
            text("select 1 from ihrms.asset where id = cast(:id as uuid)"),
            {"id": asset_id},
        )
    ).scalar()
    if exists is None:
        raise HTTPException(404, "Asset not found")
    row = (
        await session.execute(
            text("""insert into ihrms.asset_maintenance
                    (asset_id, kind, performed_on, cost, vendor, note, created_by)
                    values (cast(:a as uuid), :k, :on, :cost, :v, :n, :by)
                    returning id::text, kind, performed_on, cost, vendor, note"""),
            {"a": asset_id, "k": payload.kind, "on": payload.performed_on,
             "cost": payload.cost, "v": payload.vendor, "n": payload.note,
             "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(session, principal, "asset_maintenance.add", "asset",
                       asset_id, summary=f"{payload.kind} logged (cost {payload.cost})")
    out = MaintenanceOut(**dict(row))
    await session.commit()
    return out


# ============================================================ software licenses

class LicenseOut(BaseModel):
    id: str
    name: str
    vendor: str | None = None
    seats_total: int
    seats_used: int
    seats_available: int
    renewal_date: date | None = None
    cost_annual: Decimal
    renewal_status: str
    notes: str | None = None


class LicenseIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    vendor: str | None = None
    seats_total: int = Field(default=1, ge=0, le=100000)
    renewal_date: date | None = None
    cost_annual: Decimal = Field(default=D(0), ge=0)
    notes: str | None = None


class SeatOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str | None = None
    assigned_on: date
    status: str


def _license_out(r: dict[str, Any], today: date) -> LicenseOut:
    used = int(r["seats_used"])
    total = int(r["seats_total"])
    return LicenseOut(
        id=r["id"], name=r["name"], vendor=r["vendor"], seats_total=total,
        seats_used=used, seats_available=max(0, total - used),
        renewal_date=r["renewal_date"], cost_annual=r["cost_annual"],
        renewal_status=license_renewal_status(r["renewal_date"], today),
        notes=r["notes"],
    )


_LICENSE_SELECT = """
    select l.id::text, l.name, l.vendor, l.seats_total, l.renewal_date,
           l.cost_annual, l.notes,
           (select count(*) from ihrms.license_seat s
            where s.license_id = l.id and s.status = 'active') as seats_used
    from ihrms.software_license l
"""


@router.get("/licenses", response_model=list[LicenseOut])
async def list_licenses(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[LicenseOut]:
    rows = (
        await session.execute(text(_LICENSE_SELECT + " order by l.name"))
    ).mappings().all()
    today = date.today()
    return [_license_out(dict(r), today) for r in rows]


@router.post("/licenses", response_model=LicenseOut, status_code=201)
async def create_license(
    payload: LicenseIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> LicenseOut:
    lid = (
        await session.execute(
            text("""insert into ihrms.software_license
                    (name, vendor, seats_total, renewal_date, cost_annual, notes)
                    values (:n, :v, :st, :rd, :c, :no) returning id::text"""),
            {"n": payload.name, "v": payload.vendor, "st": payload.seats_total,
             "rd": payload.renewal_date, "c": payload.cost_annual, "no": payload.notes},
        )
    ).scalar_one()
    row = (
        await session.execute(text(_LICENSE_SELECT + " where l.id = cast(:id as uuid)"),
                              {"id": lid})
    ).mappings().one()
    out = _license_out(dict(row), date.today())
    await session.commit()
    return out


@router.get("/licenses/{license_id}/seats", response_model=list[SeatOut])
async def list_seats(
    license_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[SeatOut]:
    rows = (
        await session.execute(
            text("""select s.id::text, s.employee_id, s.assigned_on, s.status,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.license_seat s
                    left join public.employees e on e.employee_id = s.employee_id
                    where s.license_id = cast(:l as uuid) order by s.assigned_on desc"""),
            {"l": license_id},
        )
    ).mappings().all()
    return [
        SeatOut(id=r["id"], employee_id=r["employee_id"], employee_name=r["nm"] or None,
                assigned_on=r["assigned_on"], status=r["status"])
        for r in rows
    ]


class SeatIn(BaseModel):
    employee_id: int


@router.post("/licenses/{license_id}/assign", response_model=LicenseOut, status_code=201)
async def assign_seat(
    license_id: str,
    payload: SeatIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> LicenseOut:
    lic = (
        await session.execute(text(_LICENSE_SELECT + " where l.id = cast(:id as uuid)"),
                              {"id": license_id})
    ).mappings().first()
    if lic is None:
        raise HTTPException(404, "License not found")
    if int(lic["seats_used"]) >= int(lic["seats_total"]):
        raise HTTPException(409, "No seats available")
    dup = (
        await session.execute(
            text("""select 1 from ihrms.license_seat
                    where license_id = cast(:l as uuid) and employee_id = :e
                      and status = 'active'"""),
            {"l": license_id, "e": payload.employee_id},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Employee already holds a seat")
    await session.execute(
        text("""insert into ihrms.license_seat (license_id, employee_id)
                values (cast(:l as uuid), :e)"""),
        {"l": license_id, "e": payload.employee_id},
    )
    row = (
        await session.execute(text(_LICENSE_SELECT + " where l.id = cast(:id as uuid)"),
                              {"id": license_id})
    ).mappings().one()
    out = _license_out(dict(row), date.today())
    await session.commit()
    return out


@router.post("/licenses/seats/{seat_id}/revoke", status_code=204)
async def revoke_seat(
    seat_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> None:
    await session.execute(
        text("update ihrms.license_seat set status='revoked' where id = cast(:id as uuid)"),
        {"id": seat_id},
    )
    await session.commit()


# ============================================================ lost register

class LostIn(BaseModel):
    circumstances: str = Field(min_length=1)
    police_report: bool = False


class LostOut(BaseModel):
    asset_id: str
    asset_tag: str
    name: str
    reported_on: date
    circumstances: str
    police_report: bool


@router.post("/{asset_id}/lost", response_model=AssetOut)
async def mark_lost(
    asset_id: str,
    payload: LostIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> AssetOut:
    asset = (
        await session.execute(
            text("select status from ihrms.asset where id = cast(:id as uuid)"),
            {"id": asset_id},
        )
    ).mappings().first()
    if asset is None:
        raise HTTPException(404, "Asset not found")
    if asset["status"] == "lost":
        raise HTTPException(409, "Asset already marked lost")
    # close any open assignment, then flag the asset and record the circumstances
    await session.execute(
        text("""update ihrms.asset_assignment set status='returned', returned_on=current_date
                where asset_id = cast(:id as uuid) and status='assigned'"""),
        {"id": asset_id},
    )
    await session.execute(
        text("update ihrms.asset set status='lost', updated_at=now() where id = cast(:id as uuid)"),
        {"id": asset_id},
    )
    await session.execute(
        text("""insert into ihrms.asset_lost (asset_id, circumstances, police_report, created_by)
                values (cast(:id as uuid), :c, :p, :by)"""),
        {"id": asset_id, "c": payload.circumstances, "p": payload.police_report,
         "by": principal.employee_id},
    )
    await record_audit(session, principal, "asset.lost", "asset", asset_id,
                       summary="Asset marked lost")
    out = (await session.execute(text(_SELECT + " where a.id = :id"),
                                 {"id": asset_id})).mappings().one()
    result = _to_out(dict(out), date.today())
    await session.commit()
    return result


@router.get("/lost", response_model=list[LostOut])
async def lost_register(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[LostOut]:
    rows = (
        await session.execute(
            text("""select a.id::text as asset_id, a.asset_tag, a.name,
                       l.reported_on, l.circumstances, l.police_report
                    from ihrms.asset_lost l
                    join ihrms.asset a on a.id = l.asset_id
                    order by l.reported_on desc""")
        )
    ).mappings().all()
    return [LostOut(**dict(r)) for r in rows]

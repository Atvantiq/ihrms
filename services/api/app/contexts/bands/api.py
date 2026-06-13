"""Bands & grades API — band master, employee assignment, fit check.

HR maintains the band catalogue and assigns each employee a band; the band-fit
flags whether their current CTC sits within range. Tenant-scoped; audited.
"""

from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.bands.service import band_fit
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.audit import record_audit
from app.core.db import get_session
from app.core.money import D

router = APIRouter(prefix="/bands", tags=["bands"])
HR = require_roles(ROLE_HR_ADMIN)


class BandOut(BaseModel):
    id: str
    code: str
    name: str
    level: int
    min_ctc: Decimal
    max_ctc: Decimal


class BandIn(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=80)
    level: int = Field(ge=1, le=20)
    min_ctc: Decimal = Field(gt=0)
    max_ctc: Decimal = Field(gt=0)


class EmployeeBandOut(BaseModel):
    employee_id: int
    band_id: str | None = None
    band_code: str | None = None
    band_name: str | None = None
    min_ctc: Decimal | None = None
    max_ctc: Decimal | None = None
    current_ctc: Decimal | None = None
    fit: str | None = None  # within | below | above


def _band_out(r: dict[str, Any]) -> BandOut:
    return BandOut(
        id=r["id"], code=r["code"], name=r["name"], level=r["level"],
        min_ctc=r["min_ctc"], max_ctc=r["max_ctc"],
    )


@router.get("", response_model=list[BandOut])
async def list_bands(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[BandOut]:
    rows = (
        await session.execute(
            text("""select id::text, code, name, level, min_ctc, max_ctc
                    from ihrms.salary_band where is_active order by level""")
        )
    ).mappings().all()
    return [_band_out(dict(r)) for r in rows]


@router.post("", response_model=BandOut, status_code=201)
async def create_band(
    payload: BandIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> BandOut:
    if payload.max_ctc < payload.min_ctc:
        raise HTTPException(422, "max_ctc must be >= min_ctc")
    dup = (
        await session.execute(
            text("select 1 from ihrms.salary_band where code=:c"), {"c": payload.code}
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "Band code already exists")
    row = (
        await session.execute(
            text("""insert into ihrms.salary_band (code, name, level, min_ctc, max_ctc)
                    values (:c, :n, :l, :mn, :mx)
                    returning id::text, code, name, level, min_ctc, max_ctc"""),
            {"c": payload.code, "n": payload.name, "l": payload.level,
             "mn": payload.min_ctc, "mx": payload.max_ctc},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "band.create", "salary_band", row["id"],
        summary=f"Created band {payload.code}",
    )
    out = _band_out(dict(row))
    await session.commit()
    return out


class AssignIn(BaseModel):
    employee_id: int
    band_id: str


@router.post("/assign", response_model=EmployeeBandOut)
async def assign_band(
    payload: AssignIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> EmployeeBandOut:
    band = (
        await session.execute(
            text("select 1 from ihrms.salary_band where id=cast(:b as uuid) and is_active"),
            {"b": payload.band_id},
        )
    ).scalar()
    if band is None:
        raise HTTPException(404, "Band not found")
    await session.execute(
        text("""insert into ihrms.employee_band (employee_id, band_id, assigned_by)
                values (:e, cast(:b as uuid), :by)
                on conflict (tenant_id, employee_id) do update set
                  band_id=cast(:b as uuid), assigned_on=current_date, assigned_by=:by"""),
        {"e": payload.employee_id, "b": payload.band_id, "by": principal.employee_id},
    )
    await record_audit(
        session, principal, "band.assign", "employee", str(payload.employee_id),
        summary="Assigned salary band",
    )
    result = await _employee_band(session, payload.employee_id)
    await session.commit()
    return result


async def _employee_band(session: AsyncSession, employee_id: int) -> EmployeeBandOut:
    row = (
        await session.execute(
            text("""select b.id::text as band_id, b.code, b.name, b.min_ctc, b.max_ctc
                    from ihrms.employee_band eb
                    join ihrms.salary_band b on b.id = eb.band_id
                    where eb.employee_id = :e"""),
            {"e": employee_id},
        )
    ).mappings().first()
    ctc = (
        await session.execute(
            text("""select ctc_annual from ihrms.salary_structure
                    where employee_id=:e and is_active"""),
            {"e": employee_id},
        )
    ).scalar()
    ctc_d = Decimal(str(ctc)) if ctc is not None else None
    if row is None:
        return EmployeeBandOut(employee_id=employee_id, current_ctc=ctc_d)
    fit = (
        band_fit(ctc_d, D(str(row["min_ctc"])), D(str(row["max_ctc"])))
        if ctc_d is not None else None
    )
    return EmployeeBandOut(
        employee_id=employee_id, band_id=row["band_id"], band_code=row["code"],
        band_name=row["name"], min_ctc=row["min_ctc"], max_ctc=row["max_ctc"],
        current_ctc=ctc_d, fit=fit,
    )


@router.get("/employee/{employee_id}", response_model=EmployeeBandOut)
async def employee_band(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> EmployeeBandOut:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own band")
    return await _employee_band(session, employee_id)

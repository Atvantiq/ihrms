"""Holiday calendar API. Read: any authenticated user. Write: HR only."""

from datetime import date
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
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/holidays", tags=["holidays"])

HolidayType = Literal["public", "optional", "restricted"]


class HolidayOut(BaseModel):
    id: str
    name: str
    holiday_date: date
    type: HolidayType


class HolidayCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    holiday_date: date
    type: HolidayType = "public"


@router.get("", response_model=list[HolidayOut])
async def list_holidays(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    year: int | None = None,
) -> list[HolidayOut]:
    rows = (
        await session.execute(
            text("""select id::text, name, holiday_date, type
                    from ihrms.holiday
                    where is_active
                      and (cast(:year as int) is null
                           or extract(year from holiday_date) = cast(:year as int))
                    order by holiday_date"""),
            {"year": year},
        )
    ).mappings().all()
    return [HolidayOut(**dict(r)) for r in rows]


@router.post("", response_model=HolidayOut, status_code=201)
async def add_holiday(
    payload: HolidayCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> HolidayOut:
    dup = (
        await session.execute(
            text("""select 1 from ihrms.holiday
                    where holiday_date = :d and lower(name) = lower(:n) and is_active"""),
            {"d": payload.holiday_date, "n": payload.name.strip()},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "That holiday already exists on that date")
    row = (
        await session.execute(
            text("""insert into ihrms.holiday (name, holiday_date, type)
                    values (:n, :d, :t) returning id::text, name, holiday_date, type"""),
            {"n": payload.name.strip(), "d": payload.holiday_date, "t": payload.type},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "holiday.create", "holiday", row["id"],
        summary=f"Added holiday '{payload.name.strip()}' on {payload.holiday_date}",
    )
    await session.commit()
    return HolidayOut(**dict(row))


@router.delete("/{holiday_id}", status_code=204)
async def remove_holiday(
    holiday_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> None:
    row = (
        await session.execute(
            text("""update ihrms.holiday set is_active = false, updated_at = now()
                    where id = :id and is_active returning name, holiday_date"""),
            {"id": holiday_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Holiday not found")
    await record_audit(
        session, principal, "holiday.delete", "holiday", holiday_id,
        summary=f"Removed holiday '{row['name']}' on {row['holiday_date']}",
    )
    await session.commit()

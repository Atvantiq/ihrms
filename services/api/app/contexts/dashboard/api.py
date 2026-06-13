"""Dashboard summary — read-only aggregation over existing data.

Reuses the directory status derivation and queries leave/holidays. Scoped
to the caller: an HR admin sees org-wide pending approvals, a manager sees
their reports' pending requests.
"""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.core_hr.service import derive_status, fetch_directory, full_name
from app.contexts.identity.principal import Principal, get_current_principal
from app.core.db import get_session

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

NEW_JOINER_WINDOW_DAYS = 30


class Headcount(BaseModel):
    total: int
    active: int
    probation: int
    joining: int
    notice: int
    inactive: int


class OnLeaveToday(BaseModel):
    employee_name: str
    leave_code: str
    end_date: date


class NewJoiner(BaseModel):
    full_name: str
    designation: str | None = None
    date_of_joining: date


class UpcomingHoliday(BaseModel):
    name: str
    holiday_date: date


class DashboardSummary(BaseModel):
    headcount: Headcount
    on_leave_today: list[OnLeaveToday]
    my_pending_approvals: int
    new_joiners: list[NewJoiner]
    upcoming_holidays: list[UpcomingHoliday]


@router.get("", response_model=DashboardSummary)
async def summary(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> DashboardSummary:
    today = date.today()
    rows = await fetch_directory(session)

    statuses = [derive_status(r, today) for r in rows]
    headcount = Headcount(
        total=len(rows),
        active=statuses.count("Active"),
        probation=statuses.count("Probation"),
        joining=statuses.count("Joining"),
        notice=statuses.count("Notice"),
        inactive=statuses.count("Inactive"),
    )

    cutoff = today - timedelta(days=NEW_JOINER_WINDOW_DAYS)
    new_joiners = sorted(
        (
            NewJoiner(
                full_name=full_name(r),
                designation=r["designation"],
                date_of_joining=r["date_of_joining"],
            )
            for r in rows
            if r["date_of_joining"] is not None and r["date_of_joining"] >= cutoff
        ),
        key=lambda j: j.date_of_joining,
        reverse=True,
    )[:8]

    leave_rows = (
        await session.execute(
            text("""select trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm,
                       lt.code, r.end_date
                    from ihrms.leave_request r
                    join ihrms.leave_type lt on lt.id = r.leave_type_id
                    left join public.employees e on e.employee_id = r.employee_id
                    where r.status = 'approved'
                      and r.start_date <= :today and r.end_date >= :today
                    order by nm"""),
            {"today": today},
        )
    ).mappings().all()
    on_leave = [
        OnLeaveToday(employee_name=r["nm"] or "—", leave_code=r["code"], end_date=r["end_date"])
        for r in leave_rows
    ]

    if principal.is_hr:
        pending = (
            await session.execute(
                text("select count(*) from ihrms.leave_request where status='pending'")
            )
        ).scalar_one()
    else:
        pending = (
            await session.execute(
                text("""select count(*) from ihrms.leave_request
                        where status='pending' and employee_id in (
                          select employee_id from public.job_details
                          where reporting_manager = :me and is_active = 1)"""),
                {"me": principal.employee_id},
            )
        ).scalar_one()

    holidays = (
        await session.execute(
            text("""select name, holiday_date from ihrms.holiday
                    where is_active and holiday_date >= :today
                    order by holiday_date limit 4"""),
            {"today": today},
        )
    ).mappings().all()

    return DashboardSummary(
        headcount=headcount,
        on_leave_today=on_leave,
        my_pending_approvals=int(pending),
        new_joiners=new_joiners,
        upcoming_holidays=[UpcomingHoliday(**dict(h)) for h in holidays],
    )

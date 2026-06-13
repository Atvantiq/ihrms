"""Attendance data access — fetch a month's inputs and derive the summary.

Shared by the attendance API and the payroll run (which needs the LOP count).
Keeps the SQL in one place; the derivation itself stays pure in service.py.
"""

import calendar
from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.attendance.service import MonthSummary, derive_month


async def month_summary(
    session: AsyncSession, employee_id: int, year: int, month: int, today: date
) -> MonthSummary:
    start = date(year, month, 1)
    end = date(year, month, calendar.monthrange(year, month)[1])

    marks = {
        r["work_date"]: r["status"]
        for r in (
            await session.execute(
                text("""select work_date, status from ihrms.attendance_record
                        where employee_id = :emp and work_date between :s and :e"""),
                {"emp": employee_id, "s": start, "e": end},
            )
        ).mappings().all()
    }

    leave_dates: set[date] = set()
    for r in (
        await session.execute(
            text("""select start_date, end_date from ihrms.leave_request
                    where employee_id = :emp and status = 'approved'
                      and start_date <= :e and end_date >= :s"""),
            {"emp": employee_id, "s": start, "e": end},
        )
    ).mappings().all():
        d = max(r["start_date"], start)
        while d <= min(r["end_date"], end):
            leave_dates.add(d)
            d = date.fromordinal(d.toordinal() + 1)

    holiday_dates = {
        r["holiday_date"]
        for r in (
            await session.execute(
                text("""select holiday_date from ihrms.holiday
                        where is_active and holiday_date between :s and :e"""),
                {"s": start, "e": end},
            )
        ).mappings().all()
    }

    return derive_month(year, month, today, marks, leave_dates, holiday_dates)

"""Unified task inbox — GET /tasks.

Where Pulse summarises ("4 leave requests pending"), Tasks itemises: every
individual approval waiting on the caller, normalised across modules so one
page can act on all of them. Read-only here; the act of approving/rejecting
goes through each module's existing decision endpoint.

Scope mirrors the rest of the app: HR admins see the whole org; managers see
only their direct reports; plain employees have nothing to approve.
"""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import Principal, get_current_principal
from app.core.db import get_session

router = APIRouter(prefix="/tasks", tags=["tasks"])


class Task(BaseModel):
    """One actionable approval, normalised across modules."""

    task_type: Literal["leave", "timesheet", "increment"]
    ref_id: str
    employee_id: int
    employee_name: str
    title: str
    subtitle: str
    badge: str
    can_reject: bool = True
    week_of: date | None = None  # timesheet decisions key on the week, not an id


@router.get("", response_model=list[Task])
async def list_tasks(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[Task]:
    me = principal.employee_id
    is_hr = principal.is_hr
    tasks: list[Task] = []

    # --- pending leave -----------------------------------------------------
    leave_where = "r.status = 'pending'"
    params: dict[str, object] = {}
    if not is_hr:
        leave_where += (
            " and r.employee_id in (select employee_id from public.job_details"
            " where reporting_manager = :me and is_active = 1)"
        )
        params["me"] = me
    leave_rows = (
        await session.execute(
            text(f"""select r.id::text as id, r.employee_id,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm,
                       lt.code, lt.label as type_name, r.start_date, r.end_date, r.days
                    from ihrms.leave_request r
                    join ihrms.leave_type lt on lt.id = r.leave_type_id
                    left join public.employees e on e.employee_id = r.employee_id
                    where {leave_where}
                    order by r.created_at"""),
            params,
        )
    ).mappings().all()
    for r in leave_rows:
        days = float(r["days"])
        days_txt = f"{days:g} day{'s' if days != 1 else ''}"
        tasks.append(
            Task(
                task_type="leave",
                ref_id=r["id"],
                employee_id=r["employee_id"],
                employee_name=r["nm"] or "—",
                title=f"{r['type_name']} · {days_txt}",
                subtitle=f"{r['start_date']} → {r['end_date']}",
                badge=r["code"],
            )
        )

    # --- submitted timesheets ---------------------------------------------
    ts_where = "w.status = 'submitted' and w.employee_id != :me"
    if not is_hr:
        ts_where += (
            " and w.employee_id in (select employee_id from public.job_details"
            " where reporting_manager = :me and is_active = 1)"
        )
    ts_rows = (
        await session.execute(
            text(f"""select w.employee_id, w.week_start, w.total_hours,
                       trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                    from ihrms.timesheet_week w
                    left join public.employees e on e.employee_id = w.employee_id
                    where {ts_where}
                    order by w.week_start"""),
            {"me": me},
        )
    ).mappings().all()
    for r in ts_rows:
        tasks.append(
            Task(
                task_type="timesheet",
                ref_id=f"{r['employee_id']}:{r['week_start']}",
                employee_id=r["employee_id"],
                employee_name=r["nm"] or "—",
                title=f"Timesheet · {float(r['total_hours']):g} h",
                subtitle=f"Week of {r['week_start']}",
                badge="hrs",
                week_of=r["week_start"],
            )
        )

    # --- proposed increments (HR only) ------------------------------------
    if is_hr:
        inc_rows = (
            await session.execute(
                text("""select i.id::text as id, i.employee_id, i.current_ctc,
                           i.proposed_ctc, i.pct, i.effective_date,
                           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as nm
                        from ihrms.increment i
                        left join public.employees e on e.employee_id = i.employee_id
                        where i.status = 'proposed'
                        order by i.created_at""")
            )
        ).mappings().all()
        for r in inc_rows:
            tasks.append(
                Task(
                    task_type="increment",
                    ref_id=r["id"],
                    employee_id=r["employee_id"],
                    employee_name=r["nm"] or "—",
                    title=f"Increment · +{float(r['pct']):g}%",
                    subtitle=f"₹{int(r['current_ctc']):,} → ₹{int(r['proposed_ctc']):,}"
                    f" · from {r['effective_date']}",
                    badge="raise",
                    can_reject=False,  # increments are approve-or-leave; no reject flow
                )
            )

    return tasks

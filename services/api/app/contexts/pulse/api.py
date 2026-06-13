"""Pulse inbox API — GET /pulse/inbox.

Gathers the live signals (approvals, probation, exits, payroll readiness),
scopes them to the caller, and returns them ranked. HR admins see the whole
org; managers see their own reports' approvals; everyone else gets a quiet
inbox. Read-only — Pulse never mutates, it only points you at the decision.
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import Principal, get_current_principal
from app.contexts.pulse.service import Decision, rank_decisions, severity_for_count
from app.core.db import get_session

router = APIRouter(prefix="/pulse", tags=["pulse"])

# A probation period completes 90 days after joining; flag the last week of it.
PROBATION_DAYS = 90
PROBATION_WARN_DAYS = 7


async def _scalar(session: AsyncSession, sql: str, **params: object) -> int:
    return int((await session.execute(text(sql), params)).scalar_one())


@router.get("/inbox", response_model=list[Decision])
async def inbox(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[Decision]:
    me = principal.employee_id
    is_hr = principal.is_hr
    decisions: list[Decision] = []

    # 1) Leave approvals waiting on me (HR: org-wide; manager: my reports).
    if is_hr:
        leave_pending = await _scalar(
            session, "select count(*) from ihrms.leave_request where status='pending'"
        )
    else:
        leave_pending = await _scalar(
            session,
            """select count(*) from ihrms.leave_request
               where status='pending' and employee_id in (
                 select employee_id from public.job_details
                 where reporting_manager = :me and is_active = 1)""",
            me=me,
        )
    if leave_pending:
        decisions.append(
            Decision(
                kind="leave_approvals",
                severity=severity_for_count(leave_pending, high_at=5),
                icon="◰",
                title=f"{leave_pending} leave request{'s' if leave_pending != 1 else ''} pending",
                detail="Awaiting your approval decision.",
                action_label="Review",
                action_href="/tasks",
                count=leave_pending,
            )
        )

    # 2) Timesheet approvals waiting on me.
    if is_hr:
        ts_pending = await _scalar(
            session,
            """select count(*) from ihrms.timesheet_week
               where status='submitted' and employee_id != :me""",
            me=me,
        )
    else:
        ts_pending = await _scalar(
            session,
            """select count(*) from ihrms.timesheet_week w
               where w.status='submitted' and w.employee_id != :me
                 and w.employee_id in (
                   select employee_id from public.job_details
                   where reporting_manager = :me and is_active = 1)""",
            me=me,
        )
    if ts_pending:
        decisions.append(
            Decision(
                kind="timesheet_approvals",
                severity=severity_for_count(ts_pending, high_at=8),
                icon="⊞",
                title=f"{ts_pending} timesheet{'s' if ts_pending != 1 else ''} to approve",
                detail="Submitted weeks awaiting your sign-off.",
                action_label="Review",
                action_href="/tasks",
                count=ts_pending,
            )
        )

    # 2b) Attendance regularizations waiting on me.
    if is_hr:
        reg_pending = await _scalar(
            session,
            """select count(*) from ihrms.attendance_regularization
               where status='pending' and employee_id != :me""",
            me=me,
        )
    else:
        reg_pending = await _scalar(
            session,
            """select count(*) from ihrms.attendance_regularization r
               where r.status='pending' and r.employee_id != :me
                 and r.employee_id in (
                   select employee_id from public.job_details
                   where reporting_manager = :me and is_active = 1)""",
            me=me,
        )
    if reg_pending:
        decisions.append(
            Decision(
                kind="regularization_approvals",
                severity=severity_for_count(reg_pending, high_at=8),
                icon="⏱",
                title=f"{reg_pending} attendance fix"
                f"{'es' if reg_pending != 1 else ''} to review",
                detail="Regularization requests awaiting your decision.",
                action_label="Review",
                action_href="/tasks",
                count=reg_pending,
            )
        )

    # 2c) Overtime approvals waiting on me.
    if is_hr:
        ot_pending = await _scalar(
            session,
            "select count(*) from ihrms.overtime where status='pending' and employee_id != :me",
            me=me,
        )
    else:
        ot_pending = await _scalar(
            session,
            """select count(*) from ihrms.overtime o
               where o.status='pending' and o.employee_id != :me
                 and o.employee_id in (
                   select employee_id from public.job_details
                   where reporting_manager = :me and is_active = 1)""",
            me=me,
        )
    if ot_pending:
        decisions.append(
            Decision(
                kind="overtime_approvals",
                severity=severity_for_count(ot_pending, high_at=8),
                icon="⏱",
                title=f"{ot_pending} overtime claim{'s' if ot_pending != 1 else ''} to review",
                detail="Overtime awaiting your approval.",
                action_label="Review",
                action_href="/tasks",
                count=ot_pending,
            )
        )

    # 2d) Comp-off approvals waiting on me.
    if is_hr:
        co_pending = await _scalar(
            session,
            "select count(*) from ihrms.comp_off where status='pending' and employee_id != :me",
            me=me,
        )
    else:
        co_pending = await _scalar(
            session,
            """select count(*) from ihrms.comp_off c
               where c.status='pending' and c.employee_id != :me
                 and c.employee_id in (
                   select employee_id from public.job_details
                   where reporting_manager = :me and is_active = 1)""",
            me=me,
        )
    if co_pending:
        decisions.append(
            Decision(
                kind="comp_off_approvals",
                severity=severity_for_count(co_pending, high_at=8),
                icon="◰",
                title=f"{co_pending} comp-off request{'s' if co_pending != 1 else ''} to review",
                detail="Compensatory-off credits awaiting your approval.",
                action_label="Review",
                action_href="/tasks",
                count=co_pending,
            )
        )

    # The remaining signals are HR/platform decisions.
    if is_hr:
        # 3) Increment proposals awaiting approval.
        incr = await _scalar(
            session, "select count(*) from ihrms.increment where status='proposed'"
        )
        if incr:
            decisions.append(
                Decision(
                    kind="increment_approvals",
                    severity=severity_for_count(incr, high_at=5),
                    icon="★",
                    title=f"{incr} salary increment{'s' if incr != 1 else ''} proposed",
                    detail="Review and approve to push into payroll.",
                    action_label="Open",
                    action_href="/tasks",
                    count=incr,
                )
            )

        # 3b) Open helpdesk tickets.
        open_tickets = await _scalar(
            session,
            "select count(*) from ihrms.ticket where status in ('open','in_progress')",
        )
        if open_tickets:
            decisions.append(
                Decision(
                    kind="open_tickets",
                    severity=severity_for_count(open_tickets, high_at=10),
                    icon="✉",
                    title=f"{open_tickets} open helpdesk ticket{'s' if open_tickets != 1 else ''}",
                    detail="Employee requests awaiting resolution.",
                    action_label="Open",
                    action_href="/helpdesk",
                    count=open_tickets,
                )
            )

        # 4) Exit / F&F settlements mid-flight.
        exits = await _scalar(
            session,
            "select count(*) from ihrms.exit_case where status in ('clearance','fnf_computed')",
        )
        if exits:
            decisions.append(
                Decision(
                    kind="exit_settlements",
                    severity="high",
                    icon="↗",
                    title=f"{exits} exit{'s' if exits != 1 else ''} awaiting settlement",
                    detail="Clearance or full-and-final needs your action.",
                    action_label="Open",
                    action_href="/exit",
                    count=exits,
                )
            )

        # 5) Probation confirmations due within a week.
        prob = await _scalar(
            session,
            """select count(*) from ihrms.v_employee
               where is_active and date_of_joining is not null
                 and date_of_joining between
                     (current_date - cast(:full as int)) and
                     (current_date - cast(:warn as int))""",
            full=PROBATION_DAYS,
            warn=PROBATION_DAYS - PROBATION_WARN_DAYS,
        )
        if prob:
            decisions.append(
                Decision(
                    kind="probation_due",
                    severity="medium",
                    icon="◷",
                    title=f"{prob} probation{'s' if prob != 1 else ''} ending this week",
                    detail="Confirm or extend before the 90-day mark.",
                    action_label="View",
                    action_href="/directory",
                    count=prob,
                )
            )

        # 6) Candidates sitting at the offer stage.
        offers = await _scalar(
            session, "select count(*) from ihrms.candidate where stage='offer'"
        )
        if offers:
            decisions.append(
                Decision(
                    kind="offers_pending",
                    severity=severity_for_count(offers, high_at=4),
                    icon="◎",
                    title=f"{offers} candidate{'s' if offers != 1 else ''} at offer stage",
                    detail="Awaiting offer release or acceptance.",
                    action_label="Open",
                    action_href="/recruitment",
                    count=offers,
                )
            )

        # 7) Payroll readiness — active employees with no bank details on file.
        no_bank = await _scalar(
            session,
            """select count(*) from ihrms.v_employee e
               where e.is_active and not exists (
                 select 1 from ihrms.employee_bank b
                 where b.employee_id = e.employee_id and b.is_active)""",
        )
        if no_bank:
            decisions.append(
                Decision(
                    kind="payroll_bank_missing",
                    severity="high",
                    icon="₹",
                    title=f"{no_bank} employee{'s' if no_bank != 1 else ''} missing bank details",
                    detail="Bank account needed before the next payroll run.",
                    action_label="Fix",
                    action_href="/payroll",
                    count=no_bank,
                )
            )

        # 8) A payroll run left in draft.
        draft_runs = await _scalar(
            session, "select count(*) from ihrms.payroll_run where status='draft'"
        )
        if draft_runs:
            decisions.append(
                Decision(
                    kind="payroll_draft",
                    severity="medium",
                    icon="₹",
                    title=f"{draft_runs} payroll run{'s' if draft_runs != 1 else ''} in draft",
                    detail="Finalise to lock payslips and generate the bank file.",
                    action_label="Open",
                    action_href="/payroll",
                    count=draft_runs,
                )
            )

    return rank_decisions(decisions)

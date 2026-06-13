"""Leave API — ESS apply + manager/HR approval.

Approval authority: a request may be decided by the employee's reporting
manager (from public.job_details) or any hr_admin. Self-approval is blocked.
Balance bookkeeping: apply -> pending +days; approve -> pending −days,
used +days; reject/cancel -> pending −days.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.identity.principal import Principal, get_current_principal
from app.contexts.leave.schemas import (
    BalanceOut,
    Decision,
    LeaveApply,
    LeaveRequestOut,
    LeaveTypeOut,
)
from app.contexts.leave.service import (
    available,
    ensure_balance,
    holidays_in_range,
    working_days,
)
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/leave", tags=["leave"])


async def _manager_of(session: AsyncSession, employee_id: int) -> int | None:
    return (
        await session.execute(
            text("""select reporting_manager from public.job_details
                    where employee_id = :id and is_active = 1
                    order by date_of_joining desc limit 1"""),
            {"id": employee_id},
        )
    ).scalar()


async def _name_of(session: AsyncSession, employee_id: int | None) -> str | None:
    if employee_id is None:
        return None
    row = (
        await session.execute(
            text("""select trim(concat(first_name, ' ', coalesce(last_name, '')))
                    from public.employees where employee_id = :id"""),
            {"id": employee_id},
        )
    ).scalar()
    return row


# ---------------------------------------------------------------- types

@router.get("/types", response_model=list[LeaveTypeOut])
async def list_types(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[LeaveTypeOut]:
    rows = (
        await session.execute(
            text("""select id::text, key, code, label, color, description, is_paid,
                       accrual_method, annual_entitlement, min_advance_notice_days,
                       max_consecutive_days, half_day_allowed, requires_doc, show_in_ess
                    from ihrms.leave_type
                    where is_active and show_in_ess order by sort_order""")
        )
    ).mappings().all()
    return [LeaveTypeOut(**dict(r)) for r in rows]


# ---------------------------------------------------------------- balances

@router.get("/balances", response_model=list[BalanceOut])
async def my_balances(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> list[BalanceOut]:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own balances")

    today = date.today()
    year = today.year
    types = (
        await session.execute(
            text("""select id::text, code, label, color from ihrms.leave_type
                    where is_active and consumes_balance order by sort_order""")
        )
    ).mappings().all()

    out: list[BalanceOut] = []
    for t in types:
        bal = await ensure_balance(session, target, t["id"], year, today)
        out.append(
            BalanceOut(
                leave_type_id=t["id"], code=t["code"], label=t["label"], color=t["color"],
                entitled=Decimal(bal["entitled"]), accrued=Decimal(bal["accrued"]),
                carried_forward=Decimal(bal["carried_forward"]), used=Decimal(bal["used"]),
                pending=Decimal(bal["pending"]), available=available(bal),
            )
        )
    await session.commit()
    return out


# ---------------------------------------------------------------- apply

@router.post("/requests", response_model=LeaveRequestOut, status_code=201)
async def apply_leave(
    payload: LeaveApply,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> LeaveRequestOut:
    # whose leave — self, or HR applying on behalf
    target = payload.employee_id or principal.employee_id
    if payload.employee_id and payload.employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "Only HR can apply on behalf of others")

    lt = (
        await session.execute(
            text("""select id::text, label, gender_eligibility, allow_probationers,
                       min_advance_notice_days, max_consecutive_days, half_day_allowed,
                       consumes_balance
                    from ihrms.leave_type where id = :id and is_active"""),
            {"id": payload.leave_type_id},
        )
    ).mappings().first()
    if lt is None:
        raise HTTPException(404, "Leave type not found")

    holidays = await holidays_in_range(session, payload.start_date, payload.end_date)
    try:
        days = working_days(
            payload.start_date, payload.end_date, payload.half_day, holidays
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    if days == 0:
        raise HTTPException(409, "Selected range has no working days")
    if payload.half_day and not lt["half_day_allowed"]:
        raise HTTPException(409, "Half-day is not allowed for this leave type")
    if lt["max_consecutive_days"] is not None and days > lt["max_consecutive_days"]:
        raise HTTPException(
            409, f"Exceeds the maximum of {lt['max_consecutive_days']} consecutive days"
        )

    today = date.today()
    notice = (payload.start_date - today).days
    if notice < lt["min_advance_notice_days"]:
        raise HTTPException(
            409,
            f"Requires {lt['min_advance_notice_days']} days advance notice "
            f"(this request gives {notice})",
        )

    # overlap check against live requests
    overlap = (
        await session.execute(
            text("""select 1 from ihrms.leave_request
                    where employee_id = :emp and status in ('pending','approved')
                      and start_date <= :end and end_date >= :start limit 1"""),
            {"emp": target, "start": payload.start_date, "end": payload.end_date},
        )
    ).scalar()
    if overlap:
        raise HTTPException(409, "Overlaps an existing leave request")

    # balance check + reserve as pending
    if lt["consumes_balance"]:
        bal = await ensure_balance(session, target, lt["id"], today.year, today)
        if available(bal) < days:
            raise HTTPException(
                409, f"Insufficient balance — {available(bal)} day(s) available, {days} requested"
            )
        await session.execute(
            text("""update ihrms.leave_balance set pending = pending + :d, updated_at = now()
                    where employee_id = :emp and leave_type_id = :lt and period_year = :yr"""),
            {"d": days, "emp": target, "lt": lt["id"], "yr": today.year},
        )

    req_id = (
        await session.execute(
            text("""insert into ihrms.leave_request
                    (employee_id, leave_type_id, start_date, end_date, half_day, days,
                     reason, applied_by)
                    values (:emp, :lt, :start, :end, :half, :days, :reason, :by)
                    returning id::text"""),
            {"emp": target, "lt": lt["id"], "start": payload.start_date,
             "end": payload.end_date, "half": payload.half_day, "days": days,
             "reason": payload.reason, "by": principal.employee_id},
        )
    ).scalar_one()
    await session.commit()
    return await _get_request(session, req_id, principal)


# ---------------------------------------------------------------- list

_REQ_SELECT = """
    select r.id::text, r.employee_id, r.leave_type_id::text, r.start_date, r.end_date,
           r.half_day, r.days, r.reason, r.status, r.approver_id, r.decision_note,
           r.decided_at::text,
           lt.code as leave_code, lt.label as leave_label, lt.color,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as employee_name
    from ihrms.leave_request r
    join ihrms.leave_type lt on lt.id = r.leave_type_id
    left join public.employees e on e.employee_id = r.employee_id
"""


async def _decorate(
    session: AsyncSession, row: dict[str, Any], principal: Principal
) -> LeaveRequestOut:
    mgr = await _manager_of(session, row["employee_id"])
    can_decide = (
        row["status"] == "pending"
        and row["employee_id"] != principal.employee_id
        and (principal.is_hr or mgr == principal.employee_id)
    )
    can_cancel = row["status"] == "pending" and (
        row["employee_id"] == principal.employee_id or principal.is_hr
    )
    return LeaveRequestOut(
        id=row["id"], employee_id=row["employee_id"],
        employee_name=row["employee_name"] or str(row["employee_id"]),
        leave_type_id=row["leave_type_id"], leave_code=row["leave_code"],
        leave_label=row["leave_label"], color=row["color"],
        start_date=row["start_date"], end_date=row["end_date"], half_day=row["half_day"],
        days=Decimal(row["days"]), reason=row["reason"], status=row["status"],
        approver_id=row["approver_id"],
        approver_name=await _name_of(session, row["approver_id"]),
        decision_note=row["decision_note"], decided_at=row["decided_at"],
        can_decide=can_decide, can_cancel=can_cancel,
    )


async def _get_request(
    session: AsyncSession, req_id: str, principal: Principal
) -> LeaveRequestOut:
    row = (
        await session.execute(text(_REQ_SELECT + " where r.id = :id"), {"id": req_id})
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Request not found")
    return await _decorate(session, dict(row), principal)


@router.get("/requests", response_model=list[LeaveRequestOut])
async def list_requests(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    scope: str = "mine",  # mine | pending | all
) -> list[LeaveRequestOut]:
    if scope == "mine":
        where, params = "where r.employee_id = :me", {"me": principal.employee_id}
    elif scope == "pending":
        # reports of this manager (or everyone for HR), pending only
        if principal.is_hr:
            where, params = "where r.status = 'pending'", {}
        else:
            where = """where r.status = 'pending' and r.employee_id in (
                         select employee_id from public.job_details
                         where reporting_manager = :me and is_active = 1)"""
            params = {"me": principal.employee_id}
    elif scope == "all":
        if not principal.is_hr:
            raise HTTPException(403, "Only HR can view all requests")
        where, params = "", {}
    else:
        raise HTTPException(422, "Invalid scope")

    rows = (
        await session.execute(
            text(_REQ_SELECT + " " + where + " order by r.created_at desc"), params
        )
    ).mappings().all()
    return [await _decorate(session, dict(r), principal) for r in rows]


# ---------------------------------------------------------------- decisions

async def _load_for_decision(session: AsyncSession, req_id: str) -> dict[str, Any]:
    row = (
        await session.execute(
            text("""select id::text, employee_id, leave_type_id::text, days, status
                    from ihrms.leave_request where id = :id"""),
            {"id": req_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Request not found")
    return dict(row)


def _release_pending(req: dict[str, Any]) -> str:
    return """update ihrms.leave_balance set pending = greatest(pending - :d, 0),
              updated_at = now()
              where employee_id = :emp and leave_type_id = :lt and period_year = :yr"""


@router.post("/requests/{req_id}/approve", response_model=LeaveRequestOut)
async def approve(
    req_id: str,
    payload: Decision,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> LeaveRequestOut:
    req = await _load_for_decision(session, req_id)
    if req["status"] != "pending":
        raise HTTPException(409, f"Request is already {req['status']}")
    if req["employee_id"] == principal.employee_id:
        raise HTTPException(403, "You cannot approve your own leave")
    mgr = await _manager_of(session, req["employee_id"])
    if not (principal.is_hr or mgr == principal.employee_id):
        raise HTTPException(403, "Only the reporting manager or HR can approve")

    year = (
        await session.execute(
            text("select extract(year from start_date)::int from ihrms.leave_request where id=:id"),
            {"id": req_id},
        )
    ).scalar()
    await session.execute(
        text(_release_pending(req) + " "),  # pending -days
        {"d": req["days"], "emp": req["employee_id"], "lt": req["leave_type_id"], "yr": year},
    )
    await session.execute(
        text("""update ihrms.leave_balance set used = used + :d, updated_at = now()
                where employee_id = :emp and leave_type_id = :lt and period_year = :yr"""),
        {"d": req["days"], "emp": req["employee_id"], "lt": req["leave_type_id"], "yr": year},
    )
    await session.execute(
        text("""update ihrms.leave_request set status='approved', approver_id=:by,
                decision_note=:note, decided_at=now(), updated_at=now() where id=:id"""),
        {"by": principal.employee_id, "note": payload.note, "id": req_id},
    )
    await record_audit(
        session, principal, "leave.approve", "leave_request", req_id,
        summary=f"Approved {req['days']} day(s)",
    )
    await session.commit()
    return await _get_request(session, req_id, principal)


@router.post("/requests/{req_id}/reject", response_model=LeaveRequestOut)
async def reject(
    req_id: str,
    payload: Decision,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> LeaveRequestOut:
    req = await _load_for_decision(session, req_id)
    if req["status"] != "pending":
        raise HTTPException(409, f"Request is already {req['status']}")
    if req["employee_id"] == principal.employee_id:
        raise HTTPException(403, "You cannot reject your own leave")
    mgr = await _manager_of(session, req["employee_id"])
    if not (principal.is_hr or mgr == principal.employee_id):
        raise HTTPException(403, "Only the reporting manager or HR can reject")

    year = (
        await session.execute(
            text("select extract(year from start_date)::int from ihrms.leave_request where id=:id"),
            {"id": req_id},
        )
    ).scalar()
    await session.execute(
        text(_release_pending(req)),
        {"d": req["days"], "emp": req["employee_id"], "lt": req["leave_type_id"], "yr": year},
    )
    await session.execute(
        text("""update ihrms.leave_request set status='rejected', approver_id=:by,
                decision_note=:note, decided_at=now(), updated_at=now() where id=:id"""),
        {"by": principal.employee_id, "note": payload.note, "id": req_id},
    )
    await record_audit(
        session, principal, "leave.reject", "leave_request", req_id,
        summary="Rejected leave request",
    )
    await session.commit()
    return await _get_request(session, req_id, principal)


@router.post("/requests/{req_id}/cancel", response_model=LeaveRequestOut)
async def cancel(
    req_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> LeaveRequestOut:
    req = await _load_for_decision(session, req_id)
    if req["status"] != "pending":
        raise HTTPException(
            409, f"Only pending requests can be cancelled (this is {req['status']})"
        )
    if req["employee_id"] != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only cancel your own request")

    year = (
        await session.execute(
            text("select extract(year from start_date)::int from ihrms.leave_request where id=:id"),
            {"id": req_id},
        )
    ).scalar()
    await session.execute(
        text(_release_pending(req)),
        {"d": req["days"], "emp": req["employee_id"], "lt": req["leave_type_id"], "yr": year},
    )
    await session.execute(
        text("""update ihrms.leave_request set status='cancelled', updated_at=now()
                where id=:id"""),
        {"id": req_id},
    )
    await record_audit(
        session, principal, "leave.cancel", "leave_request", req_id,
        summary="Cancelled leave request",
    )
    await session.commit()
    return await _get_request(session, req_id, principal)

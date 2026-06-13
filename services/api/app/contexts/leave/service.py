"""Leave domain logic — working days, accrual, balances, request lifecycle.

Money/quantity rules: leave quantities are Decimal (halves allowed), never
float. Working days exclude Sat/Sun (holiday calendar comes in a later pass).
"""

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

HALF = Decimal("0.5")
ONE = Decimal("1")


def working_days(
    start: date, end: date, half_day: bool, holidays: frozenset[date] = frozenset()
) -> Decimal:
    """Count working days inclusive, excluding weekends and `holidays`.
    Half-day only valid for a single working day."""
    if end < start:
        raise ValueError("End date is before start date")
    if half_day and start != end:
        raise ValueError("Half-day applies to a single day only")
    days = Decimal(0)
    cur = start
    while cur <= end:
        if cur.weekday() < 5 and cur not in holidays:  # 0=Mon … 4=Fri
            days += ONE
        cur += timedelta(days=1)
    if half_day:
        if days == 0:
            raise ValueError("Selected day is a weekend or holiday")
        return HALF
    return days


async def holidays_in_range(
    session: "AsyncSession", start: date, end: date
) -> frozenset[date]:
    """Active holidays for the tenant within [start, end]."""
    rows = (
        await session.execute(
            text("""select holiday_date from ihrms.holiday
                    where is_active and holiday_date between :s and :e"""),
            {"s": start, "e": end},
        )
    ).scalars().all()
    return frozenset(rows)


def accrued_to_date(
    method: str, annual: Decimal, monthly_rate: Decimal, today: date
) -> Decimal:
    """How much is accrued so far this leave year for a full-year employee.

    - annual_upfront / event_based: full entitlement available immediately
    - monthly: monthly_rate × months elapsed (incl. current month), capped
      at the annual entitlement
    """
    if method == "monthly":
        accrued = monthly_rate * Decimal(today.month)
        return min(accrued, annual)
    return annual


async def ensure_balance(
    session: AsyncSession, employee_id: int, leave_type_id: str, year: int, today: date
) -> dict[str, Any]:
    """Return the balance row for (employee, type, year), creating/refreshing
    the accrued figure from the leave type's accrual config."""
    lt = (
        await session.execute(
            text("""select accrual_method, annual_entitlement, monthly_rate
                    from ihrms.leave_type where id = :id"""),
            {"id": leave_type_id},
        )
    ).mappings().one()
    accrued = accrued_to_date(
        lt["accrual_method"], lt["annual_entitlement"], lt["monthly_rate"], today
    )

    existing = (
        await session.execute(
            text("""select id, entitled, accrued, carried_forward, used, pending
                    from ihrms.leave_balance
                    where employee_id = :emp and leave_type_id = :lt and period_year = :yr"""),
            {"emp": employee_id, "lt": leave_type_id, "yr": year},
        )
    ).mappings().first()

    if existing is None:
        row = (
            await session.execute(
                text("""insert into ihrms.leave_balance
                        (employee_id, leave_type_id, period_year, entitled, accrued)
                        values (:emp, :lt, :yr, :ent, :acc)
                        returning id, entitled, accrued, carried_forward, used, pending"""),
                {"emp": employee_id, "lt": leave_type_id, "yr": year,
                 "ent": lt["annual_entitlement"], "acc": accrued},
            )
        ).mappings().one()
        return dict(row)

    result = dict(existing)
    # refresh accrued (monthly types grow through the year)
    if result["accrued"] != accrued:
        await session.execute(
            text("""update ihrms.leave_balance set accrued = :acc, updated_at = now()
                    where id = :id"""),
            {"acc": accrued, "id": result["id"]},
        )
        result["accrued"] = accrued
    return result


def available(balance: dict[str, Any]) -> Decimal:
    """Days an employee can still take: accrued + carried_forward − used − pending."""
    return (
        Decimal(balance["accrued"])
        + Decimal(balance["carried_forward"])
        - Decimal(balance["used"])
        - Decimal(balance["pending"])
    )

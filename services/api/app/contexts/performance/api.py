"""Performance API — review cycles, reviews, goals, increments→payroll bridge."""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any

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
from app.contexts.payroll.salary import derive_structure
from app.contexts.performance.service import (
    apply_increment,
    nine_box,
    nine_box_label,
    suggested_increment_pct,
)
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/performance", tags=["performance"])
HR = require_roles(ROLE_HR_ADMIN)


# ---------------------------------------------------------------- goals

class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    description: str | None = None
    cycle_id: str | None = None


class GoalOut(BaseModel):
    id: str
    employee_id: int
    title: str
    description: str | None = None
    progress: int
    status: str


@router.get("/goals", response_model=list[GoalOut])
async def list_goals(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
    employee_id: int | None = None,
) -> list[GoalOut]:
    target = employee_id or principal.employee_id
    if target != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own goals")
    rows = (
        await session.execute(
            text("""select id::text, employee_id, title, description, progress, status
                    from ihrms.goal where employee_id = :emp order by created_at desc"""),
            {"emp": target},
        )
    ).mappings().all()
    return [GoalOut(**dict(r)) for r in rows]


@router.post("/goals", response_model=GoalOut, status_code=201)
async def add_goal(
    payload: GoalIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> GoalOut:
    row = (
        await session.execute(
            text("""insert into ihrms.goal (employee_id, cycle_id, title, description)
                    values (:emp, cast(nullif(:cyc,'') as uuid), :t, :d)
                    returning id::text, employee_id, title, description, progress, status"""),
            {"emp": principal.employee_id, "cyc": payload.cycle_id or "",
             "t": payload.title.strip(), "d": payload.description},
        )
    ).mappings().one()
    out = GoalOut(**dict(row))
    await session.commit()
    return out


class GoalProgress(BaseModel):
    progress: int = Field(ge=0, le=100)
    status: str | None = None


@router.patch("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: str,
    payload: GoalProgress,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> GoalOut:
    row = (
        await session.execute(
            text("""update ihrms.goal set progress = :p,
                       status = coalesce(:st, status), updated_at = now()
                    where id = :id and employee_id = :emp
                    returning id::text, employee_id, title, description, progress, status"""),
            {"p": payload.progress, "st": payload.status, "id": goal_id,
             "emp": principal.employee_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Goal not found")
    out = GoalOut(**dict(row))
    await session.commit()
    return out


# ---------------------------------------------------------------- cycles

class CycleIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    period_year: int = Field(ge=2020, le=2100)


class CycleOut(BaseModel):
    id: str
    name: str
    period_year: int
    status: str
    review_count: int = 0


@router.get("/cycles", response_model=list[CycleOut])
async def list_cycles(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[CycleOut]:
    rows = (
        await session.execute(
            text("""select c.id::text, c.name, c.period_year, c.status,
                       (select count(*) from ihrms.review r where r.cycle_id=c.id) as review_count
                    from ihrms.review_cycle c order by c.created_at desc""")
        )
    ).mappings().all()
    return [CycleOut(**dict(r)) for r in rows]


@router.post("/cycles", response_model=CycleOut, status_code=201)
async def add_cycle(
    payload: CycleIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> CycleOut:
    row = (
        await session.execute(
            text("""insert into ihrms.review_cycle (name, period_year, created_by)
                    values (:n, :y, :by) returning id::text, name, period_year, status"""),
            {"n": payload.name.strip(), "y": payload.period_year, "by": principal.employee_id},
        )
    ).mappings().one()
    out = CycleOut(**dict(row), review_count=0)
    await session.commit()
    return out


@router.post("/cycles/{cycle_id}/enroll", response_model=CycleOut)
async def enroll_cycle(
    cycle_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> CycleOut:
    """Create a review row for every active employee (idempotent), with the
    manager from job_details."""
    await session.execute(
        text("""insert into ihrms.review (cycle_id, employee_id, manager_id)
                select cast(:cyc as uuid), e.employee_id, jd.reporting_manager
                from public.employees e
                left join public.job_details jd
                       on jd.employee_id = e.employee_id and jd.is_active = 1
                where e.is_active = 1
                on conflict (tenant_id, cycle_id, employee_id) do nothing"""),
        {"cyc": cycle_id},
    )
    await record_audit(
        session, principal, "review.enroll", "review_cycle", cycle_id,
        summary="Enrolled active employees into the cycle",
    )
    cyc = (
        await session.execute(
            text("""select c.id::text, c.name, c.period_year, c.status,
                       (select count(*) from ihrms.review r where r.cycle_id=c.id) as review_count
                    from ihrms.review_cycle c where c.id = :id"""),
            {"id": cycle_id},
        )
    ).mappings().one()
    out = CycleOut(**dict(cyc))
    await session.commit()
    return out


# ---------------------------------------------------------------- reviews

class ReviewOut(BaseModel):
    id: str
    cycle_id: str
    employee_id: int
    employee_name: str
    manager_id: int | None = None
    self_rating: int | None = None
    self_comment: str | None = None
    manager_rating: int | None = None
    manager_comment: str | None = None
    potential: int | None = None
    final_rating: int | None = None
    status: str
    nine_box: int | None = None
    nine_box_label: str | None = None
    can_self: bool = False
    can_manage: bool = False


_REVIEW_SELECT = """
    select r.id::text, r.cycle_id::text, r.employee_id, r.manager_id,
           r.self_rating, r.self_comment, r.manager_rating, r.manager_comment,
           r.potential, r.final_rating, r.status,
           trim(concat(e.first_name,' ',coalesce(e.last_name,''))) as employee_name
    from ihrms.review r
    left join public.employees e on e.employee_id = r.employee_id
"""


def _to_review(row: dict[str, Any], principal: Principal) -> ReviewOut:
    cell = (
        nine_box(row["final_rating"], row["potential"])
        if row["final_rating"] and row["potential"]
        else None
    )
    return ReviewOut(
        id=row["id"], cycle_id=row["cycle_id"], employee_id=row["employee_id"],
        employee_name=row["employee_name"] or str(row["employee_id"]),
        manager_id=row["manager_id"], self_rating=row["self_rating"],
        self_comment=row["self_comment"], manager_rating=row["manager_rating"],
        manager_comment=row["manager_comment"], potential=row["potential"],
        final_rating=row["final_rating"], status=row["status"],
        nine_box=cell, nine_box_label=nine_box_label(cell) if cell else None,
        can_self=(row["employee_id"] == principal.employee_id
                  and row["status"] == "pending"),
        can_manage=((row["manager_id"] == principal.employee_id or principal.is_hr)
                    and row["status"] == "self_done"),
    )


@router.get("/cycles/{cycle_id}/reviews", response_model=list[ReviewOut])
async def cycle_reviews(
    cycle_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[ReviewOut]:
    rows = (
        await session.execute(
            text(_REVIEW_SELECT + " where r.cycle_id = cast(:c as uuid) order by employee_name"),
            {"c": cycle_id},
        )
    ).mappings().all()
    return [_to_review(dict(r), principal) for r in rows]


@router.get("/reviews/mine", response_model=list[ReviewOut])
async def my_reviews(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> list[ReviewOut]:
    rows = (
        await session.execute(
            text(_REVIEW_SELECT + " where r.employee_id = :me order by r.created_at desc"),
            {"me": principal.employee_id},
        )
    ).mappings().all()
    return [_to_review(dict(r), principal) for r in rows]


async def _get_review(session: AsyncSession, rid: str, principal: Principal) -> ReviewOut:
    row = (
        await session.execute(text(_REVIEW_SELECT + " where r.id = :id"), {"id": rid})
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Review not found")
    return _to_review(dict(row), principal)


class SelfRating(BaseModel):
    self_rating: int = Field(ge=1, le=5)
    self_comment: str | None = None


@router.post("/reviews/{rid}/self", response_model=ReviewOut)
async def submit_self(
    rid: str,
    payload: SelfRating,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ReviewOut:
    cur = await _get_review(session, rid, principal)
    if not cur.can_self:
        raise HTTPException(403, "Not your review, or self-review already done")
    await session.execute(
        text("""update ihrms.review set self_rating=:r, self_comment=:c,
                status='self_done', updated_at=now() where id=:id"""),
        {"r": payload.self_rating, "c": payload.self_comment, "id": rid},
    )
    result = await _get_review(session, rid, principal)
    await session.commit()
    return result


class ManagerRating(BaseModel):
    manager_rating: int = Field(ge=1, le=5)
    potential: int = Field(ge=1, le=5)
    manager_comment: str | None = None


@router.post("/reviews/{rid}/manager", response_model=ReviewOut)
async def submit_manager(
    rid: str,
    payload: ManagerRating,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> ReviewOut:
    cur = await _get_review(session, rid, principal)
    if not cur.can_manage:
        raise HTTPException(403, "Not the manager/HR, or self-review not yet done")
    await session.execute(
        text("""update ihrms.review set manager_rating=:r, potential=:p,
                manager_comment=:c, status='manager_done', updated_at=now() where id=:id"""),
        {"r": payload.manager_rating, "p": payload.potential, "c": payload.manager_comment,
         "id": rid},
    )
    result = await _get_review(session, rid, principal)
    await session.commit()
    return result


class Publish(BaseModel):
    final_rating: int | None = Field(default=None, ge=1, le=5)


@router.post("/reviews/{rid}/publish", response_model=ReviewOut)
async def publish_review(
    rid: str,
    payload: Publish,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ReviewOut:
    cur = await _get_review(session, rid, principal)
    if cur.status != "manager_done":
        raise HTTPException(409, "Manager review not yet done")
    final = payload.final_rating or cur.manager_rating
    await session.execute(
        text("""update ihrms.review set final_rating=:f, status='published',
                updated_at=now() where id=:id"""),
        {"f": final, "id": rid},
    )
    await record_audit(
        session, principal, "review.publish", "review", rid,
        summary=f"Published rating {final} for {cur.employee_name}",
    )
    result = await _get_review(session, rid, principal)
    await session.commit()
    return result


# ---------------------------------------------------------------- increments (payroll bridge)

class IncrementOut(BaseModel):
    id: str
    employee_id: int
    current_ctc: Decimal
    proposed_ctc: Decimal
    pct: Decimal
    effective_date: date
    status: str


@router.post("/reviews/{rid}/increment", response_model=IncrementOut, status_code=201)
async def propose_increment(
    rid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> IncrementOut:
    cur = await _get_review(session, rid, principal)
    if cur.status != "published" or not cur.final_rating:
        raise HTTPException(409, "Review must be published first")
    cur_ctc = (
        await session.execute(
            text("""select ctc_annual from ihrms.salary_structure
                    where employee_id = :emp and is_active"""),
            {"emp": cur.employee_id},
        )
    ).scalar()
    if cur_ctc is None:
        raise HTTPException(409, "Employee has no salary structure to increment")
    cur_ctc = Decimal(str(cur_ctc))
    pct = suggested_increment_pct(cur.final_rating)
    proposed = apply_increment(cur_ctc, pct)
    row = (
        await session.execute(
            text("""insert into ihrms.increment
                    (employee_id, cycle_id, current_ctc, proposed_ctc, pct, effective_date)
                    values (:emp, cast(:cyc as uuid), :cur, :prop, :pct, :eff)
                    returning id::text, employee_id, current_ctc, proposed_ctc, pct,
                              effective_date, status"""),
            {"emp": cur.employee_id, "cyc": cur.cycle_id, "cur": cur_ctc,
             "prop": proposed, "pct": pct, "eff": date(date.today().year, 4, 1)},
        )
    ).mappings().one()
    out = IncrementOut(**dict(row))
    await session.commit()
    return out


@router.post("/increments/{inc_id}/approve", response_model=IncrementOut)
async def approve_increment(
    inc_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> IncrementOut:
    row = (
        await session.execute(
            text("""update ihrms.increment set status='approved', approved_by=:by,
                    updated_at=now() where id=:id and status='proposed'
                    returning id::text, employee_id, current_ctc, proposed_ctc, pct,
                              effective_date, status"""),
            {"by": principal.employee_id, "id": inc_id},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(409, "Increment not found or not in proposed state")
    out = IncrementOut(**dict(row))
    await session.commit()
    return out


@router.post("/increments/{inc_id}/push", response_model=IncrementOut)
async def push_increment(
    inc_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> IncrementOut:
    """Push an approved increment into payroll: deactivate the current salary
    structure and create a new one at the proposed CTC. The M5→M3 bridge."""
    inc = (
        await session.execute(
            text("""select employee_id, proposed_ctc, effective_date, status
                    from ihrms.increment where id = :id"""),
            {"id": inc_id},
        )
    ).mappings().first()
    if inc is None or inc["status"] != "approved":
        raise HTTPException(409, "Increment must be approved before pushing")

    s = derive_structure(Decimal(str(inc["proposed_ctc"])))
    await session.execute(
        text("""update ihrms.salary_structure set is_active=false
                where employee_id=:emp and is_active"""),
        {"emp": inc["employee_id"]},
    )
    await session.execute(
        text("""insert into ihrms.salary_structure
                (employee_id, ctc_annual, basic, hra, special_allowance, effective_from)
                values (:emp, :ctc, :basic, :hra, :special, :eff)"""),
        {"emp": inc["employee_id"], "ctc": s.ctc_annual, "basic": s.basic, "hra": s.hra,
         "special": s.special_allowance, "eff": inc["effective_date"]},
    )
    row = (
        await session.execute(
            text("""update ihrms.increment set status='pushed', updated_at=now()
                    where id=:id returning id::text, employee_id, current_ctc,
                              proposed_ctc, pct, effective_date, status"""),
            {"id": inc_id},
        )
    ).mappings().one()
    await record_audit(
        session, principal, "increment.push", "employee", str(inc["employee_id"]),
        summary=f"Pushed increment to ₹{inc['proposed_ctc']} into payroll",
    )
    out = IncrementOut(**dict(row))
    await session.commit()
    return out

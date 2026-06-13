"""Recruitment / ATS API — requisitions, candidates, interviews, offers,
and onboarding a hired candidate into the employee master (no re-entry)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.core_hr.create import EmployeeCreate, create_employee
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    require_roles,
)
from app.contexts.payroll.salary import derive_structure
from app.contexts.recruitment.service import can_transition
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/recruitment", tags=["recruitment"])
HR = require_roles(ROLE_HR_ADMIN)


# ---------------------------------------------------------------- requisitions

class ReqIn(BaseModel):
    code: str = Field(min_length=1, max_length=40)
    title: str = Field(min_length=1, max_length=120)
    department: str | None = None
    location: str | None = None
    openings: int = Field(default=1, ge=1, le=999)


class ReqOut(BaseModel):
    id: str
    code: str
    title: str
    department: str | None = None
    location: str | None = None
    openings: int
    status: str
    candidate_count: int = 0


@router.get("/requisitions", response_model=list[ReqOut])
async def list_reqs(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[ReqOut]:
    rows = (
        await session.execute(
            text("""select r.id::text, r.code, r.title, r.department, r.location,
                       r.openings, r.status,
                       (select count(*) from ihrms.candidate c
                        where c.requisition_id = r.id) as candidate_count
                    from ihrms.requisition r order by r.created_at desc""")
        )
    ).mappings().all()
    return [ReqOut(**dict(r)) for r in rows]


@router.post("/requisitions", response_model=ReqOut, status_code=201)
async def add_req(
    payload: ReqIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> ReqOut:
    dup = (
        await session.execute(
            text("select 1 from ihrms.requisition where lower(code)=lower(:c)"),
            {"c": payload.code.strip()},
        )
    ).scalar()
    if dup:
        raise HTTPException(409, "A requisition with this code exists")
    row = (
        await session.execute(
            text("""insert into ihrms.requisition
                    (code, title, department, location, openings, created_by)
                    values (:c, :t, :d, :l, :o, :by)
                    returning id::text, code, title, department, location, openings, status"""),
            {"c": payload.code.strip(), "t": payload.title.strip(),
             "d": payload.department, "l": payload.location, "o": payload.openings,
             "by": principal.employee_id},
        )
    ).mappings().one()
    out = ReqOut(**dict(row), candidate_count=0)
    await session.commit()
    return out


# ---------------------------------------------------------------- candidates

class CandidateIn(BaseModel):
    requisition_id: str
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    phone: str | None = None
    source: str = "direct"


class CandidateOut(BaseModel):
    id: str
    requisition_id: str
    name: str
    email: str
    phone: str | None = None
    source: str
    stage: str
    rating: int | None = None
    bgv_status: str
    note: str | None = None
    onboarded_employee_id: int | None = None


async def _candidate(session: AsyncSession, cid: str) -> CandidateOut:
    row = (
        await session.execute(
            text("""select id::text, requisition_id::text, name, email, phone, source,
                       stage, rating, bgv_status, note, onboarded_employee_id
                    from ihrms.candidate where id = :id"""),
            {"id": cid},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "Candidate not found")
    return CandidateOut(**dict(row))


@router.get("/candidates", response_model=list[CandidateOut])
async def list_candidates(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
    requisition_id: str = "",
    stage: str = "",
) -> list[CandidateOut]:
    rows = (
        await session.execute(
            text("""select id::text, requisition_id::text, name, email, phone, source,
                       stage, rating, bgv_status, note, onboarded_employee_id
                    from ihrms.candidate
                    where (:req = '' or requisition_id = cast(nullif(:req,'') as uuid))
                      and (:stage = '' or stage = :stage)
                    order by created_at desc"""),
            {"req": requisition_id, "stage": stage},
        )
    ).mappings().all()
    return [CandidateOut(**dict(r)) for r in rows]


@router.post("/candidates", response_model=CandidateOut, status_code=201)
async def add_candidate(
    payload: CandidateIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> CandidateOut:
    cid = (
        await session.execute(
            text("""insert into ihrms.candidate (requisition_id, name, email, phone, source)
                    values (cast(:req as uuid), :n, :e, :p, :s) returning id::text"""),
            {"req": payload.requisition_id, "n": payload.name.strip(),
             "e": str(payload.email).lower(), "p": payload.phone, "s": payload.source},
        )
    ).scalar_one()
    result = await _candidate(session, cid)
    await session.commit()
    return result


class StageMove(BaseModel):
    stage: Literal["screening", "interview", "offer", "hired", "rejected"]


@router.post("/candidates/{cid}/stage", response_model=CandidateOut)
async def move_stage(
    cid: str,
    payload: StageMove,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> CandidateOut:
    cur = await _candidate(session, cid)
    if not can_transition(cur.stage, payload.stage):
        raise HTTPException(409, f"Cannot move from {cur.stage} to {payload.stage}")
    await session.execute(
        text("update ihrms.candidate set stage=:s, updated_at=now() where id=:id"),
        {"s": payload.stage, "id": cid},
    )
    await record_audit(
        session, principal, "candidate.stage", "candidate", cid,
        summary=f"{cur.name}: {cur.stage} → {payload.stage}",
    )
    result = await _candidate(session, cid)
    await session.commit()
    return result


class CandidatePatch(BaseModel):
    rating: int | None = Field(default=None, ge=1, le=5)
    bgv_status: Literal["consent", "in_progress", "clear", "flagged"] | None = None
    note: str | None = None


@router.patch("/candidates/{cid}", response_model=CandidateOut)
async def patch_candidate(
    cid: str,
    payload: CandidatePatch,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> CandidateOut:
    fields = payload.model_dump(exclude_unset=True)
    if fields:
        sets = ", ".join(f"{k} = :{k}" for k in fields)
        await session.execute(
            text(f"update ihrms.candidate set {sets}, updated_at=now() where id=:id"),
            {**fields, "id": cid},
        )
    result = await _candidate(session, cid)
    await session.commit()
    return result


# ---------------------------------------------------------------- interviews

class InterviewIn(BaseModel):
    round: str = Field(min_length=1, max_length=60)
    scheduled_at: datetime | None = None
    recommendation: Literal["yes", "no", "maybe"] | None = None
    feedback: str | None = None


class InterviewOut(BaseModel):
    id: str
    round: str
    scheduled_at: datetime | None = None
    recommendation: str | None = None
    feedback: str | None = None


@router.get("/candidates/{cid}/interviews", response_model=list[InterviewOut])
async def list_interviews(
    cid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> list[InterviewOut]:
    rows = (
        await session.execute(
            text("""select id::text, round, scheduled_at, recommendation, feedback
                    from ihrms.interview where candidate_id=:id order by created_at"""),
            {"id": cid},
        )
    ).mappings().all()
    return [InterviewOut(**dict(r)) for r in rows]


@router.post("/candidates/{cid}/interviews", response_model=InterviewOut, status_code=201)
async def add_interview(
    cid: str,
    payload: InterviewIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> InterviewOut:
    row = (
        await session.execute(
            text("""insert into ihrms.interview
                    (candidate_id, round, interviewer_id, scheduled_at, recommendation, feedback)
                    values (cast(:c as uuid), :r, :by, :sa, :rec, :fb)
                    returning id::text, round, scheduled_at, recommendation, feedback"""),
            {"c": cid, "r": payload.round.strip(), "by": principal.employee_id,
             "sa": payload.scheduled_at, "rec": payload.recommendation,
             "fb": payload.feedback},
        )
    ).mappings().one()
    out = InterviewOut(**dict(row))
    await session.commit()
    return out


# ---------------------------------------------------------------- offers

class OfferIn(BaseModel):
    designation: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=120)
    ctc_annual: Decimal = Field(gt=0)
    joining_date: date


class OfferOut(BaseModel):
    id: str
    candidate_id: str
    designation: str
    department: str
    ctc_annual: Decimal
    joining_date: date
    status: str


@router.get("/candidates/{cid}/offer", response_model=OfferOut)
async def get_offer(
    cid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> OfferOut:
    row = (
        await session.execute(
            text("""select id::text, candidate_id::text, designation, department,
                       ctc_annual, joining_date, status
                    from ihrms.offer where candidate_id=:id
                    order by created_at desc limit 1"""),
            {"id": cid},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(404, "No offer for this candidate")
    return OfferOut(**dict(row))


@router.post("/candidates/{cid}/offer", response_model=OfferOut, status_code=201)
async def make_offer(
    cid: str,
    payload: OfferIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> OfferOut:
    cur = await _candidate(session, cid)
    if cur.stage not in ("interview", "offer"):
        raise HTTPException(409, "Candidate must reach the interview stage first")
    row = (
        await session.execute(
            text("""insert into ihrms.offer
                    (candidate_id, designation, department, ctc_annual, joining_date,
                     status, created_by)
                    values (cast(:c as uuid), :des, :dep, :ctc, :jd, 'sent', :by)
                    returning id::text, candidate_id::text, designation, department,
                              ctc_annual, joining_date, status"""),
            {"c": cid, "des": payload.designation.strip(), "dep": payload.department.strip(),
             "ctc": payload.ctc_annual, "jd": payload.joining_date,
             "by": principal.employee_id},
        )
    ).mappings().one()
    if cur.stage == "interview":
        await session.execute(
            text("update ihrms.candidate set stage='offer', updated_at=now() where id=:id"),
            {"id": cid},
        )
    await record_audit(
        session, principal, "offer.made", "candidate", cid,
        summary=f"Offer to {cur.name}: {payload.designation} @ ₹{payload.ctc_annual}",
    )
    out = OfferOut(**dict(row))
    await session.commit()
    return out


@router.post("/candidates/{cid}/offer/accept", response_model=OfferOut)
async def accept_offer(
    cid: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> OfferOut:
    row = (
        await session.execute(
            text("""update ihrms.offer set status='accepted', updated_at=now()
                    where candidate_id=:id and status='sent'
                    returning id::text, candidate_id::text, designation, department,
                              ctc_annual, joining_date, status"""),
            {"id": cid},
        )
    ).mappings().first()
    if row is None:
        raise HTTPException(409, "No sent offer to accept")
    out = OfferOut(**dict(row))
    await session.commit()
    return out


# ---------------------------------------------------------------- onboard

class OnboardIn(BaseModel):
    employee_code: str = Field(min_length=1, max_length=40)
    division: str = Field(min_length=1, max_length=120)
    branch: str = Field(min_length=1, max_length=120)
    circle_id: int
    reporting_manager_id: int | None = None


class OnboardOut(BaseModel):
    candidate_id: str
    employee_id: int
    employee_code: str


@router.post("/candidates/{cid}/onboard", response_model=OnboardOut, status_code=201)
async def onboard(
    cid: str,
    payload: OnboardIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> OnboardOut:
    """Convert an accepted-offer candidate into a fully-provisioned employee:
    creates the employee in the shared master AND sets their salary structure
    from the offer — the M4 'no re-entry' exit criterion."""
    cur = await _candidate(session, cid)
    if cur.onboarded_employee_id:
        raise HTTPException(409, "Candidate is already onboarded")
    offer = (
        await session.execute(
            text("""select designation, department, ctc_annual, joining_date
                    from ihrms.offer where candidate_id=:id and status='accepted'
                    order by created_at desc limit 1"""),
            {"id": cid},
        )
    ).mappings().first()
    if offer is None:
        raise HTTPException(409, "Candidate has no accepted offer")

    parts = cur.name.split()
    first = parts[0]
    last = " ".join(parts[1:]) or None
    try:
        employee_id = await create_employee(
            session,
            EmployeeCreate(
                first_name=first, middle_name=None, last_name=last,
                email=cur.email, phone=cur.phone or "0000000000",
                employee_code=payload.employee_code, gender=None, date_of_birth=None,
                designation=offer["designation"], department=offer["department"],
                division=payload.division, branch=payload.branch,
                circle_id=payload.circle_id,
                reporting_manager_id=payload.reporting_manager_id,
                date_of_joining=offer["joining_date"],
            ),
        )
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc

    # set salary structure from the offer CTC (reuses M3 derivation)
    s = derive_structure(Decimal(str(offer["ctc_annual"])))
    await session.execute(
        text("""insert into ihrms.salary_structure
                (employee_id, ctc_annual, basic, hra, special_allowance, effective_from)
                values (:emp, :ctc, :basic, :hra, :special, :eff)"""),
        {"emp": employee_id, "ctc": s.ctc_annual, "basic": s.basic, "hra": s.hra,
         "special": s.special_allowance, "eff": offer["joining_date"]},
    )
    await session.execute(
        text("""update ihrms.candidate set stage='hired', onboarded_employee_id=:eid,
                updated_at=now() where id=:id"""),
        {"eid": employee_id, "id": cid},
    )
    await record_audit(
        session, principal, "candidate.onboard", "candidate", cid,
        summary=f"Onboarded {cur.name} as employee {payload.employee_code}",
        changes={"employee_id": employee_id},
    )
    await session.commit()
    return OnboardOut(candidate_id=cid, employee_id=employee_id,
                      employee_code=payload.employee_code)

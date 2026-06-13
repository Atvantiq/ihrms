"""Employee personal records API — the Employee 360 sub-tabs.

One bundle read (`/employees/{id}/records`) returns family/nominees, education,
experience, awards, training, incidents and the derived special dates in a
single round-trip. Writes are HR-only, audited and tenant-scoped; each record
type has a typed create and a delete. The employee themselves may read their
own bundle (same gate as PII), nobody else but HR.
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.employee_records.service import nominee_total_ok, special_dates
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.audit import record_audit
from app.core.db import get_session

router = APIRouter(prefix="/employees", tags=["employee-records"])
HR = require_roles(ROLE_HR_ADMIN)

# resource key -> (table, ordering column)
_RESOURCES: dict[str, tuple[str, str]] = {
    "family": ("employee_family", "is_nominee desc, relation"),
    "education": ("employee_education", "year_completed desc nulls last"),
    "experience": ("employee_experience", "from_date desc nulls last"),
    "awards": ("employee_award", "awarded_on desc nulls last"),
    "training": ("employee_training", "completed_on desc nulls last, program"),
    "incidents": ("employee_incident", "incident_date desc"),
}


# ----------------------------------------------------------------- models

class FamilyMember(BaseModel):
    id: str
    relation: str
    full_name: str
    date_of_birth: date | None = None
    gender: str | None = None
    is_dependent: bool
    is_nominee: bool
    nominee_share: Decimal
    contact: str | None = None


class FamilyIn(BaseModel):
    relation: Literal["spouse", "child", "father", "mother", "sibling", "guardian", "other"]
    full_name: str = Field(min_length=1, max_length=120)
    date_of_birth: date | None = None
    gender: str | None = None
    is_dependent: bool = False
    is_nominee: bool = False
    nominee_share: Decimal = Field(default=Decimal(0), ge=0, le=100)
    contact: str | None = None


class Education(BaseModel):
    id: str
    degree: str
    specialization: str | None = None
    institution: str | None = None
    year_completed: int | None = None
    grade: str | None = None


class EducationIn(BaseModel):
    degree: str = Field(min_length=1, max_length=120)
    specialization: str | None = None
    institution: str | None = None
    year_completed: int | None = Field(default=None, ge=1950, le=2100)
    grade: str | None = None


class Experience(BaseModel):
    id: str
    employer: str
    designation: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    summary: str | None = None


class ExperienceIn(BaseModel):
    employer: str = Field(min_length=1, max_length=160)
    designation: str | None = None
    from_date: date | None = None
    to_date: date | None = None
    summary: str | None = None


class Award(BaseModel):
    id: str
    title: str
    category: str | None = None
    awarded_on: date | None = None
    citation: str | None = None


class AwardIn(BaseModel):
    title: str = Field(min_length=1, max_length=160)
    category: str | None = None
    awarded_on: date | None = None
    citation: str | None = None


class Training(BaseModel):
    id: str
    program: str
    provider: str | None = None
    status: str
    completed_on: date | None = None


class TrainingIn(BaseModel):
    program: str = Field(min_length=1, max_length=160)
    provider: str | None = None
    status: Literal["planned", "in_progress", "completed", "cancelled"] = "planned"
    completed_on: date | None = None


class Incident(BaseModel):
    id: str
    kind: str
    incident_date: date
    category: str | None = None
    severity: str
    description: str
    action_taken: str | None = None
    status: str


class IncidentIn(BaseModel):
    kind: Literal["disciplinary", "accident"]
    incident_date: date
    category: str | None = None
    severity: Literal["low", "medium", "high"] = "low"
    description: str = Field(min_length=1)
    action_taken: str | None = None
    status: Literal["open", "closed"] = "open"


class SpecialDateOut(BaseModel):
    label: str
    on: date
    in_days: int
    years: int | None = None


class RecordsBundle(BaseModel):
    employee_id: int
    family: list[FamilyMember]
    education: list[Education]
    experience: list[Experience]
    awards: list[Award]
    training: list[Training]
    incidents: list[Incident]
    special_dates: list[SpecialDateOut]
    nominee_total: Decimal


# ----------------------------------------------------------------- helpers

async def _ensure_can_read(employee_id: int, principal: Principal) -> None:
    if employee_id != principal.employee_id and not principal.is_hr:
        raise HTTPException(403, "You can only view your own records")


async def _ensure_employee(session: AsyncSession, employee_id: int) -> None:
    exists = (
        await session.execute(
            text("select 1 from public.employees where employee_id = :e"),
            {"e": employee_id},
        )
    ).scalar()
    if exists is None:
        raise HTTPException(404, "Employee not found")


def _to[T: BaseModel](model: type[T], row: dict[str, Any]) -> T:
    """Build a response model from a DB row, stringifying the uuid id."""
    data = {**row, "id": str(row["id"])}
    return model(**{k: data[k] for k in model.model_fields})


async def _rows(
    session: AsyncSession, resource: str, employee_id: int
) -> list[dict[str, Any]]:
    table, order = _RESOURCES[resource]
    res = await session.execute(
        text(f"select * from ihrms.{table} where employee_id = :e order by {order}"),
        {"e": employee_id},
    )
    return [dict(r) for r in res.mappings().all()]


# ----------------------------------------------------------------- bundle read

@router.get("/{employee_id}/records", response_model=RecordsBundle)
async def get_records(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> RecordsBundle:
    await _ensure_can_read(employee_id, principal)
    emp = (
        await session.execute(
            text("""select e.date_of_birth, j.date_of_joining
                    from public.employees e
                    left join public.job_details j on j.employee_id = e.employee_id
                    where e.employee_id = :e"""),
            {"e": employee_id},
        )
    ).mappings().first()
    if emp is None:
        raise HTTPException(404, "Employee not found")

    fam = await _rows(session, "family", employee_id)
    return RecordsBundle(
        employee_id=employee_id,
        family=[_to(FamilyMember, r) for r in fam],
        education=[_to(Education, r) for r in await _rows(session, "education", employee_id)],
        experience=[_to(Experience, r) for r in await _rows(session, "experience", employee_id)],
        awards=[_to(Award, r) for r in await _rows(session, "awards", employee_id)],
        training=[_to(Training, r) for r in await _rows(session, "training", employee_id)],
        incidents=[_to(Incident, r) for r in await _rows(session, "incidents", employee_id)],
        special_dates=[
            SpecialDateOut(label=s.label, on=s.on, in_days=s.in_days, years=s.years)
            for s in special_dates(emp["date_of_birth"], emp["date_of_joining"], date.today())
        ],
        nominee_total=sum(
            (Decimal(str(r["nominee_share"])) for r in fam if r["is_nominee"]), Decimal(0)
        ),
    )


# ----------------------------------------------------------------- creates

@router.post("/{employee_id}/family", response_model=FamilyMember, status_code=201)
async def add_family(
    employee_id: int,
    payload: FamilyIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> FamilyMember:
    await _ensure_employee(session, employee_id)
    if payload.is_nominee:
        existing = (
            await session.execute(
                text("""select coalesce(sum(nominee_share),0) from ihrms.employee_family
                        where employee_id = :e and is_nominee"""),
                {"e": employee_id},
            )
        ).scalar_one()
        if not nominee_total_ok([Decimal(str(existing))], payload.nominee_share):
            raise HTTPException(422, "Nominee shares would exceed 100%")
    row = (
        await session.execute(
            text("""insert into ihrms.employee_family
                    (employee_id, relation, full_name, date_of_birth, gender,
                     is_dependent, is_nominee, nominee_share, contact, created_by)
                    values (:e, :rel, :n, :dob, :g, :dep, :nom, :share, :c, :by)
                    returning *"""),
            {"e": employee_id, "rel": payload.relation, "n": payload.full_name,
             "dob": payload.date_of_birth, "g": payload.gender,
             "dep": payload.is_dependent, "nom": payload.is_nominee,
             "share": payload.nominee_share, "c": payload.contact,
             "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(session, principal, "employee_family.add", "employee_family",
                       str(row["id"]), summary=f"Family record for {employee_id}")
    out = _to(FamilyMember, dict(row))
    await session.commit()
    return out


@router.post("/{employee_id}/education", response_model=Education, status_code=201)
async def add_education(
    employee_id: int,
    payload: EducationIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Education:
    await _ensure_employee(session, employee_id)
    row = (
        await session.execute(
            text("""insert into ihrms.employee_education
                    (employee_id, degree, specialization, institution, year_completed,
                     grade, created_by)
                    values (:e, :d, :s, :i, :y, :g, :by) returning *"""),
            {"e": employee_id, "d": payload.degree, "s": payload.specialization,
             "i": payload.institution, "y": payload.year_completed, "g": payload.grade,
             "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(session, principal, "employee_education.add", "employee_education",
                       str(row["id"]), summary=f"Education {payload.degree} for {employee_id}")
    out = _to(Education, dict(row))
    await session.commit()
    return out


@router.post("/{employee_id}/experience", response_model=Experience, status_code=201)
async def add_experience(
    employee_id: int,
    payload: ExperienceIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Experience:
    await _ensure_employee(session, employee_id)
    row = (
        await session.execute(
            text("""insert into ihrms.employee_experience
                    (employee_id, employer, designation, from_date, to_date, summary, created_by)
                    values (:e, :emp, :des, :f, :t, :s, :by) returning *"""),
            {"e": employee_id, "emp": payload.employer, "des": payload.designation,
             "f": payload.from_date, "t": payload.to_date, "s": payload.summary,
             "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(session, principal, "employee_experience.add", "employee_experience",
                       str(row["id"]), summary=f"Experience for {employee_id}")
    out = _to(Experience, dict(row))
    await session.commit()
    return out


@router.post("/{employee_id}/awards", response_model=Award, status_code=201)
async def add_award(
    employee_id: int,
    payload: AwardIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Award:
    await _ensure_employee(session, employee_id)
    row = (
        await session.execute(
            text("""insert into ihrms.employee_award
                    (employee_id, title, category, awarded_on, citation, created_by)
                    values (:e, :t, :c, :on, :cit, :by) returning *"""),
            {"e": employee_id, "t": payload.title, "c": payload.category,
             "on": payload.awarded_on, "cit": payload.citation, "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(session, principal, "employee_award.add", "employee_award",
                       str(row["id"]), summary=f"Award {payload.title} for {employee_id}")
    out = _to(Award, dict(row))
    await session.commit()
    return out


@router.post("/{employee_id}/training", response_model=Training, status_code=201)
async def add_training(
    employee_id: int,
    payload: TrainingIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Training:
    await _ensure_employee(session, employee_id)
    row = (
        await session.execute(
            text("""insert into ihrms.employee_training
                    (employee_id, program, provider, status, completed_on, created_by)
                    values (:e, :p, :pr, :s, :on, :by) returning *"""),
            {"e": employee_id, "p": payload.program, "pr": payload.provider,
             "s": payload.status, "on": payload.completed_on, "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(session, principal, "employee_training.add", "employee_training",
                       str(row["id"]), summary=f"Training {payload.program} for {employee_id}")
    out = _to(Training, dict(row))
    await session.commit()
    return out


@router.post("/{employee_id}/incidents", response_model=Incident, status_code=201)
async def add_incident(
    employee_id: int,
    payload: IncidentIn,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> Incident:
    await _ensure_employee(session, employee_id)
    row = (
        await session.execute(
            text("""insert into ihrms.employee_incident
                    (employee_id, kind, incident_date, category, severity, description,
                     action_taken, status, created_by)
                    values (:e, :k, :d, :c, :sev, :desc, :act, :st, :by) returning *"""),
            {"e": employee_id, "k": payload.kind, "d": payload.incident_date,
             "c": payload.category, "sev": payload.severity, "desc": payload.description,
             "act": payload.action_taken, "st": payload.status, "by": principal.employee_id},
        )
    ).mappings().one()
    await record_audit(session, principal, "employee_incident.add", "employee_incident",
                       str(row["id"]), summary=f"{payload.kind} incident for {employee_id}")
    out = _to(Incident, dict(row))
    await session.commit()
    return out


# ----------------------------------------------------------------- delete

@router.delete("/{employee_id}/records/{resource}/{record_id}", status_code=204)
async def delete_record(
    employee_id: int,
    resource: str,
    record_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, HR],
) -> None:
    if resource not in _RESOURCES:
        raise HTTPException(404, "Unknown record type")
    table = _RESOURCES[resource][0]
    await session.execute(
        text(f"""delete from ihrms.{table}
                 where id = cast(:id as uuid) and employee_id = :e"""),
        {"id": record_id, "e": employee_id},
    )
    await record_audit(session, principal, f"{table}.delete", table, record_id,
                       summary=f"Deleted {resource} record for {employee_id}")
    await session.commit()

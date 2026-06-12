"""Employee creation — writes to the SHARED ONAQT tables.

Contract (blueprint doc 24 §24.2 rule 4): follow ONAQT's conventions exactly —
ID drawn from public.global_ids (12-digit registry), smallint flags,
employees + job_details inserted in ONE transaction. Nothing is altered
structurally; we only add rows the way the existing app does.
"""

import secrets
from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class EmployeeCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=80)
    middle_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    employee_code: str = Field(min_length=1, max_length=40)
    gender: str | None = None
    date_of_birth: date | None = None

    designation: str = Field(min_length=1, max_length=120)
    department: str = Field(min_length=1, max_length=120)
    division: str = Field(min_length=1, max_length=120)
    branch: str = Field(min_length=1, max_length=120)
    circle_id: int
    reporting_manager_id: int | None = None
    date_of_joining: date

    @field_validator("first_name", "middle_name", "last_name", "employee_code")
    @classmethod
    def strip_text(cls, v: str | None) -> str | None:
        return v.strip() if v is not None else None


class DirectoryMeta(BaseModel):
    """Existing values for form dropdowns (free text today; masters come later)."""

    departments: list[str]
    divisions: list[str]
    branches: list[str]
    designations: list[str]
    circle_ids: list[int]


async def fetch_meta(session: AsyncSession) -> DirectoryMeta:
    rows = (
        await session.execute(
            text("""select
              array(select distinct department from public.job_details
                    where department is not null order by 1) as departments,
              array(select distinct division from public.job_details
                    where division is not null order by 1) as divisions,
              array(select distinct branch from public.job_details
                    where branch is not null order by 1) as branches,
              array(select distinct designation from public.job_details
                    where designation is not null order by 1) as designations,
              array(select distinct circle_id from public.job_details
                    order by 1) as circle_ids
            """)
        )
    ).mappings().one()
    return DirectoryMeta(**dict(rows))


async def _new_global_id(session: AsyncSession) -> int:
    """Draw a fresh 12-digit id from the shared registry (ONAQT convention)."""
    for _ in range(10):
        candidate = secrets.randbelow(900_000_000_000) + 100_000_000_000
        inserted = (
            await session.execute(
                text("""insert into public.global_ids (id) values (:id)
                        on conflict (id) do nothing returning id"""),
                {"id": candidate},
            )
        ).scalar()
        if inserted is not None:
            return candidate
    raise RuntimeError("Could not allocate a unique global id")


async def create_employee(session: AsyncSession, payload: EmployeeCreate) -> int:
    """Insert employee + job assignment in one transaction; returns employee_id."""
    dup = (
        await session.execute(
            text("""select
              exists(select 1 from public.employees where lower(email)=lower(:email)) as email_taken,
              exists(select 1 from public.employees where lower(employee_code)=lower(:code)) as code_taken
            """),
            {"email": payload.email, "code": payload.employee_code},
        )
    ).mappings().one()
    if dup["email_taken"]:
        raise ValueError("An employee with this email already exists")
    if dup["code_taken"]:
        raise ValueError("This employee code is already in use")

    if payload.reporting_manager_id is not None:
        mgr = (
            await session.execute(
                text("select 1 from public.employees where employee_id = :id"),
                {"id": payload.reporting_manager_id},
            )
        ).scalar()
        if mgr is None:
            raise ValueError("Reporting manager not found")

    employee_id = await _new_global_id(session)
    short_name = payload.first_name.split()[0]

    await session.execute(
        text("""insert into public.employees
            (employee_id, employee_code, email, first_name, middle_name, last_name,
             short_name, phone, date_of_birth, gender, is_active)
            values (:employee_id, :employee_code, :email, :first_name, :middle_name,
                    :last_name, :short_name, :phone, :date_of_birth, :gender, 1)"""),
        {
            "employee_id": employee_id,
            "employee_code": payload.employee_code,
            "email": str(payload.email).lower(),
            "first_name": payload.first_name,
            "middle_name": payload.middle_name,
            "last_name": payload.last_name,
            "short_name": short_name,
            "phone": payload.phone,
            "date_of_birth": payload.date_of_birth,
            "gender": payload.gender,
        },
    )
    await session.execute(
        text("""insert into public.job_details
            (employee_id, designation, circle_id, branch, department, division,
             reporting_manager, date_of_joining, is_active)
            values (:employee_id, :designation, :circle_id, :branch, :department,
                    :division, :reporting_manager, :date_of_joining, 1)"""),
        {
            "employee_id": employee_id,
            "designation": payload.designation,
            "circle_id": payload.circle_id,
            "branch": payload.branch,
            "department": payload.department,
            "division": payload.division,
            "reporting_manager": payload.reporting_manager_id,
            "date_of_joining": payload.date_of_joining,
        },
    )
    await session.commit()
    return employee_id

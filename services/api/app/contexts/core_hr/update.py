"""Employee updates — writes to the SHARED ONAQT tables (doc 24 contract).

- employees / job_details rows are UPDATEd in place, conventions preserved.
- employee_details (PAN, Aadhaar, family) is update-or-insert: the table has
  no unique constraint on employee_id, so we check-then-write explicitly.
- email is IMMUTABLE here: it is the auth link for both apps; changing it
  is a separate, deliberate flow (auth + employee together) in a later pass.
"""

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.validators import validate_aadhaar, validate_pan


class EmployeeUpdate(BaseModel):
    """Partial update — only provided fields are written."""

    first_name: str | None = Field(default=None, min_length=1, max_length=80)
    middle_name: str | None = None
    last_name: str | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    gender: str | None = None
    date_of_birth: date | None = None

    designation: str | None = Field(default=None, min_length=1, max_length=120)
    department: str | None = Field(default=None, min_length=1, max_length=120)
    division: str | None = Field(default=None, min_length=1, max_length=120)
    branch: str | None = Field(default=None, min_length=1, max_length=120)
    circle_id: int | None = None
    reporting_manager_id: int | None = None
    date_of_joining: date | None = None
    date_of_leaving: date | None = None

    fathers_name: str | None = None
    mothers_name: str | None = None
    marital_status: str | None = None
    spouse_name: str | None = None
    alternate_phone: str | None = None
    pan_no: str | None = None
    aadhaar_no: str | None = None

    @field_validator("pan_no")
    @classmethod
    def _pan(cls, v: str | None) -> str | None:
        # blank clears the field; otherwise validate + normalise
        return None if not (v and v.strip()) else validate_pan(v)

    @field_validator("aadhaar_no")
    @classmethod
    def _aadhaar(cls, v: str | None) -> str | None:
        return None if not (v and v.strip()) else validate_aadhaar(v)


_EMPLOYEE_COLS = ("first_name", "middle_name", "last_name", "phone", "gender", "date_of_birth")
_JOB_COLS = (
    "designation", "department", "division", "branch", "circle_id",
    "reporting_manager_id", "date_of_joining", "date_of_leaving",
)
_DETAIL_COLS = (
    "fathers_name", "mothers_name", "marital_status", "spouse_name",
    "alternate_phone", "pan_no", "aadhaar_no",
)
# employee_details uses 'adhar_no' (ONAQT spelling); job_details uses 'reporting_manager'
_DB_NAMES = {"aadhaar_no": "adhar_no", "reporting_manager_id": "reporting_manager"}


async def update_employee(
    session: AsyncSession, employee_id: int, payload: EmployeeUpdate
) -> None:
    exists = (
        await session.execute(
            text("select 1 from public.employees where employee_id = :id"),
            {"id": employee_id},
        )
    ).scalar()
    if exists is None:
        raise LookupError("Employee not found")

    fields: dict[str, Any] = payload.model_dump(exclude_unset=True)

    if "reporting_manager_id" in fields and fields["reporting_manager_id"] is not None:
        if fields["reporting_manager_id"] == employee_id:
            raise ValueError("An employee cannot report to themselves")
        mgr = (
            await session.execute(
                text("select 1 from public.employees where employee_id = :id"),
                {"id": fields["reporting_manager_id"]},
            )
        ).scalar()
        if mgr is None:
            raise ValueError("Reporting manager not found")

    def write_set(cols: tuple[str, ...]) -> tuple[str, dict[str, Any]]:
        sets, params = [], {}
        for col in cols:
            if col in fields:
                db_col = _DB_NAMES.get(col, col)
                sets.append(f"{db_col} = :{col}")
                params[col] = fields[col]
        return ", ".join(sets), params

    emp_set, emp_params = write_set(_EMPLOYEE_COLS)
    if emp_set:
        await session.execute(
            text(f"""update public.employees set {emp_set}, updated_at = now()
                     where employee_id = :employee_id"""),
            {**emp_params, "employee_id": employee_id},
        )

    job_set, job_params = write_set(_JOB_COLS)
    if job_set:
        await session.execute(
            text(f"""update public.job_details set {job_set}, updated_at = now()
                     where employee_id = :employee_id and is_active = 1"""),
            {**job_params, "employee_id": employee_id},
        )

    detail_set, detail_params = write_set(_DETAIL_COLS)
    if detail_set:
        has_row = (
            await session.execute(
                text("select 1 from public.employee_details where employee_id = :id limit 1"),
                {"id": employee_id},
            )
        ).scalar()
        if has_row:
            await session.execute(
                text(f"""update public.employee_details set {detail_set}, updated_at = now()
                         where employee_id = :employee_id"""),
                {**detail_params, "employee_id": employee_id},
            )
        else:
            cols = [_DB_NAMES.get(c, c) for c in detail_params]
            placeholders = [f":{c}" for c in detail_params]
            await session.execute(
                text(f"""insert into public.employee_details
                         (employee_id, {", ".join(cols)})
                         values (:employee_id, {", ".join(placeholders)})"""),
                {**detail_params, "employee_id": employee_id},
            )


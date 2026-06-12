"""Directory read model over ihrms.v_employee (shared ONAQT data).

Status derivation (single source of truth):
- Notice    — date_of_leaving set and today or later (serving notice)
- Joining   — date_of_joining in the future
- Inactive  — is_active flag off (or already left)
- Probation — joined within the last 90 days
- Active    — everything else
"""

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

PROBATION_DAYS = 90

_BASE_QUERY = text("""
    select v.employee_id, v.employee_code, v.email,
           v.first_name, v.middle_name, v.last_name, v.short_name,
           v.phone, v.date_of_birth, v.gender, v.is_active,
           v.designation_c as designation, v.department_c as department,
           v.division_c as division, v.branch_c as branch, v.circle_id,
           v.reporting_manager_id, v.date_of_joining, v.date_of_leaving,
           v.fathers_name, v.mothers_name, v.marital_status, v.spouse_name,
           v.alternate_phone, v.pan_no, v.aadhaar_no,
           trim(concat(m.first_name, ' ', coalesce(m.last_name, ''))) as manager_name
    from ihrms.v_employee v
    left join ihrms.v_employee m on m.employee_id = v.reporting_manager_id
    order by v.first_name, v.last_name
""")


def derive_status(row: dict[str, Any], today: date) -> str:
    dol: date | None = row["date_of_leaving"]
    doj: date | None = row["date_of_joining"]
    if dol is not None and dol >= today:
        return "Notice"
    if doj is not None and doj > today:
        return "Joining"
    if not row["is_active"] or (dol is not None and dol < today):
        return "Inactive"
    if doj is not None and (today - doj).days <= PROBATION_DAYS:
        return "Probation"
    return "Active"


def tenure_label(doj: date | None, today: date) -> str:
    if doj is None or doj > today:
        return "—"
    months = (today.year - doj.year) * 12 + (today.month - doj.month)
    if today.day < doj.day:
        months -= 1
    return f"{months // 12}y {months % 12}m"


def full_name(row: dict[str, Any]) -> str:
    parts = [row["first_name"], row["middle_name"], row["last_name"]]
    return " ".join(p.strip() for p in parts if p and p.strip())


async def fetch_directory(session: AsyncSession) -> list[dict[str, Any]]:
    result = await session.execute(_BASE_QUERY)
    return [dict(r) for r in result.mappings().all()]

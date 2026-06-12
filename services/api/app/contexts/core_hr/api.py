from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.core_hr.schemas import (
    DirectoryStats,
    EmployeeDetail,
    EmployeeListItem,
    EmployeeListOut,
)
from app.contexts.core_hr.service import derive_status, fetch_directory, full_name, tenure_label
from app.core.db import get_session
from app.core.security import require_user

router = APIRouter(prefix="/employees", tags=["employees"], dependencies=[Depends(require_user)])


def _to_list_item(row: dict[str, Any], today: date) -> EmployeeListItem:
    return EmployeeListItem(
        employee_id=row["employee_id"],
        employee_code=row["employee_code"],
        full_name=full_name(row),
        email=row["email"],
        designation=row["designation"],
        department=row["department"],
        branch=row["branch"],
        manager_name=row["manager_name"] or None,
        date_of_joining=row["date_of_joining"],
        tenure=tenure_label(row["date_of_joining"], today),
        status=derive_status(row, today),
    )


@router.get("", response_model=EmployeeListOut)
async def list_employees(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str = "",
    department: str = "",
    status: str = "",
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
) -> EmployeeListOut:
    today = date.today()
    rows = await fetch_directory(session)

    all_items = [_to_list_item(r, today) for r in rows]
    stats = DirectoryStats(
        total=len(all_items),
        active=sum(1 for i in all_items if i.status == "Active"),
        probation=sum(1 for i in all_items if i.status == "Probation"),
        joining=sum(1 for i in all_items if i.status == "Joining"),
        notice=sum(1 for i in all_items if i.status == "Notice"),
        inactive=sum(1 for i in all_items if i.status == "Inactive"),
        departments=sorted({i.department for i in all_items if i.department}),
    )

    needle = q.strip().lower()
    matches = [
        i
        for i in all_items
        if (
            not needle
            or needle in i.full_name.lower()
            or needle in i.email.lower()
            or needle in i.employee_code.lower()
        )
        and (not department or i.department == department)
        and (not status or i.status == status)
    ]
    return EmployeeListOut(
        items=matches[offset : offset + limit],
        total_matches=len(matches),
        stats=stats,
    )


@router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EmployeeDetail:
    today = date.today()
    rows = await fetch_directory(session)
    for row in rows:
        if row["employee_id"] == employee_id:
            base = _to_list_item(row, today)
            return EmployeeDetail(
                **base.model_dump(),
                first_name=row["first_name"],
                middle_name=row["middle_name"],
                last_name=row["last_name"],
                short_name=row["short_name"],
                phone=row["phone"],
                date_of_birth=row["date_of_birth"],
                gender=row["gender"],
                division=row["division"],
                reporting_manager_id=row["reporting_manager_id"],
                date_of_leaving=row["date_of_leaving"],
                fathers_name=row["fathers_name"],
                mothers_name=row["mothers_name"],
                marital_status=row["marital_status"],
                spouse_name=row["spouse_name"],
                alternate_phone=row["alternate_phone"],
                pan_no=row["pan_no"],
                aadhaar_no=row["aadhaar_no"],
            )
    raise HTTPException(404, "Employee not found")

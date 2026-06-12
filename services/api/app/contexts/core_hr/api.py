from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.contexts.core_hr.create import (
    DirectoryMeta,
    EmployeeCreate,
    create_employee,
    fetch_meta,
)
from app.contexts.core_hr.schemas import (
    DirectoryStats,
    EmployeeDetail,
    EmployeeListItem,
    EmployeeListOut,
)
from app.contexts.core_hr.service import derive_status, fetch_directory, full_name, tenure_label
from app.contexts.core_hr.update import EmployeeUpdate, update_employee
from app.contexts.identity.principal import (
    ROLE_HR_ADMIN,
    Principal,
    get_current_principal,
    require_roles,
)
from app.core.db import get_session

router = APIRouter(prefix="/employees", tags=["employees"])


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
    principal: Annotated[Principal, Depends(get_current_principal)],
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


@router.get("/meta", response_model=DirectoryMeta)
async def directory_meta(
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> DirectoryMeta:
    return await fetch_meta(session)


@router.post("", response_model=EmployeeDetail, status_code=201)
async def add_employee(
    payload: EmployeeCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> EmployeeDetail:
    try:
        employee_id = await create_employee(session, payload)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return await get_employee(employee_id, session, principal)


@router.patch("/{employee_id}", response_model=EmployeeDetail)
async def edit_employee(
    employee_id: int,
    payload: EmployeeUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, require_roles(ROLE_HR_ADMIN)],
) -> EmployeeDetail:
    try:
        await update_employee(session, employee_id, payload)
    except LookupError as exc:
        raise HTTPException(404, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    return await get_employee(employee_id, session, principal)


@router.get("/{employee_id}", response_model=EmployeeDetail)
async def get_employee(
    employee_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> EmployeeDetail:
    # PII (personal/statutory fields) is visible only to HR or the person
    # themselves — directory users see job + contact info only.
    pii_visible = principal.is_hr or principal.employee_id == employee_id
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
                gender=row["gender"],
                division=row["division"],
                circle_id=row["circle_id"],
                reporting_manager_id=row["reporting_manager_id"],
                date_of_leaving=row["date_of_leaving"],
                date_of_birth=row["date_of_birth"] if pii_visible else None,
                fathers_name=row["fathers_name"] if pii_visible else None,
                mothers_name=row["mothers_name"] if pii_visible else None,
                marital_status=row["marital_status"] if pii_visible else None,
                spouse_name=row["spouse_name"] if pii_visible else None,
                alternate_phone=row["alternate_phone"] if pii_visible else None,
                pan_no=row["pan_no"] if pii_visible else None,
                aadhaar_no=row["aadhaar_no"] if pii_visible else None,
                pii_visible=pii_visible,
            )
    raise HTTPException(404, "Employee not found")

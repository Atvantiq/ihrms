from datetime import date

from pydantic import BaseModel

EmploymentStatus = str  # Active | Probation | Joining | Notice | Inactive


class EmployeeListItem(BaseModel):
    employee_id: int
    employee_code: str
    full_name: str
    email: str
    designation: str | None = None
    department: str | None = None
    branch: str | None = None
    manager_name: str | None = None
    date_of_joining: date | None = None
    tenure: str
    status: EmploymentStatus


class EmployeeDetail(EmployeeListItem):
    first_name: str
    middle_name: str | None = None
    last_name: str | None = None
    short_name: str | None = None
    phone: str | None = None
    date_of_birth: date | None = None
    gender: str | None = None
    division: str | None = None
    reporting_manager_id: int | None = None
    date_of_leaving: date | None = None
    fathers_name: str | None = None
    mothers_name: str | None = None
    marital_status: str | None = None
    spouse_name: str | None = None
    alternate_phone: str | None = None
    pan_no: str | None = None
    aadhaar_no: str | None = None


class DirectoryStats(BaseModel):
    total: int
    active: int
    probation: int
    joining: int
    notice: int
    inactive: int
    departments: list[str]


class EmployeeListOut(BaseModel):
    items: list[EmployeeListItem]
    total_matches: int
    stats: DirectoryStats

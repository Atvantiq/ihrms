from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class LeaveTypeOut(BaseModel):
    id: str
    key: str
    code: str
    label: str
    color: str
    description: str | None = None
    is_paid: bool
    accrual_method: str
    annual_entitlement: Decimal
    min_advance_notice_days: int
    max_consecutive_days: int | None = None
    half_day_allowed: bool
    requires_doc: bool
    show_in_ess: bool


class BalanceOut(BaseModel):
    leave_type_id: str
    code: str
    label: str
    color: str
    entitled: Decimal
    accrued: Decimal
    carried_forward: Decimal
    used: Decimal
    pending: Decimal
    available: Decimal


class LeaveApply(BaseModel):
    leave_type_id: str
    start_date: date
    end_date: date
    half_day: bool = False
    reason: str | None = Field(default=None, max_length=500)
    # HR-only: apply on behalf of another employee
    employee_id: int | None = None


class LeaveRequestOut(BaseModel):
    id: str
    employee_id: int
    employee_name: str
    leave_type_id: str
    leave_code: str
    leave_label: str
    color: str
    start_date: date
    end_date: date
    half_day: bool
    days: Decimal
    reason: str | None = None
    status: str
    approver_id: int | None = None
    approver_name: str | None = None
    decision_note: str | None = None
    decided_at: str | None = None
    can_decide: bool = False
    can_cancel: bool = False


class Decision(BaseModel):
    note: str | None = Field(default=None, max_length=500)

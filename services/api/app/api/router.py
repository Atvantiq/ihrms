from fastapi import APIRouter

from app.api.health import router as health_router
from app.contexts.advances.api import router as advances_router
from app.contexts.assets.api import router as assets_router
from app.contexts.attendance.api import router as attendance_router
from app.contexts.audit.api import router as audit_router
from app.contexts.comp_off.api import router as comp_off_router
from app.contexts.consent.api import router as consent_router
from app.contexts.control_plane.api import router as control_plane_router
from app.contexts.core_hr.api import router as employees_router
from app.contexts.dashboard.api import router as dashboard_router
from app.contexts.exit_fnf.api import router as exit_router
from app.contexts.feedback.api import router as feedback_router
from app.contexts.identity.api import router as me_router
from app.contexts.identity.dev_login import router as dev_login_router
from app.contexts.leave.api import router as leave_router
from app.contexts.leave.holidays import router as holidays_router
from app.contexts.org.api import router as org_router
from app.contexts.overtime.api import router as overtime_router
from app.contexts.payroll.api import router as payroll_router
from app.contexts.performance.api import router as performance_router
from app.contexts.pulse.api import router as pulse_router
from app.contexts.recruitment.api import router as recruitment_router
from app.contexts.reports.api import router as reports_router
from app.contexts.shifts.api import router as shifts_router
from app.contexts.tasks.api import router as tasks_router
from app.contexts.tax.api import router as tax_router
from app.contexts.timesheet.api import router as timesheet_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(pulse_router)
api_router.include_router(tasks_router)
api_router.include_router(assets_router)
api_router.include_router(advances_router)
api_router.include_router(consent_router)
api_router.include_router(tax_router)
api_router.include_router(shifts_router)
api_router.include_router(overtime_router)
api_router.include_router(comp_off_router)
api_router.include_router(feedback_router)
api_router.include_router(employees_router)
api_router.include_router(me_router)
api_router.include_router(org_router)
api_router.include_router(leave_router)
api_router.include_router(holidays_router)
api_router.include_router(payroll_router)
api_router.include_router(attendance_router)
api_router.include_router(timesheet_router)
api_router.include_router(recruitment_router)
api_router.include_router(performance_router)
api_router.include_router(reports_router)
api_router.include_router(control_plane_router)
api_router.include_router(exit_router)
api_router.include_router(audit_router)
api_router.include_router(dev_login_router)

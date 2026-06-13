from fastapi import APIRouter

from app.api.health import router as health_router
from app.contexts.audit.api import router as audit_router
from app.contexts.core_hr.api import router as employees_router
from app.contexts.dashboard.api import router as dashboard_router
from app.contexts.identity.api import router as me_router
from app.contexts.identity.dev_login import router as dev_login_router
from app.contexts.leave.api import router as leave_router
from app.contexts.leave.holidays import router as holidays_router
from app.contexts.org.api import router as org_router
from app.contexts.payroll.api import router as payroll_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(dashboard_router)
api_router.include_router(employees_router)
api_router.include_router(me_router)
api_router.include_router(org_router)
api_router.include_router(leave_router)
api_router.include_router(holidays_router)
api_router.include_router(payroll_router)
api_router.include_router(audit_router)
api_router.include_router(dev_login_router)

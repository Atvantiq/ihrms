from fastapi import APIRouter

from app.api.health import router as health_router
from app.contexts.core_hr.api import router as employees_router
from app.contexts.identity.api import router as me_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health_router)
api_router.include_router(employees_router)
api_router.include_router(me_router)

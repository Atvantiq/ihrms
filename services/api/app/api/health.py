"""Health probes.

- /health  — liveness: process is up. Cheap, no dependencies. For k8s livenessProbe.
- /ready   — readiness: can serve traffic (DB reachable). For k8s readinessProbe
             and load-balancer gating.
- /health/info — legacy detailed check (DB + visible employee count).
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session

router = APIRouter(tags=["health"])


class Liveness(BaseModel):
    status: str


class Readiness(BaseModel):
    status: str
    database: str


class HealthInfo(BaseModel):
    status: str
    database: str
    employees_visible: int | None = None


@router.get("/health", response_model=Liveness)
async def health() -> Liveness:
    return Liveness(status="ok")


@router.get("/ready", response_model=Readiness)
async def ready(
    session: Annotated[AsyncSession, Depends(get_session)],
    response: Response,
) -> Readiness:
    try:
        await session.execute(text("select 1"))
        return Readiness(status="ready", database="up")
    except Exception:
        response.status_code = 503
        return Readiness(status="not_ready", database="down")


@router.get("/health/info", response_model=HealthInfo)
async def health_info(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> HealthInfo:
    try:
        result = await session.execute(text("select count(*) from public.employees"))
        count: int = result.scalar_one()
        return HealthInfo(status="ok", database="up", employees_visible=count)
    except Exception:
        return HealthInfo(status="degraded", database="down")

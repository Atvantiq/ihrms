from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session

router = APIRouter(tags=["health"])


class HealthOut(BaseModel):
    status: str
    database: str
    employees_visible: int | None = None


@router.get("/health", response_model=HealthOut)
async def health(session: Annotated[AsyncSession, Depends(get_session)]) -> HealthOut:
    try:
        result = await session.execute(text("select count(*) from public.employees"))
        count: int = result.scalar_one()
        return HealthOut(status="ok", database="up", employees_visible=count)
    except Exception:
        return HealthOut(status="degraded", database="down")

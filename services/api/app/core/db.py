from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    """All iHRMS models live in the `ihrms` schema — never in `public`.

    The `public` schema belongs to ONAQT (live production app): read it via
    views/soft references only, never define or alter its tables here.
    """

    __table_args__ = {"schema": "ihrms"}


engine = create_async_engine(get_settings().sqlalchemy_async_url, pool_size=5, max_overflow=5)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a session with the tenant GUC set, so RLS (migration 0006)
    scopes every ihrms.* query to this tenant. Set on each checkout because
    pooled connections are reused. Single-tenant today; when multi-tenant,
    derive the tenant from the authenticated principal instead of settings.
    """
    async with SessionLocal() as session:
        await session.execute(
            text("select set_config('app.tenant_id', :t, false)"),
            {"t": get_settings().tenant_id},
        )
        yield session

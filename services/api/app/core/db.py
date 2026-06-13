import re
from collections.abc import AsyncIterator

from sqlalchemy import event
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


# Tenant isolation: set app.tenant_id at the START of EVERY transaction so the
# RLS policies (migration 0006) scope every query — including reads and audit
# inserts that run after an intermediate commit. Transaction-local (is_local
# = true) so it never leaks across pooled connections. Single-tenant today;
# when multi-tenant, source the tenant from request context instead of config.
_TENANT_ID = get_settings().tenant_id
if not re.fullmatch(r"[A-Za-z0-9_-]+", _TENANT_ID):
    raise ValueError(f"Unsafe tenant_id: {_TENANT_ID!r}")


@event.listens_for(engine.sync_engine, "begin")
def _set_tenant_guc(conn: object) -> None:
    conn.exec_driver_sql(  # type: ignore[attr-defined]
        f"select set_config('app.tenant_id', '{_TENANT_ID}', true)"
    )


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session

import re
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


# Tenant isolation: each request is exactly ONE transaction (services never
# commit; handlers read-then-commit once), so a transaction-local
# `set app.tenant_id` at session start scopes every query under the RLS
# policies (migration 0006) for the whole request. SET LOCAL works through
# the Supabase pooler (unlike connection startup settings) and is cleared at
# transaction end, so it can never leak across pooled connections.
# Single-tenant today; when multi-tenant, source the tenant from request
# context here instead of config.
_TENANT_ID = get_settings().tenant_id
if not re.fullmatch(r"[A-Za-z0-9_-]+", _TENANT_ID):
    raise ValueError(f"Unsafe tenant_id: {_TENANT_ID!r}")

engine = create_async_engine(get_settings().sqlalchemy_async_url, pool_size=5, max_overflow=5)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        await session.execute(
            text("select set_config('app.tenant_id', :t, true)"),
            {"t": _TENANT_ID},
        )
        yield session

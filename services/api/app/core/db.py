from collections.abc import AsyncIterator

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
    async with SessionLocal() as session:
        yield session

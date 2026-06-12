"""Alembic environment for iHRMS.

CRITICAL SAFETY RULES (blueprint doc 24):
- This database is SHARED with the live ONAQT app. Its tables live in `public`.
- iHRMS migrations only ever create/alter objects in the `ihrms` schema.
- The Alembic version table is `ihrms.alembic_version` — fully separate from
  ONAQT's own `public.alembic_version`. The two histories never collide.
"""

import os

from alembic import context
from sqlalchemy import create_engine, pool, text

config = context.config

DATABASE_URL = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")

target_metadata = None  # migrations are hand-written SQL for full control


def run_migrations_online() -> None:
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL env var is required")
    engine = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        # Schema must exist before Alembic writes its version table into it.
        connection.execute(text("create schema if not exists ihrms"))
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version",
            version_table_schema="ihrms",
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()

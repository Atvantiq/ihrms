"""Integration test harness — runs the real app against an ephemeral Postgres.

Set TEST_DATABASE_URL to a throwaway database (CI uses a service container;
locally a temp cluster). When unset, integration tests are skipped so the
pure-unit suite still runs anywhere.

Setup: rebuild a minimal ONAQT `public` schema + the `ihrms` schema via real
migrations, seed two employees and their user_account rows, then exercise the
app through an in-process ASGI client with real (test-signed) JWTs.
"""

import os
import pathlib
import subprocess
import sys
import time
from collections.abc import AsyncIterator

import pytest

TEST_DB = os.environ.get("TEST_DATABASE_URL")
JWT_SECRET = "integration-test-secret"

# Point the app at the test DB BEFORE it is imported anywhere.
if TEST_DB:
    os.environ["DATABASE_URL"] = TEST_DB
    os.environ["TENANT_ID"] = "atvantiq"
    os.environ["SUPABASE_JWT_SECRET"] = JWT_SECRET
    os.environ["AUTH_DISABLED"] = "false"
    os.environ["DEV_LOGIN_ENABLED"] = "false"

HERE = pathlib.Path(__file__).parent
API_ROOT = HERE.parent.parent

ADMIN_AUTH_ID = "00000000-0000-0000-0000-000000000001"
ADMIN_EMP_ID = 100000000001
EMP_AUTH_ID = "00000000-0000-0000-0000-000000000002"
EMP_EMP_ID = 100000000002

# When no test database is configured, don't collect the integration tests at
# all (they need a real Postgres). The unit suite still runs anywhere.
if not TEST_DB:
    collect_ignore_glob = ["test_*.py"]


def _mint(sub: str, email: str) -> str:
    from jose import jwt

    return jwt.encode(
        {"sub": sub, "email": email, "aud": "authenticated", "exp": int(time.time()) + 3600},
        JWT_SECRET,
        algorithm="HS256",
    )


@pytest.fixture(scope="session", autouse=True)
def _db() -> None:
    import psycopg2

    conn = psycopg2.connect(TEST_DB)
    conn.autocommit = True
    cur = conn.cursor()

    # clean slate
    cur.execute("drop schema if exists ihrms cascade")
    cur.execute("drop table if exists auth.users cascade")
    for t in ("addresses", "employee_details", "job_details", "employees", "global_ids"):
        cur.execute(f"drop table if exists public.{t} cascade")

    # minimal ONAQT public schema
    cur.execute((HERE / "fixtures_public.sql").read_text())
    conn.close()

    # real iHRMS migrations
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=API_ROOT,
        env={**os.environ, "DATABASE_URL": TEST_DB},
        check=True,
    )

    # seed two employees + linked accounts (superuser bypasses RLS for seeding)
    conn = psycopg2.connect(TEST_DB)
    conn.autocommit = True
    cur = conn.cursor()
    for gid in (ADMIN_EMP_ID, EMP_EMP_ID):
        cur.execute("insert into public.global_ids (id) values (%s)", (gid,))
    cur.execute(
        """insert into public.employees
           (employee_id, employee_code, email, first_name, last_name, short_name,
            phone, gender, is_active)
           values (%s,'ADM-001','admin@test.local','Ada','Admin','Ada','+910000000001','female',1),
                  (%s,'EMP-001','emp@test.local','Eli','Employee','Eli','+910000000002','male',1)""",
        (ADMIN_EMP_ID, EMP_EMP_ID),
    )
    cur.execute(
        """insert into public.job_details
           (employee_id, designation, circle_id, branch, department, division,
            reporting_manager, date_of_joining)
           values (%s,'CHRO',1,'HQ','People','Central',null,'2020-01-01'),
                  (%s,'Engineer',1,'HQ','Engineering','Central',%s,'2026-06-01')""",
        (ADMIN_EMP_ID, EMP_EMP_ID, ADMIN_EMP_ID),
    )
    cur.execute(
        """insert into ihrms.user_account (auth_user_id, employee_id, roles, persona)
           values (%s,%s,'{employee,hr_admin}','hr'),
                  (%s,%s,'{employee}','employee')""",
        (ADMIN_AUTH_ID, ADMIN_EMP_ID, EMP_AUTH_ID, EMP_EMP_ID),
    )
    conn.close()


@pytest.fixture
async def client() -> AsyncIterator[object]:
    from httpx import ASGITransport, AsyncClient

    from app.core.db import engine
    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    # pytest-asyncio uses a fresh event loop per test; asyncpg connections are
    # bound to the loop they were created on, so drop the pool after each test
    # to avoid reusing a connection from a now-closed loop.
    await engine.dispose()


@pytest.fixture
def hr_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_mint(ADMIN_AUTH_ID, 'admin@test.local')}"}


@pytest.fixture
def emp_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {_mint(EMP_AUTH_ID, 'emp@test.local')}"}

"""Integration tests for overtime: log → approve → paid in payroll run."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_log_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/overtime", json={})).status_code == 401


async def test_log_appears_in_tasks_and_self(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    logged = await client.post(
        "/api/v1/overtime", headers=emp_headers,
        json={"ot_date": "2026-06-07", "hours": "5", "reason": "Release night"},
    )
    assert logged.status_code == 201, logged.text
    ot = logged.json()
    assert ot["status"] == "pending"

    # duplicate for the same day rejected
    dup = await client.post(
        "/api/v1/overtime", headers=emp_headers,
        json={"ot_date": "2026-06-07", "hours": "2", "reason": "again"},
    )
    assert dup.status_code == 409

    # employee cannot approve their own
    assert (
        await client.post(f"/api/v1/overtime/{ot['id']}/approve", headers=emp_headers)
    ).status_code == 403

    # shows as an overtime task for HR
    tasks = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    assert any(t["task_type"] == "overtime" and t["ref_id"] == ot["id"] for t in tasks)


async def test_approved_overtime_paid_in_run(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1200000, "effective_from": "2026-01-01", "tax_regime": "new"},
    )
    ot = (
        await client.post(
            "/api/v1/overtime", headers=emp_headers,
            json={"ot_date": "2026-06-05", "hours": "4", "rate_multiplier": "2.0",
                  "reason": "Weekend deploy"},
        )
    ).json()
    appr = await client.post(f"/api/v1/overtime/{ot['id']}/approve", headers=hr_headers)
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"

    run = await client.post(
        "/api/v1/payroll/runs", headers=hr_headers,
        json={"period_year": 2027, "period_month": 10, "working_days": 30},
    )
    assert run.status_code == 201, run.text
    register = (
        await client.get(f"/api/v1/payroll/runs/{run.json()['id']}/register", headers=hr_headers)
    ).json()
    slip = next(p for p in register if p["employee_id"] == EMP_ID)
    assert "overtime" in slip["earnings"]
    assert Decimal(slip["earnings"]["overtime"]) > 0

    # the OT is now marked paid
    mine = (await client.get("/api/v1/overtime?scope=mine", headers=emp_headers)).json()
    assert next(o for o in mine if o["id"] == ot["id"])["status"] == "paid"

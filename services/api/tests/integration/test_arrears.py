"""Integration test: back-dated salary change → arrear → paid in next run."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_backdated_raise_creates_and_pays_arrear(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    # baseline structure effective at the start of the year
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1200000, "effective_from": "2026-01-01", "tax_regime": "new"},
    )

    # raise it, back-dated two months -> arrears for those months
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1800000, "effective_from": "2026-04-01", "tax_regime": "new"},
    )

    arrears = (await client.get("/api/v1/payroll/arrears", headers=hr_headers)).json()
    mine = next(a for a in arrears if a["employee_id"] == EMP_ID and a["status"] == "pending")
    assert mine["months"] >= 1
    assert Decimal(mine["amount"]) > 0  # a raise owes a positive arrear

    # run payroll -> arrears appear on the payslip and are marked paid
    run = await client.post(
        "/api/v1/payroll/runs", headers=hr_headers,
        json={"period_year": 2027, "period_month": 9, "working_days": 30},
    )
    assert run.status_code == 201, run.text
    register = (
        await client.get(f"/api/v1/payroll/runs/{run.json()['id']}/register", headers=hr_headers)
    ).json()
    slip = next(p for p in register if p["employee_id"] == EMP_ID)
    assert "arrears" in slip["earnings"]
    assert Decimal(slip["earnings"]["arrears"]) == Decimal(mine["amount"])

    # the arrear is now settled
    after = (await client.get("/api/v1/payroll/arrears", headers=hr_headers)).json()
    settled = next(a for a in after if a["id"] == mine["id"])
    assert settled["status"] == "paid"


async def test_employee_sees_only_own_arrears(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    # employee querying another employee's id still only gets their own scope
    mine = (await client.get("/api/v1/payroll/arrears", headers=emp_headers)).json()
    assert all(a["employee_id"] == EMP_ID for a in mine)

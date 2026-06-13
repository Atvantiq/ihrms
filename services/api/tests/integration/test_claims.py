"""Integration tests for expense claims + payroll reimbursement."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/claims", json={})).status_code == 401


async def test_file_appears_in_tasks(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    filed = await client.post(
        "/api/v1/claims", headers=emp_headers,
        json={"category": "travel", "description": "Client visit cab",
              "claim_date": "2026-06-05", "amount": "1200", "receipt_ref": "cab.pdf"},
    )
    assert filed.status_code == 201, filed.text
    c = filed.json()
    assert c["status"] == "pending"
    self_appr = await client.post(f"/api/v1/claims/{c['id']}/approve", headers=emp_headers)
    assert self_appr.status_code == 403
    tasks = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    assert any(t["task_type"] == "claim" and t["ref_id"] == c["id"] for t in tasks)


async def test_approved_claim_reimbursed_in_run(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1200000, "effective_from": "2026-01-01", "tax_regime": "new"},
    )
    c = (
        await client.post(
            "/api/v1/claims", headers=emp_headers,
            json={"category": "food", "description": "Team lunch", "claim_date": "2026-06-04",
                  "amount": "3500"},
        )
    ).json()
    appr = await client.post(f"/api/v1/claims/{c['id']}/approve", headers=hr_headers)
    assert appr.status_code == 200 and appr.json()["status"] == "approved"

    run = await client.post(
        "/api/v1/payroll/runs", headers=hr_headers,
        json={"period_year": 2027, "period_month": 11, "working_days": 30},
    )
    assert run.status_code == 201, run.text
    register = (
        await client.get(f"/api/v1/payroll/runs/{run.json()['id']}/register", headers=hr_headers)
    ).json()
    slip = next(p for p in register if p["employee_id"] == EMP_ID)
    assert "reimbursements" in slip["earnings"]
    assert Decimal(slip["earnings"]["reimbursements"]) >= 3500

    mine = (await client.get("/api/v1/claims?scope=mine", headers=emp_headers)).json()
    assert next(x for x in mine if x["id"] == c["id"])["status"] == "paid"

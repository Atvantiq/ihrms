"""Integration tests for advances/loans + payroll EMI recovery."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002  # seeded "Eli Employee"


async def test_non_hr_cannot_issue(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/advances", headers=emp_headers,
        json={"employee_id": EMP_ID, "principal_amount": "10000", "emi_amount": "1000"},
    )
    assert r.status_code == 403


async def test_issue_and_employee_sees_own(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    issued = await client.post(
        "/api/v1/advances", headers=hr_headers,
        json={"employee_id": EMP_ID, "kind": "advance",
              "principal_amount": "30000", "emi_amount": "10000", "reason": "Relocation"},
    )
    assert issued.status_code == 201, issued.text
    body = issued.json()
    assert body["outstanding"] == "30000.00"
    assert body["recovered"] == "0.00"

    mine = (await client.get(f"/api/v1/advances/employee/{EMP_ID}", headers=emp_headers)).json()
    assert any(a["id"] == body["id"] for a in mine)
    # can't peek at someone else's
    forbidden = await client.get("/api/v1/advances/employee/100000000001", headers=emp_headers)
    assert forbidden.status_code == 403


async def test_emi_cannot_exceed_principal(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/advances", headers=hr_headers,
        json={"employee_id": EMP_ID, "principal_amount": "5000", "emi_amount": "9000"},
    )
    assert r.status_code == 422


async def test_payroll_recovers_emi(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    # clean slate — cancel any active advances left by earlier tests so payroll
    # (which recovers the oldest active advance) acts on the one we issue here
    existing = (await client.get("/api/v1/advances", headers=hr_headers)).json()
    for a in existing:
        if a["employee_id"] == EMP_ID and a["status"] == "active":
            await client.post(f"/api/v1/advances/{a['id']}/cancel", headers=hr_headers)

    # give the employee a salary structure so payroll has someone to pay
    struct = await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1200000, "effective_from": "2026-01-01", "tax_regime": "new"},
    )
    assert struct.status_code == 200, struct.text

    # issue a loan with a 10k EMI on a 25k principal
    adv = (
        await client.post(
            "/api/v1/advances", headers=hr_headers,
            json={"employee_id": EMP_ID, "kind": "loan",
                  "principal_amount": "25000", "emi_amount": "10000"},
        )
    ).json()

    # run payroll for a fresh month
    run = await client.post(
        "/api/v1/payroll/runs", headers=hr_headers,
        json={"period_year": 2026, "period_month": 11, "working_days": 30},
    )
    assert run.status_code == 201, run.text

    # outstanding dropped by the EMI
    after = (await client.get("/api/v1/advances", headers=hr_headers)).json()
    mine = next(a for a in after if a["id"] == adv["id"])
    assert mine["outstanding"] == "15000.00"
    assert mine["recovered"] == "10000.00"

    # the payslip register shows the loan_recovery deduction
    register = (
        await client.get(f"/api/v1/payroll/runs/{run.json()['id']}/register", headers=hr_headers)
    ).json()
    slip = next(p for p in register if p["employee_id"] == EMP_ID)
    assert "loan_recovery" in slip["deductions"]
    assert slip["deductions"]["loan_recovery"] == "10000"

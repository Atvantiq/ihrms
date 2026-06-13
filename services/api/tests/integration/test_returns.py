"""Integration tests for statutory IDs + return-file downloads."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_non_hr_cannot_set_statutory(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.put(
        f"/api/v1/payroll/statutory/{EMP_ID}", headers=emp_headers, json={"uan": "100200300400"}
    )
    assert r.status_code == 403


async def test_uan_validated(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    bad = await client.put(
        f"/api/v1/payroll/statutory/{EMP_ID}", headers=hr_headers, json={"uan": "123"}
    )
    assert bad.status_code == 422


async def test_ecr_download_contains_member(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    # set statutory IDs + a structure, then run payroll
    await client.put(
        f"/api/v1/payroll/statutory/{EMP_ID}", headers=hr_headers,
        json={"uan": "100200300400", "esic_ip": "3100000001", "pt_state": "KA"},
    )
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1200000, "effective_from": "2026-01-01", "tax_regime": "new"},
    )
    run = await client.post(
        "/api/v1/payroll/runs", headers=hr_headers,
        json={"period_year": 2027, "period_month": 5, "working_days": 30},
    )
    assert run.status_code == 201, run.text
    run_id = run.json()["id"]

    ecr = await client.get(f"/api/v1/payroll/runs/{run_id}/ecr", headers=hr_headers)
    assert ecr.status_code == 200
    assert ecr.headers["content-type"].startswith("text/plain")
    assert "100200300400#~#" in ecr.text  # the UAN leads the member line

    pt = await client.get(f"/api/v1/payroll/runs/{run_id}/pt", headers=hr_headers)
    assert pt.status_code == 200
    assert pt.text.startswith("State,EmployeeCode")

"""Integration tests for effective-dated employee history."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_history_requires_auth(client: AsyncClient) -> None:
    assert (await client.get(f"/api/v1/employees/{EMP_ID}/history")).status_code == 401


async def test_job_change_is_logged(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    before = (await client.get(f"/api/v1/employees/{EMP_ID}/history", headers=hr_headers)).json()

    # promote: change designation
    r = await client.patch(
        f"/api/v1/employees/{EMP_ID}", headers=hr_headers,
        json={"designation": "Staff Engineer"},
    )
    assert r.status_code == 200, r.text

    after = (await client.get(f"/api/v1/employees/{EMP_ID}/history", headers=hr_headers)).json()
    assert len(after) == len(before) + 1
    entry = after[0]
    assert entry["category"] == "job"
    assert entry["field"] == "designation"
    assert entry["new_value"] == "Staff Engineer"
    assert entry["changed_by"] == 100000000001  # the HR admin


async def test_unchanged_value_is_not_logged(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    # set a known designation, then "change" it to the same value
    await client.patch(
        f"/api/v1/employees/{EMP_ID}", headers=hr_headers, json={"designation": "Lead Engineer"},
    )
    mid = (await client.get(f"/api/v1/employees/{EMP_ID}/history", headers=hr_headers)).json()
    await client.patch(
        f"/api/v1/employees/{EMP_ID}", headers=hr_headers, json={"designation": "Lead Engineer"},
    )
    after = (await client.get(f"/api/v1/employees/{EMP_ID}/history", headers=hr_headers)).json()
    assert len(after) == len(mid)  # no new row for an unchanged value


async def test_compensation_change_is_logged(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    await client.put(
        f"/api/v1/payroll/structures/{EMP_ID}", headers=hr_headers,
        json={"ctc_annual": 1800000, "effective_from": "2026-04-01", "tax_regime": "new"},
    )
    hist = (await client.get(f"/api/v1/employees/{EMP_ID}/history", headers=hr_headers)).json()
    comp = next((h for h in hist if h["category"] == "compensation"), None)
    assert comp is not None
    assert comp["field"] == "ctc_annual"
    assert Decimal(comp["new_value"]) == Decimal("1800000")


async def test_employee_cannot_see_others_history(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.get("/api/v1/employees/100000000001/history", headers=emp_headers)
    assert r.status_code == 403

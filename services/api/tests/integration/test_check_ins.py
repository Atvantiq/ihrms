"""Integration tests for check-ins."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002  # reports to ADMIN (100000000001)


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/check-ins", json={})).status_code == 401


async def test_log_and_see_own(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/check-ins", headers=emp_headers,
        json={"highlights": "Shipped the payroll fix", "challenges": "Flaky CI", "mood": 4},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["mood_label"] == "good"

    mine = (await client.get("/api/v1/check-ins/mine", headers=emp_headers)).json()
    assert any(c["id"] == body["id"] for c in mine)


async def test_manager_sees_report_check_in(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    logged = await client.post(
        "/api/v1/check-ins", headers=emp_headers,
        json={"highlights": "Closed three tickets", "mood": 5},
    )
    cid = logged.json()["id"]
    # ADMIN is HR and the reporting manager → sees it on the team feed
    team = (await client.get("/api/v1/check-ins/team", headers=hr_headers)).json()
    assert any(c["id"] == cid and c["employee_id"] == EMP_ID for c in team)


async def test_invalid_mood_rejected(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/check-ins", headers=emp_headers,
        json={"highlights": "x", "mood": 9},
    )
    assert r.status_code == 422

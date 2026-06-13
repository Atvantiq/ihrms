"""Integration tests for comp-off: earn → approve → avail."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_earn_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/comp-off", json={})).status_code == 401


async def test_earn_approve_avail_lifecycle(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    earned = await client.post(
        "/api/v1/comp-off", headers=emp_headers,
        json={"earned_date": "2026-06-06", "reason": "Worked Saturday release"},
    )
    assert earned.status_code == 201, earned.text
    co = earned.json()
    assert co["status"] == "pending"

    # duplicate for the same earned day rejected
    dup = await client.post(
        "/api/v1/comp-off", headers=emp_headers,
        json={"earned_date": "2026-06-06", "reason": "again"},
    )
    assert dup.status_code == 409

    # employee cannot approve their own
    assert (
        await client.post(f"/api/v1/comp-off/{co['id']}/approve", headers=emp_headers)
    ).status_code == 403

    # appears as a comp-off task for HR
    tasks = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    assert any(t["task_type"] == "comp_off" and t["ref_id"] == co["id"] for t in tasks)

    # HR approves -> gets an expiry, shows as available
    appr = await client.post(f"/api/v1/comp-off/{co['id']}/approve", headers=hr_headers)
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"
    assert appr.json()["expiry_date"] == "2026-09-04"  # 90 days after 2026-06-06

    avail = (await client.get("/api/v1/comp-off?scope=available", headers=emp_headers)).json()
    assert any(c["id"] == co["id"] for c in avail)

    # avail it as a day off
    used = await client.post(
        f"/api/v1/comp-off/{co['id']}/avail", headers=emp_headers,
        json={"avail_date": "2026-06-20"},
    )
    assert used.status_code == 200
    assert used.json()["status"] == "availed"
    assert used.json()["availed_on"] == "2026-06-20"

    # no longer available
    avail2 = (await client.get("/api/v1/comp-off?scope=available", headers=emp_headers)).json()
    assert not any(c["id"] == co["id"] for c in avail2)


async def test_cannot_avail_unapproved(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    co = (
        await client.post(
            "/api/v1/comp-off", headers=emp_headers,
            json={"earned_date": "2026-05-30", "reason": "Worked weekend"},
        )
    ).json()
    r = await client.post(
        f"/api/v1/comp-off/{co['id']}/avail", headers=emp_headers,
        json={"avail_date": "2026-06-20"},
    )
    assert r.status_code == 409

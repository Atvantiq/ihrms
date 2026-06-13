"""Integration test for the performance calibration view."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

ADMIN_ID = 100000000001  # seeded HR admin (also the dev principal)


async def test_calibration_flow(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    cyc = await client.post(
        "/api/v1/performance/cycles", headers=hr_headers,
        json={"name": "FY26 Calibration", "period_year": 2026},
    )
    assert cyc.status_code == 201, cyc.text
    cycle_id = cyc.json()["id"]

    enrolled = await client.post(
        f"/api/v1/performance/cycles/{cycle_id}/enroll", headers=hr_headers
    )
    assert enrolled.status_code == 200, enrolled.text
    assert enrolled.json()["review_count"] >= 1

    # non-HR is blocked
    forbidden = await client.get(
        f"/api/v1/performance/cycles/{cycle_id}/calibration", headers=emp_headers
    )
    assert forbidden.status_code == 403

    # initial calibration: nothing rated yet
    cal = (await client.get(
        f"/api/v1/performance/cycles/{cycle_id}/calibration", headers=hr_headers
    )).json()
    assert cal["rated_count"] == 0
    assert cal["pending_count"] >= 1
    assert [b["rating"] for b in cal["buckets"]] == [5, 4, 3, 2, 1]
    assert all(b["actual_pct"] == "0.0" or b["actual_pct"] == "0" for b in cal["buckets"])

    # rate the admin's own review through self -> manager
    reviews = (await client.get(
        f"/api/v1/performance/cycles/{cycle_id}/reviews", headers=hr_headers
    )).json()
    mine = next(r for r in reviews if r["employee_id"] == ADMIN_ID)
    assert (await client.post(
        f"/api/v1/performance/reviews/{mine['id']}/self", headers=hr_headers,
        json={"self_rating": 4, "self_comment": "solid year"},
    )).status_code == 200
    assert (await client.post(
        f"/api/v1/performance/reviews/{mine['id']}/manager", headers=hr_headers,
        json={"manager_rating": 4, "potential": 3, "manager_comment": "exceeds"},
    )).status_code == 200

    cal2 = (await client.get(
        f"/api/v1/performance/cycles/{cycle_id}/calibration", headers=hr_headers
    )).json()
    assert cal2["rated_count"] == 1
    bucket4 = next(b for b in cal2["buckets"] if b["rating"] == 4)
    assert bucket4["count"] == 1
    assert bucket4["actual_pct"] == "100.0"
    # target for a 4 is 20% -> delta +80
    assert bucket4["delta_pct"] == "80.0"

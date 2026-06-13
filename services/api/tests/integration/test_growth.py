"""Integration tests for development plans + mentorship."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

ADMIN_ID = 100000000001
EMP_ID = 100000000002


async def test_plan_lifecycle_self(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    # employee creates their own plan (no employee_id -> self)
    created = await client.post(
        "/api/v1/growth/plans", headers=emp_headers,
        json={"focus_area": "Public speaking", "objective": "Lead 3 demos",
              "target_date": "2026-12-31"},
    )
    assert created.status_code == 201, created.text
    plan = created.json()
    assert plan["employee_id"] == EMP_ID and plan["status"] == "active"

    # add two actions, toggle one
    await client.post(f"/api/v1/growth/plans/{plan['id']}/actions", headers=emp_headers,
                      json={"action": "Join Toastmasters"})
    with_actions = (await client.post(
        f"/api/v1/growth/plans/{plan['id']}/actions", headers=emp_headers,
        json={"action": "Present at all-hands"},
    )).json()
    assert len(with_actions["actions"]) == 2
    first = with_actions["actions"][0]["id"]
    toggled = (await client.post(
        f"/api/v1/growth/plans/{plan['id']}/actions/{first}/toggle", headers=emp_headers
    )).json()
    assert next(a for a in toggled["actions"] if a["id"] == first)["status"] == "done"

    # mark achieved
    done = await client.patch(
        f"/api/v1/growth/plans/{plan['id']}", headers=emp_headers,
        json={"status": "achieved"},
    )
    assert done.json()["status"] == "achieved"

    # listing my plans returns it
    mine = (await client.get("/api/v1/growth/plans", headers=emp_headers)).json()
    assert any(p["id"] == plan["id"] for p in mine)


async def test_cannot_view_others_plans(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.get(f"/api/v1/growth/plans?employee_id={ADMIN_ID}", headers=emp_headers)
    assert r.status_code == 403


async def test_hr_creates_plan_for_employee(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    created = await client.post(
        "/api/v1/growth/plans", headers=hr_headers,
        json={"employee_id": EMP_ID, "focus_area": "Leadership",
              "objective": "Mentor a junior"},
    )
    assert created.status_code == 201
    assert created.json()["employee_id"] == EMP_ID


async def test_mentorship(client: AsyncClient, hr_headers: dict[str, str],
                          emp_headers: dict[str, str]) -> None:
    created = await client.post(
        "/api/v1/growth/mentorships", headers=hr_headers,
        json={"mentor_id": ADMIN_ID, "mentee_id": EMP_ID, "focus": "Career growth"},
    )
    assert created.status_code == 201, created.text
    m = created.json()
    assert m["mentor_id"] == ADMIN_ID and m["status"] == "active"

    # self-pairing rejected
    bad = await client.post(
        "/api/v1/growth/mentorships", headers=hr_headers,
        json={"mentor_id": ADMIN_ID, "mentee_id": ADMIN_ID},
    )
    assert bad.status_code == 422

    # non-HR cannot create
    forbidden = await client.post(
        "/api/v1/growth/mentorships", headers=emp_headers,
        json={"mentor_id": ADMIN_ID, "mentee_id": EMP_ID},
    )
    assert forbidden.status_code == 403

    # the mentee sees the pairing
    mine = (await client.get("/api/v1/growth/mentorships", headers=emp_headers)).json()
    assert any(x["id"] == m["id"] for x in mine)

    # close it
    closed = await client.post(
        f"/api/v1/growth/mentorships/{m['id']}/close", headers=hr_headers
    )
    assert closed.json()["status"] == "closed"

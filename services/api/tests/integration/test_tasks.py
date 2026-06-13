"""Integration tests for the unified task inbox."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_tasks_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/tasks")).status_code == 401


async def test_plain_employee_has_no_tasks(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    # the seeded employee manages no one -> nothing to approve
    tasks = (await client.get("/api/v1/tasks", headers=emp_headers)).json()
    assert tasks == []


async def test_leave_request_appears_and_clears_on_approval(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    types = (await client.get("/api/v1/leave/types", headers=emp_headers)).json()
    cl = next(t for t in types if t["code"] == "CL")
    req = (
        await client.post(
            "/api/v1/leave/requests",
            headers=emp_headers,
            json={"leave_type_id": cl["id"], "start_date": "2026-09-07", "end_date": "2026-09-08"},
        )
    ).json()

    # the new request shows up as an itemised leave task for HR
    tasks = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    mine = next((t for t in tasks if t["task_type"] == "leave" and t["ref_id"] == req["id"]), None)
    assert mine is not None
    assert mine["badge"] == "CL"
    assert mine["can_reject"] is True

    # approving it through the leave endpoint removes it from the inbox
    appr = await client.post(
        f"/api/v1/leave/requests/{req['id']}/approve", headers=hr_headers, json={"note": "ok"}
    )
    assert appr.status_code == 200
    after = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    assert not any(t["ref_id"] == req["id"] for t in after)

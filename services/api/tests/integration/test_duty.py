"""Integration tests for OOD/WFH duty requests."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/duty", json={})).status_code == 401


async def test_request_approve_marks_attendance(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    req = await client.post(
        "/api/v1/duty", headers=emp_headers,
        json={"duty_type": "wfh", "start_date": "2026-07-06", "end_date": "2026-07-08",
              "reason": "Remote sprint"},
    )
    assert req.status_code == 201, req.text
    duty = req.json()

    # employee can't approve own
    self_appr = await client.post(f"/api/v1/duty/{duty['id']}/approve", headers=emp_headers)
    assert self_appr.status_code == 403

    # shows as a duty task for HR
    tasks = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    assert any(t["task_type"] == "duty" and t["ref_id"] == duty["id"] for t in tasks)

    # HR approves -> attendance for the 3 days becomes wfh
    appr = await client.post(f"/api/v1/duty/{duty['id']}/approve", headers=hr_headers)
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"

    summary = (
        await client.get(
            f"/api/v1/attendance/summary?year=2026&month=7&employee_id={EMP_ID}",
            headers=hr_headers,
        )
    ).json()
    marked = {d["day"]: d["status"] for d in summary["days"]}
    assert marked["2026-07-06"] == "wfh"
    assert marked["2026-07-08"] == "wfh"


async def test_end_before_start_rejected(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/duty", headers=emp_headers,
        json={"duty_type": "wfh", "start_date": "2026-07-10", "end_date": "2026-07-06",
              "reason": "x"},
    )
    assert r.status_code == 422

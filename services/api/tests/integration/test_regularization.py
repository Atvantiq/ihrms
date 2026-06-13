"""Integration tests for attendance regularization (request → approve → record)."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002  # "Eli Employee", reports to ADMIN (100000000001)
WORK_DATE = "2026-06-08"  # a past Monday


async def test_request_requires_auth(client: AsyncClient) -> None:
    r = await client.post("/api/v1/attendance/regularizations", json={})
    assert r.status_code == 401


async def test_employee_requests_and_hr_approves_writes_record(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # employee files a regularization for a forgotten day
    req = await client.post(
        "/api/v1/attendance/regularizations",
        headers=emp_headers,
        json={"work_date": WORK_DATE, "requested_status": "present", "reason": "Forgot to mark"},
    )
    assert req.status_code == 201, req.text
    reg = req.json()
    assert reg["status"] == "pending"

    # duplicate pending request for the same day is rejected
    dup = await client.post(
        "/api/v1/attendance/regularizations",
        headers=emp_headers,
        json={"work_date": WORK_DATE, "requested_status": "present", "reason": "again"},
    )
    assert dup.status_code == 409

    # employee cannot approve their own
    self_appr = await client.post(
        f"/api/v1/attendance/regularizations/{reg['id']}/approve", headers=emp_headers, json={}
    )
    assert self_appr.status_code == 403

    # it appears in HR's task inbox as a regularization task
    tasks = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    assert any(t["task_type"] == "regularization" and t["ref_id"] == reg["id"] for t in tasks)

    # HR approves -> regularization approved AND attendance record written
    appr = await client.post(
        f"/api/v1/attendance/regularizations/{reg['id']}/approve",
        headers=hr_headers, json={"note": "ok"},
    )
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"

    summary = (
        await client.get(
            f"/api/v1/attendance/summary?year=2026&month=6&employee_id={EMP_ID}",
            headers=hr_headers,
        )
    ).json()
    marked = {d["day"]: d["status"] for d in summary["days"]}
    assert marked[WORK_DATE] == "present"

    # and it's gone from the inbox
    after = (await client.get("/api/v1/tasks", headers=hr_headers)).json()
    assert not any(t["ref_id"] == reg["id"] for t in after)


async def test_reject_does_not_write_record(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    other_date = "2026-06-09"
    reg = (
        await client.post(
            "/api/v1/attendance/regularizations",
            headers=emp_headers,
            json={"work_date": other_date, "requested_status": "wfh", "reason": "Was remote"},
        )
    ).json()
    rej = await client.post(
        f"/api/v1/attendance/regularizations/{reg['id']}/reject",
        headers=hr_headers, json={"note": "no proof"},
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"
    # day stays unmarked (not 'wfh')
    summary = (
        await client.get(
            f"/api/v1/attendance/summary?year=2026&month=6&employee_id={EMP_ID}",
            headers=hr_headers,
        )
    ).json()
    marked = {d["day"]: d["status"] for d in summary["days"]}
    assert marked.get(other_date) != "wfh"

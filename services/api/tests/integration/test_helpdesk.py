"""Integration tests for the helpdesk lifecycle."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

ADMIN = 100000000001


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/tickets", json={})).status_code == 401


async def test_raise_assign_resolve(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    raised = await client.post(
        "/api/v1/tickets", headers=emp_headers,
        json={"category": "it", "subject": "Laptop won't boot",
              "description": "Black screen since morning", "priority": "high"},
    )
    assert raised.status_code == 201, raised.text
    t = raised.json()
    assert t["status"] == "open"

    # raiser sees it under mine
    mine = (await client.get("/api/v1/tickets?scope=mine", headers=emp_headers)).json()
    assert any(x["id"] == t["id"] for x in mine)
    # non-HR can't list all
    assert (await client.get("/api/v1/tickets?scope=all", headers=emp_headers)).status_code == 403

    # HR assigns -> moves to in_progress
    assigned = await client.post(
        f"/api/v1/tickets/{t['id']}/assign", headers=hr_headers, json={"assignee_id": ADMIN},
    )
    assert assigned.status_code == 200
    assert assigned.json()["status"] == "in_progress"
    assert assigned.json()["assignee_id"] == ADMIN

    # resolve with a note
    resolved = await client.post(
        f"/api/v1/tickets/{t['id']}/status", headers=hr_headers,
        json={"status": "resolved", "resolution": "Replaced the SSD"},
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolution"] == "Replaced the SSD"
    assert resolved.json()["resolved_at"] is not None


async def test_bad_transition_rejected(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    t = (
        await client.post(
            "/api/v1/tickets", headers=emp_headers,
            json={"category": "payroll", "subject": "Payslip query", "description": "?"},
        )
    ).json()
    # open -> open is invalid (must use in_progress/resolved/closed)
    aid = {"assignee_id": ADMIN}
    await client.post(f"/api/v1/tickets/{t['id']}/assign", headers=hr_headers, json=aid)
    await client.post(
        f"/api/v1/tickets/{t['id']}/status", headers=hr_headers, json={"status": "closed"}
    )
    # closed -> resolved invalid
    r = await client.post(
        f"/api/v1/tickets/{t['id']}/status", headers=hr_headers, json={"status": "resolved"}
    )
    assert r.status_code == 409

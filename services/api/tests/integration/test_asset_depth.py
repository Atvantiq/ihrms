"""Integration tests for asset requests + maintenance log."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002  # seeded "Eli Employee"


async def _make_asset(client: AsyncClient, hr: dict[str, str], tag: str) -> dict:
    r = await client.post(
        "/api/v1/assets", headers=hr,
        json={"asset_tag": tag, "category": "laptop", "name": "ThinkPad",
              "purchase_date": "2025-01-01", "purchase_cost": "90000"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_request_approve_with_allocation(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # employee raises a request for themselves
    raised = await client.post(
        "/api/v1/assets/requests", headers=emp_headers,
        json={"category": "laptop", "justification": "Current one is failing"},
    )
    assert raised.status_code == 201, raised.text
    req = raised.json()
    assert req["status"] == "pending" and req["employee_id"] == EMP_ID

    # employee sees their own, but cannot list pending (HR-only scope)
    mine = (await client.get("/api/v1/assets/requests?scope=mine", headers=emp_headers)).json()
    assert any(r["id"] == req["id"] for r in mine)
    forbidden = await client.get("/api/v1/assets/requests?scope=pending", headers=emp_headers)
    assert forbidden.status_code == 403

    # HR approves WITH allocation of an in-stock asset -> request fulfilled, asset assigned
    asset = await _make_asset(client, hr_headers, "AST-REQ-1")
    approved = await client.post(
        f"/api/v1/assets/requests/{req['id']}/approve", headers=hr_headers,
        json={"asset_id": asset["id"], "note": "Allocated MacBook"},
    )
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "fulfilled"
    assert approved.json()["allocated_asset_id"] == asset["id"]

    # the allocated asset is now assigned to the requester
    held = (await client.get(f"/api/v1/assets/employee/{EMP_ID}", headers=hr_headers)).json()
    assert any(a["id"] == asset["id"] for a in held)

    # re-approving a non-pending request is rejected
    again = await client.post(
        f"/api/v1/assets/requests/{req['id']}/approve", headers=hr_headers, json={}
    )
    assert again.status_code == 409


async def test_request_reject(client: AsyncClient, hr_headers: dict[str, str],
                              emp_headers: dict[str, str]) -> None:
    raised = (await client.post(
        "/api/v1/assets/requests", headers=emp_headers,
        json={"category": "monitor", "justification": "Dual screen"},
    )).json()
    rej = await client.post(
        f"/api/v1/assets/requests/{raised['id']}/reject", headers=hr_headers,
        json={"note": "Budget freeze"},
    )
    assert rej.status_code == 200
    assert rej.json()["status"] == "rejected"
    assert rej.json()["decision_note"] == "Budget freeze"


async def test_maintenance_log(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    asset = await _make_asset(client, hr_headers, "AST-MNT-1")
    logged = await client.post(
        f"/api/v1/assets/{asset['id']}/maintenance", headers=hr_headers,
        json={"kind": "repair", "performed_on": "2026-05-10", "cost": "3500",
              "vendor": "Acme Repairs", "note": "Screen replacement"},
    )
    assert logged.status_code == 201, logged.text
    assert logged.json()["kind"] == "repair"
    assert logged.json()["cost"] == "3500.00"

    rows = (await client.get(
        f"/api/v1/assets/{asset['id']}/maintenance", headers=hr_headers
    )).json()
    assert len(rows) == 1 and rows[0]["vendor"] == "Acme Repairs"


async def test_maintenance_requires_hr(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/assets/00000000-0000-0000-0000-000000000000/maintenance",
        headers=emp_headers,
        json={"kind": "service", "performed_on": "2026-05-10"},
    )
    assert r.status_code == 403

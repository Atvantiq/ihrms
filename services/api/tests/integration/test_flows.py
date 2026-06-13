"""Integration tests — real app, real Postgres, real migrations.

Cover the DB-backed paths the unit suite can't: auth/role resolution,
directory reads through the view, employee writes to the shared tables,
the leave apply→approve balance lifecycle, holiday-aware day counts,
PII redaction, and audit recording.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_me_resolves_roles(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/me", headers=hr_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["is_hr"] is True
    assert "hr_admin" in body["roles"]


async def test_unauthenticated_is_401(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/me")).status_code == 401


async def test_directory_lists_seeded_employees(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.get("/api/v1/employees", headers=hr_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["stats"]["total"] == 2
    names = {i["full_name"] for i in body["items"]}
    assert {"Ada Admin", "Eli Employee"} <= names


async def test_non_hr_cannot_add_employee(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post("/api/v1/employees", headers=emp_headers, json={})
    assert r.status_code == 403


async def test_create_employee_writes_shared_tables(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    payload = {
        "first_name": "New",
        "last_name": "Hire",
        "email": "new.hire@example.com",
        "phone": "+910000000009",
        "employee_code": "EMP-NEW",
        "designation": "Analyst",
        "department": "Engineering",
        "division": "Central",
        "branch": "HQ",
        "circle_id": 1,
        "date_of_joining": "2026-06-01",
    }
    r = await client.post("/api/v1/employees", headers=hr_headers, json=payload)
    assert r.status_code == 201, r.text
    eid = r.json()["employee_id"]
    # appears in the directory
    listing = (await client.get("/api/v1/employees", headers=hr_headers)).json()
    assert any(i["employee_id"] == eid for i in listing["items"])
    # duplicate email rejected
    dup = await client.post("/api/v1/employees", headers=hr_headers, json=payload)
    assert dup.status_code == 409


async def test_pii_redaction(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # HR sets PAN on the employee
    await client.patch(
        f"/api/v1/employees/{100000000002}",
        headers=hr_headers,
        json={"pan_no": "ABCPE1234F"},
    )
    # HR sees it
    hr_view = (
        await client.get("/api/v1/employees/100000000002", headers=hr_headers)
    ).json()
    assert hr_view["pan_no"] == "ABCPE1234F"
    assert hr_view["pii_visible"] is True
    # the other employee does not
    other = (
        await client.get("/api/v1/employees/100000000001", headers=emp_headers)
    ).json()
    assert other["pan_no"] is None
    assert other["pii_visible"] is False


async def test_leave_apply_approve_balance_lifecycle(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    types = (await client.get("/api/v1/leave/types", headers=emp_headers)).json()
    cl = next(t for t in types if t["code"] == "CL")

    # balance before
    before = (await client.get("/api/v1/leave/balances", headers=emp_headers)).json()
    cl_before = next(b for b in before if b["code"] == "CL")
    avail0 = float(cl_before["available"])

    # apply 2 working days (Mon–Tue)
    apply = await client.post(
        "/api/v1/leave/requests",
        headers=emp_headers,
        json={
            "leave_type_id": cl["id"],
            "start_date": "2026-07-06",
            "end_date": "2026-07-07",
        },
    )
    assert apply.status_code == 201, apply.text
    req = apply.json()
    assert float(req["days"]) == 2.0
    assert req["status"] == "pending"

    # reserved as pending
    mid = (await client.get("/api/v1/leave/balances", headers=emp_headers)).json()
    cl_mid = next(b for b in mid if b["code"] == "CL")
    assert float(cl_mid["pending"]) == 2.0
    assert float(cl_mid["available"]) == avail0 - 2.0

    # employee cannot approve their own
    self_appr = await client.post(
        f"/api/v1/leave/requests/{req['id']}/approve", headers=emp_headers, json={}
    )
    assert self_appr.status_code == 403

    # HR approves -> used, pending released
    appr = await client.post(
        f"/api/v1/leave/requests/{req['id']}/approve",
        headers=hr_headers,
        json={"note": "ok"},
    )
    assert appr.status_code == 200
    assert appr.json()["status"] == "approved"

    after = (await client.get("/api/v1/leave/balances", headers=emp_headers)).json()
    cl_after = next(b for b in after if b["code"] == "CL")
    assert float(cl_after["used"]) == 2.0
    assert float(cl_after["pending"]) == 0.0


async def test_leave_excludes_holiday(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # add a holiday on Wed 2026-07-15
    h = await client.post(
        "/api/v1/holidays",
        headers=hr_headers,
        json={"name": "Test Holiday", "holiday_date": "2026-07-15"},
    )
    assert h.status_code == 201
    types = (await client.get("/api/v1/leave/types", headers=emp_headers)).json()
    sl = next(t for t in types if t["code"] == "SL")
    # Mon–Fri 2026-07-13..17 with Wed a holiday => 4 days
    r = await client.post(
        "/api/v1/leave/requests",
        headers=emp_headers,
        json={
            "leave_type_id": sl["id"],
            "start_date": "2026-07-13",
            "end_date": "2026-07-17",
        },
    )
    assert r.status_code == 201, r.text
    assert float(r.json()["days"]) == 4.0


async def test_pan_is_validated_and_normalised(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    # a malformed PAN is rejected at the boundary
    bad = await client.patch(
        "/api/v1/employees/100000000002", headers=hr_headers, json={"pan_no": "NOTAPAN"}
    )
    assert bad.status_code == 422
    # a valid lowercase PAN is accepted and stored upper-cased
    ok = await client.patch(
        "/api/v1/employees/100000000002", headers=hr_headers, json={"pan_no": " abcpe1234f "}
    )
    assert ok.status_code in (200, 204), ok.text
    view = (
        await client.get("/api/v1/employees/100000000002", headers=hr_headers)
    ).json()
    assert view["pan_no"] == "ABCPE1234F"


async def test_writes_are_audited(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    events = (
        await client.get(
            "/api/v1/audit/events?entity_type=employee", headers=hr_headers
        )
    ).json()
    actions = {e["action"] for e in events}
    assert "employee.create" in actions or "employee.update" in actions

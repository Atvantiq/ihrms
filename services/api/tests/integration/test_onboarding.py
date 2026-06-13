"""Integration tests for onboarding templates + per-hire checklists."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002  # seeded "Eli Employee"


async def test_template_seeded_and_extendable(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    tpl = (await client.get("/api/v1/onboarding/template", headers=hr_headers)).json()
    assert len(tpl) >= 6  # standard checklist seeded by the migration
    added = await client.post(
        "/api/v1/onboarding/template", headers=hr_headers,
        json={"title": "Order swag kit", "owner_role": "hr", "sort_order": 70},
    )
    assert added.status_code == 201
    tpl2 = (await client.get("/api/v1/onboarding/template", headers=hr_headers)).json()
    assert any(t["title"] == "Order swag kit" for t in tpl2)


async def test_generate_and_work_checklist(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    gen = await client.post(
        f"/api/v1/onboarding/employees/{EMP_ID}/generate", headers=hr_headers
    )
    assert gen.status_code == 201, gen.text
    body = gen.json()
    assert body["total"] >= 6
    assert body["done"] == 0 and body["pct"] == 0

    # idempotent — second generate doesn't duplicate
    again = (await client.post(
        f"/api/v1/onboarding/employees/{EMP_ID}/generate", headers=hr_headers
    )).json()
    assert again["total"] == body["total"]

    # the employee can see and work their own checklist
    own = (await client.get(
        f"/api/v1/onboarding/employees/{EMP_ID}/tasks", headers=emp_headers
    )).json()
    first = own["tasks"][0]["id"]
    toggled = (await client.post(
        f"/api/v1/onboarding/employees/{EMP_ID}/tasks/{first}/toggle", headers=emp_headers
    )).json()
    assert toggled["done"] == 1
    assert next(t for t in toggled["tasks"] if t["id"] == first)["status"] == "done"
    assert toggled["pct"] > 0

    # in-progress overview lists this employee (not fully complete)
    overview = (await client.get("/api/v1/onboarding/in-progress", headers=hr_headers)).json()
    assert any(o["employee_id"] == EMP_ID for o in overview)


async def test_cannot_view_others(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.get(
        "/api/v1/onboarding/employees/100000000001/tasks", headers=emp_headers
    )
    assert r.status_code == 403


async def test_generate_requires_hr(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        f"/api/v1/onboarding/employees/{EMP_ID}/generate", headers=emp_headers
    )
    assert r.status_code == 403

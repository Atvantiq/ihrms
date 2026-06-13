"""Integration tests for the asset register & assignment lifecycle."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002  # seeded "Eli Employee"


async def _make_asset(client: AsyncClient, hr: dict[str, str], tag: str) -> dict:
    r = await client.post(
        "/api/v1/assets",
        headers=hr,
        json={
            "asset_tag": tag,
            "category": "laptop",
            "name": "MacBook Pro 14",
            "serial_no": "C02XYZ",
            "purchase_date": "2025-01-01",
            "purchase_cost": "150000",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_non_hr_cannot_register(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post("/api/v1/assets", headers=emp_headers, json={
        "asset_tag": "X", "name": "Y",
    })
    assert r.status_code == 403


async def test_register_computes_book_value(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    a = await _make_asset(client, hr_headers, "AST-BV-1")
    assert a["status"] == "in_stock"
    # a 2025-bought laptop is partly depreciated by 2026 but not zero
    assert a["book_value"] is not None
    assert 0 < float(a["book_value"]) < 150000


async def test_assign_then_return_lifecycle(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    a = await _make_asset(client, hr_headers, "AST-LIFE-1")
    aid = a["id"]

    # assign to the employee
    assigned = await client.post(
        f"/api/v1/assets/{aid}/assign", headers=hr_headers,
        json={"employee_id": EMP_ID, "note": "Onboarding kit"},
    )
    assert assigned.status_code == 200, assigned.text
    body = assigned.json()
    assert body["status"] == "assigned"
    assert body["holder_id"] == EMP_ID

    # it now shows up under the employee (self can see their own)
    mine = (await client.get(f"/api/v1/assets/employee/{EMP_ID}", headers=emp_headers)).json()
    assert any(x["id"] == aid for x in mine)

    # cannot assign an already-assigned asset
    again = await client.post(
        f"/api/v1/assets/{aid}/assign", headers=hr_headers, json={"employee_id": EMP_ID}
    )
    assert again.status_code == 409

    # return it -> back in stock, no holder
    returned = await client.post(
        f"/api/v1/assets/{aid}/return", headers=hr_headers, json={"condition": "fair"}
    )
    assert returned.status_code == 200
    assert returned.json()["status"] == "in_stock"
    assert returned.json()["holder_id"] is None

    # employee no longer holds it
    mine2 = (await client.get(f"/api/v1/assets/employee/{EMP_ID}", headers=emp_headers)).json()
    assert not any(x["id"] == aid for x in mine2)


async def test_employee_cannot_see_others_assets(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # employee asking for someone else's assets is forbidden
    r = await client.get("/api/v1/assets/employee/100000000001", headers=emp_headers)
    assert r.status_code == 403

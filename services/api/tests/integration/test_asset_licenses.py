"""Integration tests for software licenses + lost-asset register."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002
ADMIN_ID = 100000000001


async def _asset(client: AsyncClient, hr: dict[str, str], tag: str) -> dict:
    r = await client.post(
        "/api/v1/assets", headers=hr,
        json={"asset_tag": tag, "category": "laptop", "name": "ThinkPad"},
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_license_seat_tracking(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    lic = await client.post(
        "/api/v1/assets/licenses", headers=hr_headers,
        json={"name": "Figma", "vendor": "Figma Inc", "seats_total": 1,
              "renewal_date": "2030-01-01", "cost_annual": "12000"},
    )
    assert lic.status_code == 201, lic.text
    lid = lic.json()["id"]
    assert lic.json()["seats_available"] == 1
    assert lic.json()["renewal_status"] == "active"

    # assign the only seat
    after = await client.post(
        f"/api/v1/assets/licenses/{lid}/assign", headers=hr_headers,
        json={"employee_id": EMP_ID},
    )
    assert after.status_code == 201
    assert after.json()["seats_used"] == 1 and after.json()["seats_available"] == 0

    # no seats left -> 409
    full = await client.post(
        f"/api/v1/assets/licenses/{lid}/assign", headers=hr_headers,
        json={"employee_id": ADMIN_ID},
    )
    assert full.status_code == 409

    # revoke frees a seat
    seats = (await client.get(
        f"/api/v1/assets/licenses/{lid}/seats", headers=hr_headers
    )).json()
    seat_id = seats[0]["id"]
    rev = await client.post(
        f"/api/v1/assets/licenses/seats/{seat_id}/revoke", headers=hr_headers
    )
    assert rev.status_code == 204
    listed = (await client.get("/api/v1/assets/licenses", headers=hr_headers)).json()
    figma = next(x for x in listed if x["id"] == lid)
    assert figma["seats_available"] == 1


async def test_lost_register(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    a = await _asset(client, hr_headers, "AST-LOST-1")
    lost = await client.post(
        f"/api/v1/assets/{a['id']}/lost", headers=hr_headers,
        json={"circumstances": "Stolen from car", "police_report": True},
    )
    assert lost.status_code == 200, lost.text
    assert lost.json()["status"] == "lost"

    # marking lost again is rejected
    again = await client.post(
        f"/api/v1/assets/{a['id']}/lost", headers=hr_headers,
        json={"circumstances": "x"},
    )
    assert again.status_code == 409

    register = (await client.get("/api/v1/assets/lost", headers=hr_headers)).json()
    entry = next(x for x in register if x["asset_id"] == a["id"])
    assert entry["circumstances"] == "Stolen from car"
    assert entry["police_report"] is True


async def test_non_hr_blocked(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/assets/licenses", headers=emp_headers)
    assert r.status_code == 403

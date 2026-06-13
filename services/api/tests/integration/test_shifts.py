"""Integration tests for shifts: master, assignment, roster, self-view."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_default_general_shift_seeded(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    shifts = (await client.get("/api/v1/shifts", headers=hr_headers)).json()
    gen = next(s for s in shifts if s["code"] == "GEN")
    assert gen["hours"] == "8.00"  # 9:30–18:30 less 60m break


async def test_non_hr_cannot_create(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/shifts", headers=emp_headers,
        json={"code": "X", "name": "X", "start_time": "09:00", "end_time": "17:00"},
    )
    assert r.status_code == 403


async def test_create_assign_and_roster(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    night = await client.post(
        "/api/v1/shifts", headers=hr_headers,
        json={"code": "NIGHT", "name": "Night", "start_time": "22:00",
              "end_time": "06:00", "break_minutes": 30},
    )
    assert night.status_code == 201, night.text
    body = night.json()
    assert body["is_night"] is True
    assert body["hours"] == "7.50"
    shift_id = body["id"]

    # assign the night shift to the employee
    assigned = await client.post(
        "/api/v1/shifts/assign", headers=hr_headers,
        json={"employee_id": EMP_ID, "shift_id": shift_id, "effective_from": "2026-06-01"},
    )
    assert assigned.status_code == 201, assigned.text

    # roster shows the employee on the night shift
    roster = (await client.get("/api/v1/shifts/roster?on=2026-06-15", headers=hr_headers)).json()
    mine = next(r for r in roster if r["employee_id"] == EMP_ID)
    assert mine["shift_code"] == "NIGHT"

    # the employee sees their own shift
    my = (await client.get("/api/v1/shifts/my", headers=emp_headers)).json()
    assert my is not None
    assert my["shift_code"] == "NIGHT"


async def test_employee_cannot_see_others_shift(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.get("/api/v1/shifts/my?employee_id=100000000001", headers=emp_headers)
    assert r.status_code == 403

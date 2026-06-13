"""Integration tests for the PIP lifecycle."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_non_hr_cannot_open(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/pip", headers=emp_headers,
        json={"employee_id": EMP_ID, "reason": "x", "objectives": "y",
              "start_date": "2026-06-01", "end_date": "2026-09-01"},
    )
    assert r.status_code == 403


async def test_open_checkpoint_close(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    opened = await client.post(
        "/api/v1/pip", headers=hr_headers,
        json={"employee_id": EMP_ID, "reason": "Missed delivery targets",
              "objectives": "Ship 3 features; close 90% tickets in SLA",
              "start_date": "2026-06-01", "end_date": "2026-09-01"},
    )
    assert opened.status_code == 201, opened.text
    pip = opened.json()
    assert pip["status"] == "active"
    assert len(pip["suggested_checkpoints"]) == 3

    # employee sees their own PIP
    mine = (await client.get("/api/v1/pip?scope=mine", headers=emp_headers)).json()
    assert any(p["id"] == pip["id"] for p in mine)

    # HR records a checkpoint
    cp = await client.post(
        f"/api/v1/pip/{pip['id']}/checkpoint", headers=hr_headers,
        json={"rating": "at_risk", "note": "Two of three objectives behind"},
    )
    assert cp.status_code == 200
    assert len(cp.json()["checkpoints"]) == 1

    # close it
    closed = await client.post(
        f"/api/v1/pip/{pip['id']}/close", headers=hr_headers, json={"outcome": "improved"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "improved"

    # can't checkpoint a closed PIP
    cp2 = await client.post(
        f"/api/v1/pip/{pip['id']}/checkpoint", headers=hr_headers, json={"rating": "on_track"},
    )
    assert cp2.status_code == 409


async def test_end_before_start_rejected(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/pip", headers=hr_headers,
        json={"employee_id": EMP_ID, "reason": "x", "objectives": "y",
              "start_date": "2026-09-01", "end_date": "2026-06-01"},
    )
    assert r.status_code == 422

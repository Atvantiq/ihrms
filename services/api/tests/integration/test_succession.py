"""Integration tests for succession planning."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

ADMIN_ID = 100000000001
EMP_ID = 100000000002


async def test_position_and_bench_flow(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    pos = await client.post(
        "/api/v1/succession/positions", headers=hr_headers,
        json={"title": "Head of Engineering", "incumbent_id": ADMIN_ID,
              "risk_level": "high"},
    )
    assert pos.status_code == 201, pos.text
    body = pos.json()
    pid = body["id"]
    assert body["incumbent_name"]  # joined from employees
    assert body["bench_status"] == "at_risk"  # no successors yet

    # add a developing successor -> 'developing'
    dev = await client.post(
        f"/api/v1/succession/positions/{pid}/candidates", headers=hr_headers,
        json={"employee_id": EMP_ID, "readiness": "1_2_years", "note": "Strong IC"},
    )
    assert dev.status_code == 201
    assert dev.json()["bench_status"] == "developing"
    assert dev.json()["ready_now"] == 0

    # dup candidate rejected
    again = await client.post(
        f"/api/v1/succession/positions/{pid}/candidates", headers=hr_headers,
        json={"employee_id": EMP_ID, "readiness": "ready_now"},
    )
    assert again.status_code == 409

    # listed back with the candidate
    positions = (await client.get("/api/v1/succession/positions", headers=hr_headers)).json()
    p = next(x for x in positions if x["id"] == pid)
    assert any(c["employee_id"] == EMP_ID for c in p["candidates"])

    # remove the candidate -> back to at_risk
    cand_id = p["candidates"][0]["id"]
    rem = await client.delete(
        f"/api/v1/succession/positions/{pid}/candidates/{cand_id}", headers=hr_headers
    )
    assert rem.status_code == 204
    positions2 = (await client.get("/api/v1/succession/positions", headers=hr_headers)).json()
    p2 = next(x for x in positions2 if x["id"] == pid)
    assert p2["bench_status"] == "at_risk"


async def test_requires_hr(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/succession/positions", headers=emp_headers)
    assert r.status_code == 403

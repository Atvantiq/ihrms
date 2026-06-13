"""Integration tests for the Employee 360 personal-records bundle."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002    # seeded "Eli Employee"
OTHER_ID = 100000000001  # seeded admin


async def test_non_hr_cannot_write(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        f"/api/v1/employees/{EMP_ID}/education", headers=emp_headers,
        json={"degree": "B.Tech"},
    )
    assert r.status_code == 403


async def test_employee_reads_own_but_not_others(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    own = await client.get(f"/api/v1/employees/{EMP_ID}/records", headers=emp_headers)
    assert own.status_code == 200
    other = await client.get(f"/api/v1/employees/{OTHER_ID}/records", headers=emp_headers)
    assert other.status_code == 403


async def test_full_bundle_roundtrip(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    # one of each record type
    assert (await client.post(
        f"/api/v1/employees/{EMP_ID}/education", headers=hr_headers,
        json={"degree": "M.Tech", "institution": "IIT", "year_completed": 2018, "grade": "8.7"},
    )).status_code == 201
    assert (await client.post(
        f"/api/v1/employees/{EMP_ID}/experience", headers=hr_headers,
        json={"employer": "Acme Corp", "designation": "SDE", "from_date": "2018-07-01"},
    )).status_code == 201
    assert (await client.post(
        f"/api/v1/employees/{EMP_ID}/awards", headers=hr_headers,
        json={"title": "Star Performer", "awarded_on": "2025-01-15"},
    )).status_code == 201
    assert (await client.post(
        f"/api/v1/employees/{EMP_ID}/training", headers=hr_headers,
        json={"program": "Leadership 101", "status": "completed", "completed_on": "2025-06-01"},
    )).status_code == 201
    assert (await client.post(
        f"/api/v1/employees/{EMP_ID}/incidents", headers=hr_headers,
        json={"kind": "accident", "incident_date": "2025-03-10", "severity": "low",
              "description": "Minor slip in canteen", "status": "closed"},
    )).status_code == 201

    bundle = (await client.get(
        f"/api/v1/employees/{EMP_ID}/records", headers=hr_headers
    )).json()
    assert any(e["degree"] == "M.Tech" for e in bundle["education"])
    assert any(x["employer"] == "Acme Corp" for x in bundle["experience"])
    assert any(a["title"] == "Star Performer" for a in bundle["awards"])
    assert any(t["program"] == "Leadership 101" for t in bundle["training"])
    assert any(i["kind"] == "accident" for i in bundle["incidents"])
    # seeded employees carry DOB/DOJ -> derived special dates present
    assert len(bundle["special_dates"]) >= 1


async def test_nominee_share_cap(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r1 = await client.post(
        f"/api/v1/employees/{EMP_ID}/family", headers=hr_headers,
        json={"relation": "spouse", "full_name": "Priya", "is_nominee": True,
              "nominee_share": "70"},
    )
    assert r1.status_code == 201, r1.text
    # a second nominee that would push the total over 100% is rejected
    r2 = await client.post(
        f"/api/v1/employees/{EMP_ID}/family", headers=hr_headers,
        json={"relation": "child", "full_name": "Aarav", "is_nominee": True,
              "nominee_share": "40"},
    )
    assert r2.status_code == 422

    bundle = (await client.get(
        f"/api/v1/employees/{EMP_ID}/records", headers=hr_headers
    )).json()
    nominee = next(f for f in bundle["family"] if f["full_name"] == "Priya")
    assert nominee["is_nominee"] is True

    # delete the family record we added, bundle reflects it
    deleted = await client.delete(
        f"/api/v1/employees/{EMP_ID}/records/family/{nominee['id']}", headers=hr_headers
    )
    assert deleted.status_code == 204
    after = (await client.get(
        f"/api/v1/employees/{EMP_ID}/records", headers=hr_headers
    )).json()
    assert not any(f["id"] == nominee["id"] for f in after["family"])

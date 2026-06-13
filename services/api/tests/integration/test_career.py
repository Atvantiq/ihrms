"""Integration tests for career ladders, competencies, expectations, placement."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002
ADMIN_ID = 100000000001


async def test_seeded_track_and_levels(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    tracks = (await client.get("/api/v1/career/tracks", headers=hr_headers)).json()
    eng = next(t for t in tracks if t["name"] == "Engineering")
    assert len(eng["levels"]) == 4
    # levels come back rank-ordered
    assert [lv["rank"] for lv in eng["levels"]] == [1, 2, 3, 4]

    comps = (await client.get("/api/v1/career/competencies", headers=hr_headers)).json()
    assert any(c["name"] == "Technical depth" for c in comps)


async def test_expectations_and_placement_flow(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    tracks = (await client.get("/api/v1/career/tracks", headers=hr_headers)).json()
    eng = next(t for t in tracks if t["name"] == "Engineering")
    senior = next(lv for lv in eng["levels"] if lv["rank"] == 2)
    comps = (await client.get("/api/v1/career/competencies", headers=hr_headers)).json()
    tech = next(c for c in comps if c["name"] == "Technical depth")

    # set an expectation on the Senior level
    exps = await client.post(
        f"/api/v1/career/levels/{senior['id']}/expectations", headers=hr_headers,
        json={"competency_id": tech["id"], "expectation": "Owns a service end to end"},
    )
    assert exps.status_code == 201, exps.text
    assert any(e["competency_name"] == "Technical depth" for e in exps.json())

    # place the employee on the Senior level
    placed = await client.put(
        f"/api/v1/career/employees/{EMP_ID}/placement", headers=hr_headers,
        json={"level_id": senior["id"]},
    )
    assert placed.status_code == 200, placed.text
    ladder = placed.json()
    assert ladder["level"]["name"] == "Senior Engineer"
    assert ladder["track_name"] == "Engineering"
    assert ladder["next_level"]["name"] == "Staff Engineer"
    assert any(e["expectation"] == "Owns a service end to end" for e in ladder["expectations"])

    # employee can read their own ladder, not others'
    own = await client.get(f"/api/v1/career/employees/{EMP_ID}/ladder", headers=emp_headers)
    assert own.status_code == 200
    assert own.json()["level"]["rank"] == 2
    other = await client.get(
        f"/api/v1/career/employees/{ADMIN_ID}/ladder", headers=emp_headers
    )
    assert other.status_code == 403


async def test_duplicate_rank_rejected(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    tracks = (await client.get("/api/v1/career/tracks", headers=hr_headers)).json()
    eng = next(t for t in tracks if t["name"] == "Engineering")
    r = await client.post(
        f"/api/v1/career/tracks/{eng['id']}/levels", headers=hr_headers,
        json={"name": "Dup", "rank": 1},
    )
    assert r.status_code == 409


async def test_writes_require_hr(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/career/competencies", headers=emp_headers, json={"name": "Sneaky"}
    )
    assert r.status_code == 403

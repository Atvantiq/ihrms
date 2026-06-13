"""Integration tests for the deeper Exit tabs — KT, interview, alumni, analytics."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002  # seeded "Eli Employee"


async def _open_case(client: AsyncClient, hr: dict[str, str]) -> str:
    # one non-paid case per employee is allowed — reuse if a prior test opened one
    existing = (await client.get("/api/v1/exit/cases", headers=hr)).json()
    for c in existing:
        if c["employee_id"] == EMP_ID and c["status"] != "paid":
            return c["id"]
    r = await client.post(
        "/api/v1/exit/cases", headers=hr,
        json={"employee_id": EMP_ID, "resignation_date": "2026-05-01",
              "last_working_day": "2026-06-30", "reason": "Better opportunity"},
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_kt_seed_toggle(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    case_id = await _open_case(client, hr_headers)
    seeded = (await client.post(
        f"/api/v1/exit/cases/{case_id}/kt/seed-defaults", headers=hr_headers
    )).json()
    assert len(seeded) == 5
    assert all(i["status"] == "pending" for i in seeded)

    # seeding again is idempotent
    again = (await client.post(
        f"/api/v1/exit/cases/{case_id}/kt/seed-defaults", headers=hr_headers
    )).json()
    assert len(again) == 5

    # add a custom task
    added = (await client.post(
        f"/api/v1/exit/cases/{case_id}/kt", headers=hr_headers,
        json={"task": "Return office keys", "assignee": "Facilities"},
    )).json()
    assert len(added) == 6

    # toggle one done
    first = added[0]["id"]
    toggled = (await client.post(
        f"/api/v1/exit/cases/{case_id}/kt/{first}/toggle", headers=hr_headers
    )).json()
    assert next(i for i in toggled if i["id"] == first)["status"] == "done"


async def test_interview_upsert(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    case_id = await _open_case(client, hr_headers)
    assert (await client.get(
        f"/api/v1/exit/cases/{case_id}/interview", headers=hr_headers
    )).json() is None

    saved = await client.put(
        f"/api/v1/exit/cases/{case_id}/interview", headers=hr_headers,
        json={"primary_reason": "Compensation", "would_recommend": True,
              "rating_management": 4, "rating_role": 3, "rating_culture": 5,
              "feedback": "Great team", "conducted_on": "2026-06-20"},
    )
    assert saved.status_code == 200, saved.text
    assert saved.json()["rating_culture"] == 5

    # re-PUT updates in place (no duplicate row)
    again = await client.put(
        f"/api/v1/exit/cases/{case_id}/interview", headers=hr_headers,
        json={"primary_reason": "Relocation", "would_recommend": False},
    )
    assert again.json()["primary_reason"] == "Relocation"
    fetched = (await client.get(
        f"/api/v1/exit/cases/{case_id}/interview", headers=hr_headers
    )).json()
    assert fetched["primary_reason"] == "Relocation"
    assert fetched["would_recommend"] is False


async def test_alumni_and_analytics(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    await _open_case(client, hr_headers)
    up = await client.post(
        "/api/v1/exit/alumni", headers=hr_headers,
        json={"employee_id": EMP_ID, "eligible_for_rehire": True,
              "personal_email": "eli@example.com", "note": "Strong performer"},
    )
    assert up.status_code == 201, up.text
    assert up.json()["eligible_for_rehire"] is True

    alumni = (await client.get("/api/v1/exit/alumni", headers=hr_headers)).json()
    assert any(a["employee_id"] == EMP_ID for a in alumni)

    analytics = (await client.get("/api/v1/exit/analytics", headers=hr_headers)).json()
    assert analytics["total_exits"] >= 1
    assert "attrition_rate_pct" in analytics
    assert isinstance(analytics["by_reason"], dict)


async def test_non_hr_blocked(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/exit/analytics", headers=emp_headers)
    assert r.status_code == 403

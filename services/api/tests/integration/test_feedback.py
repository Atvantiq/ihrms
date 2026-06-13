"""Integration tests for feedback & recognition."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

ADMIN = 100000000001  # Ada Admin
EMP = 100000000002    # Eli Employee


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.post("/api/v1/feedback", json={})).status_code == 401


async def test_cannot_feedback_self(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/feedback", headers=emp_headers,
        json={"to_employee_id": EMP, "message": "great work me"},
    )
    assert r.status_code == 409


async def test_private_feedback_visible_to_recipient(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    # HR (Ada) gives Eli private feedback
    sent = await client.post(
        "/api/v1/feedback", headers=hr_headers,
        json={"to_employee_id": EMP, "kind": "feedback", "visibility": "private",
              "message": "Strong ownership on the release."},
    )
    assert sent.status_code == 201, sent.text
    fid = sent.json()["id"]

    # Eli sees it in received
    received = (await client.get("/api/v1/feedback/received", headers=emp_headers)).json()
    assert any(f["id"] == fid for f in received)
    # Ada sees it in given
    given = (await client.get("/api/v1/feedback/given", headers=hr_headers)).json()
    assert any(f["id"] == fid for f in given)


async def test_public_recognition_on_wall(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    badges = (await client.get("/api/v1/feedback/badges", headers=emp_headers)).json()
    assert "teamwork" in badges

    rec = await client.post(
        "/api/v1/feedback", headers=emp_headers,
        json={"to_employee_id": ADMIN, "kind": "recognition", "badge": "teamwork",
              "visibility": "public", "message": "Thanks for unblocking us!"},
    )
    assert rec.status_code == 201, rec.text
    rid = rec.json()["id"]

    # anyone sees it on the wall
    wall = (await client.get("/api/v1/feedback/wall", headers=hr_headers)).json()
    card = next((f for f in wall if f["id"] == rid), None)
    assert card is not None
    assert card["badge"] == "teamwork"
    assert card["from_name"] and card["to_name"]


async def test_unknown_badge_rejected(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/feedback", headers=emp_headers,
        json={"to_employee_id": ADMIN, "kind": "recognition", "badge": "bogus",
              "message": "x"},
    )
    assert r.status_code == 404

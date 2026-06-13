"""Integration tests for platform announcements (Track-B TB3).

Covers the RBAC split that the unit suite can't: super_admin authors and
retracts, every authenticated user reads active ones, and the write is audited.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

POST = "/api/v1/control-plane/announcements"


async def test_super_admin_can_post_and_all_users_read(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        POST,
        headers=hr_headers,
        json={"title": "Release 1.1", "body": "Payroll PDFs now bilingual.", "level": "success"},
    )
    assert r.status_code == 201, r.text
    ann = r.json()
    assert ann["level"] == "success"
    assert ann["id"]

    # a plain employee — not super_admin — still sees it
    listing = (await client.get(POST, headers=emp_headers)).json()
    assert any(a["id"] == ann["id"] for a in listing)


async def test_non_super_admin_cannot_post(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        POST, headers=emp_headers, json={"title": "x", "body": "y", "level": "info"}
    )
    assert r.status_code == 403


async def test_unauthenticated_cannot_read(client: AsyncClient) -> None:
    assert (await client.get(POST)).status_code == 401


async def test_invalid_level_rejected(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    r = await client.post(
        POST, headers=hr_headers, json={"title": "x", "body": "y", "level": "critical"}
    )
    assert r.status_code == 422


async def test_retract_hides_announcement(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    created = (
        await client.post(
            POST,
            headers=hr_headers,
            json={"title": "Temp notice", "body": "Will be retracted.", "level": "info"},
        )
    ).json()
    aid = created["id"]
    assert any(a["id"] == aid for a in (await client.get(POST, headers=emp_headers)).json())

    # an employee cannot retract
    assert (
        await client.delete(f"{POST}/{aid}", headers=emp_headers)
    ).status_code == 403

    # super_admin retracts -> gone from the active list
    assert (await client.delete(f"{POST}/{aid}", headers=hr_headers)).status_code == 204
    assert not any(a["id"] == aid for a in (await client.get(POST, headers=emp_headers)).json())


async def test_post_is_audited(
    client: AsyncClient, hr_headers: dict[str, str]
) -> None:
    await client.post(
        POST,
        headers=hr_headers,
        json={"title": "Audited notice", "body": "Should appear in audit.", "level": "info"},
    )
    events = (
        await client.get(
            "/api/v1/audit/events?entity_type=announcement", headers=hr_headers
        )
    ).json()
    assert any(e["action"] == "announcement.post" for e in events)

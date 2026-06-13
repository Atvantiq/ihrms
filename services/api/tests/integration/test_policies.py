"""Integration tests for policies & acknowledgements."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/policies")).status_code == 401


async def test_non_hr_cannot_publish(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/policies", headers=emp_headers,
        json={"title": "X", "body": "Y"},
    )
    assert r.status_code == 403


async def test_publish_acknowledge_compliance(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    pub = await client.post(
        "/api/v1/policies", headers=hr_headers,
        json={"title": "Code of Conduct", "category": "compliance",
              "body": "Be excellent to each other.", "version": 2},
    )
    assert pub.status_code == 201, pub.text
    pid = pub.json()["id"]

    # employee sees it as not-yet-acknowledged
    listing = (await client.get("/api/v1/policies", headers=emp_headers)).json()
    mine = next(p for p in listing if p["id"] == pid)
    assert mine["acknowledged"] is False

    # acknowledge it (idempotent)
    ack = await client.post(f"/api/v1/policies/{pid}/ack", headers=emp_headers)
    assert ack.status_code == 200
    assert ack.json()["acknowledged"] is True
    await client.post(f"/api/v1/policies/{pid}/ack", headers=emp_headers)  # no error on repeat

    after = (await client.get("/api/v1/policies", headers=emp_headers)).json()
    assert next(p for p in after if p["id"] == pid)["acknowledged"] is True

    # HR compliance reflects at least one acknowledgement
    comp = (await client.get(f"/api/v1/policies/{pid}/compliance", headers=hr_headers)).json()
    assert comp["acknowledged"] >= 1
    assert comp["headcount"] >= comp["acknowledged"]
    assert comp["pending"] == comp["headcount"] - comp["acknowledged"]


async def test_compliance_hr_only(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    pid = (
        await client.post(
            "/api/v1/policies", headers=hr_headers, json={"title": "WFH policy", "body": "..."},
        )
    ).json()["id"]
    r = await client.get(f"/api/v1/policies/{pid}/compliance", headers=emp_headers)
    assert r.status_code == 403

"""Integration tests for DPDP consent."""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

EMP_ID = 100000000002


async def test_consent_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/v1/consent")).status_code == 401


async def test_defaults_to_not_given(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    lines = (await client.get("/api/v1/consent", headers=emp_headers)).json()
    # every defined purpose is present and ungranted by default
    assert len(lines) >= 4
    assert all(line["status"] == "not_given" for line in lines)
    assert any(line["purpose"] == "payroll_banking" and line["required"] for line in lines)


async def test_grant_then_withdraw(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    granted = await client.post(
        "/api/v1/consent", headers=emp_headers,
        json={"purpose": "communications", "grant": True},
    )
    assert granted.status_code == 200
    line = next(c for c in granted.json() if c["purpose"] == "communications")
    assert line["status"] == "granted"
    assert line["decided_at"] is not None

    withdrawn = await client.post(
        "/api/v1/consent", headers=emp_headers,
        json={"purpose": "communications", "grant": False},
    )
    line = next(c for c in withdrawn.json() if c["purpose"] == "communications")
    assert line["status"] == "withdrawn"


async def test_unknown_purpose_rejected(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/consent", headers=emp_headers, json={"purpose": "selling_data", "grant": True}
    )
    assert r.status_code == 404


async def test_cannot_manage_others_consent(
    client: AsyncClient, emp_headers: dict[str, str]
) -> None:
    r = await client.post(
        "/api/v1/consent?employee_id=100000000001", headers=emp_headers,
        json={"purpose": "communications", "grant": True},
    )
    assert r.status_code == 403


async def test_hr_overview(
    client: AsyncClient, hr_headers: dict[str, str], emp_headers: dict[str, str]
) -> None:
    await client.post(
        "/api/v1/consent", headers=emp_headers,
        json={"purpose": "data_processing", "grant": True},
    )
    overview = (await client.get("/api/v1/consent/overview", headers=hr_headers)).json()
    dp = next(o for o in overview if o["purpose"] == "data_processing")
    assert dp["granted"] >= 1
    # non-HR cannot see the overview
    assert (await client.get("/api/v1/consent/overview", headers=emp_headers)).status_code == 403

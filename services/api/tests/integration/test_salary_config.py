"""Integration tests for salary config (component catalogue + preview)."""

from decimal import Decimal

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def test_seeded_components(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    comps = (await client.get("/api/v1/salary-config/components", headers=hr_headers)).json()
    codes = {c["code"] for c in comps}
    assert {"BASIC", "HRA", "SPECIAL"} <= codes


async def test_non_hr_forbidden(client: AsyncClient, emp_headers: dict[str, str]) -> None:
    r = await client.get("/api/v1/salary-config/components", headers=emp_headers)
    assert r.status_code == 403


async def test_preview_matches_builtin(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    # 12L CTC should resolve to the standard 40/50 split = gross 98200
    rep = (
        await client.get("/api/v1/salary-config/preview?ctc_annual=1200000", headers=hr_headers)
    ).json()
    by = {line["code"]: Decimal(line["amount"]) for line in rep["lines"]}
    assert by["BASIC"] == 40000
    assert by["HRA"] == 20000
    assert Decimal(rep["gross_monthly"]) == 98200


async def test_add_component(client: AsyncClient, hr_headers: dict[str, str]) -> None:
    r = await client.post(
        "/api/v1/salary-config/components", headers=hr_headers,
        json={"code": "LTA", "name": "Leave Travel Allowance", "component_type": "reimbursement",
              "calc_type": "fixed", "value": "5000", "tax_treatment": "exempt"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["code"] == "LTA"
    dup = await client.post(
        "/api/v1/salary-config/components", headers=hr_headers,
        json={"code": "LTA", "name": "x", "component_type": "earning", "calc_type": "fixed"},
    )
    assert dup.status_code == 409
